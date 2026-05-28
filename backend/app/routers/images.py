from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.pixabay import get_image

router = APIRouter(prefix="/images", tags=["images"])


class ImageOut(BaseModel):
    url: str
    query: str


@router.get("", response_model=ImageOut)
async def get_city_image(
    q: str = Query(..., description="Nom de la ville ou destination"),
    mode: str = Query(default="ville", description="Mode transport pour le fallback"),
):
    """Retourne une URL d'image pour la destination donnée (avec cache)."""
    url = await get_image(query=q, fallback_mode=mode)
    return {"url": url, "query": q}


@router.get("/batch", response_model=list[ImageOut])
async def get_batch_images(
    q: str = Query(..., description="Noms séparés par des virgules"),
    mode: str = Query(default="ville"),
):
    """Retourne des images pour plusieurs destinations en une requête."""
    cities = [c.strip() for c in q.split(",") if c.strip()][:10]
    results = []
    for city in cities:
        url = await get_image(query=city, fallback_mode=mode)
        results.append({"url": url, "query": city})
    return results
