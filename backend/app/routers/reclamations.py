from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Billet, Reclamation, User
from app.schemas import ReclamationCreate, ReclamationOut
from app.services.email import send_reclamation_email
from app.services.identity import verify_billet_identity
from app.services.numeros import generate_numero_reclamation

router = APIRouter(prefix="/reclamations", tags=["reclamations"])


@router.post("", response_model=ReclamationOut, status_code=201)
def create_reclamation(payload: ReclamationCreate, db: Annotated[Session, Depends(get_db)]):
    billet: Billet | None = None
    user: User | None = None

    if payload.numero_billet:
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
                detail="Le numéro de billet ne correspond pas aux informations fournies.",
            )
        user = billet.user
    else:
        user = (
            db.query(User)
            .filter(
                User.nom.ilike(payload.identity.nom),
                User.prenom.ilike(payload.identity.prenom),
                User.date_naissance == payload.identity.date_naissance,
            )
            .first()
        )
        if user is None:
            raise HTTPException(
                status_code=403,
                detail="Aucun compte ne correspond aux informations fournies.",
            )

    reclamation = Reclamation(
        user_id=user.id,
        billet_id=billet.id if billet else None,
        type=payload.type,
        description=payload.description,
        numero_suivi=generate_numero_reclamation(),
    )
    db.add(reclamation)
    db.commit()
    db.refresh(reclamation)

    send_reclamation_email(
        to_email=payload.email_contact,
        to_name=f"{user.prenom} {user.nom}",
        numero_suivi=reclamation.numero_suivi,
        type_reclamation=reclamation.type,
    )
    return reclamation


@router.get("/{numero_suivi}", response_model=ReclamationOut)
def suivi_reclamation(numero_suivi: str, db: Annotated[Session, Depends(get_db)]):
    rec = db.query(Reclamation).filter(Reclamation.numero_suivi == numero_suivi).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="Réclamation introuvable")
    return rec
