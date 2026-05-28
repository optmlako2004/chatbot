"""Stub temporaire : Noé n'a pas commit le vrai service nominatim.

Fallback OSM/Nominatim pour l'autocomplete des lieux quand la BDD ne renvoie rien.
Retourne [] en attendant le vrai fichier.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://nominatim.openstreetmap.org/search"


async def search(
    query: str,
    type_transport: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    if not query or len(query) < 2:
        return []
    params = {"q": query, "format": "json", "limit": limit, "addressdetails": 1, "accept-language": "fr"}
    headers = {"User-Agent": "voyage-assistant-sae2/1.0"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(_BASE, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Nominatim échec: %s", e)
        return []
    out = []
    for it in data:
        addr = it.get("address", {})
        out.append({
            "id": it.get("place_id"),
            "nom": it.get("display_name", "").split(",")[0],
            "ville": addr.get("city") or addr.get("town") or addr.get("village") or "",
            "pays": addr.get("country", ""),
            "lat": float(it.get("lat", 0)),
            "lon": float(it.get("lon", 0)),
            "type": type_transport,
            "source": "nominatim",
        })
    return out
