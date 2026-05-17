from __future__ import annotations

from datetime import datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trajet
from app.schemas import TrajetOut, TransportType

router = APIRouter(prefix="/trajets", tags=["trajets"])


@router.get("", response_model=list[TrajetOut])
def search_trajets(
    db: Annotated[Session, Depends(get_db)],
    type: TransportType | None = Query(default=None),
    depart: str | None = Query(default=None),
    arrivee: str | None = Query(default=None),
    date_str: str | None = Query(default=None, alias="date"),
):
    """Recherche avec fallback gracieux : si la requête exacte ne renvoie rien,
    on relâche progressivement les filtres (date → arrivée → départ) tout en
    gardant `type` car c'est ce que l'utilisateur a explicitement choisi."""

    def _base():
        return db.query(Trajet).filter(Trajet.statut == "actif", Trajet.places_dispo > 0)

    day = None
    if date_str:
        try:
            day = datetime.fromisoformat(date_str).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide (YYYY-MM-DD attendu)")

    def _filtered(use_date: bool, use_arrivee: bool, use_depart: bool):
        q = _base()
        if type:
            q = q.filter(Trajet.type == type)
        if use_depart and depart:
            q = q.filter(Trajet.depart.ilike(f"%{depart}%"))
        if use_arrivee and arrivee:
            q = q.filter(Trajet.arrivee.ilike(f"%{arrivee}%"))
        if use_date and day:
            start = datetime.combine(day, time.min)
            end = datetime.combine(day, time.max)
            q = q.filter(Trajet.date_depart >= start, Trajet.date_depart <= end)
        return q.order_by(Trajet.date_depart.asc()).limit(50).all()

    # Cascade : exact → sans date → sans arrivée → sans départ → tous du mode
    for combo in (
        (True, True, True),
        (False, True, True),
        (False, False, True),
        (False, True, False),
        (False, False, False),
    ):
        results = _filtered(*combo)
        if results:
            return results
    return []


@router.get("/{trajet_id}", response_model=TrajetOut)
def get_trajet(trajet_id: str, db: Annotated[Session, Depends(get_db)]):
    trajet = db.get(Trajet, trajet_id)
    if trajet is None:
        raise HTTPException(status_code=404, detail="Trajet introuvable")
    return trajet
