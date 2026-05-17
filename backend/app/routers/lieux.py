from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.data.lieux import search_lieux

router = APIRouter(prefix="/lieux", tags=["lieux"])


class LieuOut(BaseModel):
    nom: str
    ville: str
    pays: str
    code: str
    type: str


@router.get("", response_model=list[LieuOut])
def autocomplete(
    q: str = Query(default="", description="Texte à chercher dans nom/ville/pays/code"),
    type: Optional[Literal["avion", "train", "bateau", "bus"]] = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
):
    """Autocomplete pour les champs Départ/Arrivée du formulaire de recherche."""
    return search_lieux(query=q, type_transport=type, limit=limit)
