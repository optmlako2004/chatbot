from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Billet, User


def verify_billet_identity(
    db: Session,
    numero_billet: str,
    nom: str,
    prenom: str,
    date_naissance: date,
) -> Billet | None:
    """Vérifie qu'un numéro de billet correspond bien à un utilisateur identifié.

    Match insensible à la casse sur nom/prénom. Date de naissance stricte.
    Retourne le Billet si tout correspond, None sinon.
    """
    billet = db.query(Billet).filter(Billet.numero_billet == numero_billet).first()
    if billet is None:
        return None

    user: User = billet.user
    n_in = nom.strip().lower()
    p_in = prenom.strip().lower()
    n_db = (user.nom or "").strip().lower()
    p_db = (user.prenom or "").strip().lower()

    # Accepte l'ordre normal OU l'inversion nom/prénom (cas fréquent Google OAuth
    # ou utilisateurs qui confondent les deux champs).
    match_normal  = (n_in == n_db and p_in == p_db)
    match_swapped = (n_in == p_db and p_in == n_db)
    if not (match_normal or match_swapped):
        return None
    if user.date_naissance != date_naissance:
        return None

    return billet
