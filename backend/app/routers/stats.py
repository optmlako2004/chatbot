"""Statistiques globales de la base de données — chiffres affichés sur la home."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Route

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(db: Session = Depends(get_db)):
    """Retourne les vrais chiffres de la BDD pour la page d'accueil."""
    destinations = db.query(func.count(func.distinct(Route.arrivee))).scalar() or 0
    compagnies   = db.query(func.count(func.distinct(Route.compagnie))).scalar() or 0
    routes_total = db.query(func.count(Route.id)).scalar() or 0

    return {
        "destinations": destinations,
        "compagnies": compagnies,
        "routes_total": routes_total,
    }
