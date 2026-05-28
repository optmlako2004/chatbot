from __future__ import annotations

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.data.lieux import _EN_TO_FR_QUERY, _norm
from app.database import get_db
from app.models import Route
from app.services import nominatim

router = APIRouter(prefix="/lieux", tags=["lieux"])


class LieuOut(BaseModel):
    nom: str
    ville: str
    pays: str
    code: str
    type: str


def _search_db(db: Session, q: str, type_transport: str | None, limit: int) -> list[dict]:
    """Cherche dans la table Route (2 999 destinations) avec support accents + pays + anglais."""
    from sqlalchemy import func as sqlfunc
    from app.routers.trajets import _clean_dest_name

    q_norm = _norm(q)
    extra_prefixes: list[str] = _EN_TO_FR_QUERY.get(q_norm, [])

    seen: set[str] = set()
    results: list[dict] = []

    def _pull(pattern: str, must_contain: str | None = None) -> None:
        """Tire des lignes depuis la BDD et les ajoute à results."""
        for col in (Route.depart, Route.arrivee):
            qry = (
                db.query(col, Route.type, sqlfunc.count(col).label("cnt"))
                .filter(col.ilike(pattern))
                .group_by(col, Route.type)
            )
            if type_transport:
                qry = qry.filter(Route.type == type_transport)
            # Trier par fréquence DESC → les grandes villes (Paris, London) avant les petites
            qry = qry.order_by(sqlfunc.count(col).desc()).limit(limit * 6)
            for (raw, rtype, _cnt) in qry.all():
                clean = _clean_dest_name(raw)
                clean_norm = _norm(clean)
                raw_norm = _norm(raw)
                # Filtre : doit correspondre sur le nom brut OU le nom traduit
                if must_contain and must_contain not in raw_norm and must_contain not in clean_norm:
                    continue
                # Si pas de filtre transport : dédup par nom seul (évite "Marseille avion/train/bus/bateau")
                key = clean if not type_transport else f"{clean}|{rtype}"
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "nom": clean,
                        "ville": clean,
                        "pays": "",
                        "code": clean[:3].upper(),
                        "type": rtype,
                    })
            if len(results) >= limit:
                break

    # 1. Recherche directe : la chaîne brute commence par q
    _pull(f"{q}%", must_contain=q_norm)
    # 2. Traductions pays/EN → pas de filtre supplémentaire (le préfixe suffit)
    for prefix in extra_prefixes:
        if len(results) >= limit:
            break
        _pull(f"{prefix}%")
    # 3. Milieu de mot en fallback
    if len(results) < 3:
        _pull(f"% {q}%", must_contain=q_norm)

    return results[:limit]


@router.get("", response_model=list[LieuOut])
async def autocomplete(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(default="", description="Texte à chercher"),
    type: Optional[Literal["avion", "train", "bateau", "bus"]] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Autocomplete 100 % dynamique depuis la BDD (2 999 destinations).
    Gère : accents manquants, anglais, noms de pays, milieu de mot."""
    if not q or len(q) < 1:
        return []

    results = _search_db(db, q, type, limit)
    if results:
        return results

    # Nominatim uniquement si vraiment rien trouvé dans la BDD
    if len(q) >= 2:
        return await nominatim.search(query=q, type_transport=type, limit=limit)

    return []
