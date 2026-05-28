from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from datetime import datetime, timezone

from app.models import Billet, Route, Trajet, User
from app.schemas import BilletAccess, BilletCreate, BilletModification, BilletOut
from app.services.auth import get_current_user
from app.services.billet_pdf import build_billet_pdf
from app.services.email import send_confirmation_email
from app.services.identity import verify_billet_identity
from app.services.numeros import generate_numero_billet

router = APIRouter(prefix="/billets", tags=["billets"])


def _materialize_dyn_trajet(db: Session, dyn_id: str, classe_override: str | None = None, prix_override: float | None = None) -> Trajet | None:
    """Matérialise un trajet dynamique (dyn-{route_uuid}-{YYYY-MM-DD}) en ligne DB."""
    # Format : "dyn-{uuid}-{YYYY-MM-DD}" — l'UUID contient 4 tirets donc on splitte depuis la droite
    # rsplit("-", 3) donne ["dyn-{uuid}", "YYYY", "MM", "DD"]
    parts = dyn_id.rsplit("-", 3)
    if len(parts) != 4 or not dyn_id.startswith("dyn-"):
        return None
    try:
        route_id = parts[0][4:]   # retire le préfixe "dyn-"
        date_dep = datetime.strptime(f"{parts[1]}-{parts[2]}-{parts[3]}", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

    route = db.get(Route, route_id)
    if route is None:
        return None

    # Déjà matérialisé ? (idempotent)
    existing = db.query(Trajet).filter(
        Trajet.depart == route.depart,
        Trajet.arrivee == route.arrivee,
        Trajet.compagnie == route.compagnie,
    ).filter(
        Trajet.date_depart >= date_dep.replace(hour=0, minute=0),
        Trajet.date_depart <  date_dep.replace(hour=23, minute=59),
    ).first()
    if existing:
        return existing

    # Recalcule les valeurs dynamiques avec le même seed déterministe
    from app.routers.trajets import _make_trajet_out  # import local pour éviter les circulaires
    t_dyn = _make_trajet_out(route, date_dep)

    trajet = Trajet(
        type=route.type,
        depart=route.depart,
        arrivee=route.arrivee,
        date_depart=t_dyn.date_depart,
        date_arrivee=t_dyn.date_arrivee,
        compagnie=route.compagnie,
        prix=prix_override if prix_override is not None else t_dyn.prix,
        places_dispo=t_dyn.places_dispo,
        retard_minutes=t_dyn.retard_minutes,
        statut=t_dyn.statut,
        photo_url=t_dyn.photo_url,
        has_wifi=t_dyn.has_wifi,
        has_prise=t_dyn.has_prise,
        stops=t_dyn.stops,
        classe=classe_override or t_dyn.classe,
    )
    db.add(trajet)
    db.flush()
    return trajet


@router.post("", response_model=BilletOut, status_code=201)
def create_billet(payload: BilletCreate, db: Annotated[Session, Depends(get_db)]):
    trajet = db.get(Trajet, payload.trajet_id)

    # Trajet dynamique (pas encore matérialisé) → on le crée en BDD maintenant
    if trajet is None and str(payload.trajet_id).startswith("dyn-"):
        trajet = _materialize_dyn_trajet(
            db,
            payload.trajet_id,
            classe_override=payload.classe,
            prix_override=payload.prix_paye,
        )

    if trajet is None:
        raise HTTPException(status_code=404, detail="Trajet introuvable")
    nb_places = max(1, int(payload.nb_places or 1))
    if trajet.statut != "actif" or trajet.places_dispo < nb_places:
        raise HTTPException(status_code=400, detail="Trajet non disponible ou places insuffisantes")

    v = payload.voyageur
    user = db.query(User).filter(User.email == v.email).first()
    if user is None:
        user = User(
            nom=v.nom,
            prenom=v.prenom,
            date_naissance=v.date_naissance,
            email=v.email,
            telephone=v.telephone,
        )
        db.add(user)
        db.flush()
    else:
        # L'utilisateur existait déjà (signup mail/Google) : les infos saisies
        # dans le formulaire de réservation font foi pour le voyageur réel.
        user.nom = v.nom
        user.prenom = v.prenom
        user.date_naissance = v.date_naissance
        if v.telephone:
            user.telephone = v.telephone
        db.flush()

    billet = Billet(
        user_id=user.id,
        trajet_id=trajet.id,
        numero_billet=generate_numero_billet(),
        siege=payload.siege,
        prix_paye=payload.prix_paye if payload.prix_paye is not None else trajet.prix,
    )
    trajet.places_dispo -= nb_places
    db.add(billet)
    db.commit()
    db.refresh(billet)

    JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
               "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    dd = trajet.date_depart
    date_fr = f"{JOURS_FR[dd.weekday()]} {dd.day} {MOIS_FR[dd.month - 1]} {dd.year} à {dd:%H:%M}"
    trajet_resume = (
        f"{trajet.type.capitalize()} {trajet.compagnie} · {trajet.depart} → {trajet.arrivee} · {date_fr}"
    )
    classe_label = payload.classe or trajet.classe or "Standard"
    try:
        pdf_bytes = build_billet_pdf(
            numero_billet=billet.numero_billet,
            voyageur_nom=user.nom,
            voyageur_prenom=user.prenom,
            trajet_type=trajet.type,
            depart=trajet.depart,
            arrivee=trajet.arrivee,
            date_depart=trajet.date_depart.strftime("%d/%m/%Y · %H:%M"),
            date_arrivee=trajet.date_arrivee.strftime("%d/%m/%Y · %H:%M"),
            compagnie=trajet.compagnie,
            classe=classe_label,
            prix_paye=billet.prix_paye,
            siege=billet.siege,
        )
    except Exception:  # pragma: no cover — PDF doit pas bloquer la résa
        pdf_bytes = None

    send_confirmation_email(
        to_email=user.email,
        to_name=f"{user.prenom} {user.nom}",
        numero_billet=billet.numero_billet,
        trajet_resume=trajet_resume,
        chatbot_url=f"{settings.frontend_url}/assistant",
        pdf_bytes=pdf_bytes,
        montant=f"{billet.prix_paye:.2f} EUR",
        classe=classe_label,
    )

    # Indexation RAG du billet — le bot pourra le retrouver via similarité
    try:
        from app.services import rag
        billet_text = (
            f"Billet {billet.numero_billet} au nom de {user.prenom} {user.nom}. "
            f"Trajet : {trajet.type} {trajet.compagnie}, de {trajet.depart} à {trajet.arrivee}, "
            f"le {date_fr}. Arrivée prévue {trajet.date_arrivee.strftime('%d/%m/%Y à %H:%M')}. "
            f"Classe {classe_label}, siège {billet.siege or 'non attribué'}. "
            f"Prix payé : {billet.prix_paye:.2f} EUR. "
            f"Nombre de places : {billet.nb_places}."
        )
        rag.index_text(
            billet_text,
            doc_id=f"billet:{billet.numero_billet}",
            meta={
                "type": "billet",
                "source": f"Billet {billet.numero_billet}",
                "user_id": user.id,
                "numero_billet": billet.numero_billet,
            },
        )
    except Exception:  # pragma: no cover — RAG indispo ne doit pas casser la résa
        pass

    return billet


@router.get("/mine", response_model=list[BilletOut])
def list_my_billets(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Tous les billets achetés par l'utilisateur connecté (les plus récents d'abord)."""
    billets = (
        db.query(Billet)
        .filter(Billet.user_id == user.id)
        .order_by(Billet.created_at.desc())
        .all()
    )
    return billets


@router.post("/access", response_model=BilletOut)
def access_billet(payload: BilletAccess, db: Annotated[Session, Depends(get_db)]):
    """Récupère un billet via numéro + vérification d'identité (pas de login)."""
    billet = verify_billet_identity(
        db,
        numero_billet=payload.numero_billet,
        nom=payload.identity.nom,
        prenom=payload.identity.prenom,
        date_naissance=payload.identity.date_naissance,
    )
    if billet is None:
        raise HTTPException(
            status_code=403,
            detail="Les informations fournies ne correspondent pas à un billet existant.",
        )
    return billet


@router.post("/{numero_billet}/modifier", response_model=BilletOut)
def modifier_billet(
    numero_billet: str,
    payload: BilletModification,
    identity: BilletAccess,
    db: Annotated[Session, Depends(get_db)],
):
    billet = verify_billet_identity(
        db,
        numero_billet=numero_billet,
        nom=identity.identity.nom,
        prenom=identity.identity.prenom,
        date_naissance=identity.identity.date_naissance,
    )
    if billet is None:
        raise HTTPException(status_code=403, detail="Identité non vérifiée.")
    if billet.statut != "confirme":
        raise HTTPException(status_code=400, detail="Billet non modifiable dans son statut actuel.")

    nouveau = db.get(Trajet, payload.nouveau_trajet_id)
    if nouveau is None or nouveau.statut != "actif" or nouveau.places_dispo <= 0:
        raise HTTPException(status_code=400, detail="Nouveau trajet indisponible.")

    ancien = billet.trajet
    ancien.places_dispo += 1
    nouveau.places_dispo -= 1
    billet.trajet_id = nouveau.id
    billet.prix_paye = nouveau.prix

    db.commit()
    db.refresh(billet)
    return billet


@router.post("/{numero_billet}/annuler", response_model=BilletOut)
def annuler_billet(
    numero_billet: str,
    identity: BilletAccess,
    db: Annotated[Session, Depends(get_db)],
):
    billet = verify_billet_identity(
        db,
        numero_billet=numero_billet,
        nom=identity.identity.nom,
        prenom=identity.identity.prenom,
        date_naissance=identity.identity.date_naissance,
    )
    if billet is None:
        raise HTTPException(status_code=403, detail="Identité non vérifiée.")
    if billet.statut == "annule":
        raise HTTPException(status_code=400, detail="Billet déjà annulé.")
    billet.statut = "rembourse"
    billet.trajet.places_dispo += 1
    db.commit()
    db.refresh(billet)
    return billet
