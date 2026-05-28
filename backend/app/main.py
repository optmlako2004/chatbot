from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import admin, auth, billets, chat, images, lieux, reclamations, stats, trajets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    _ensure_route_indexes()
    _index_cgv()


def _ensure_route_indexes() -> None:
    """Crée les index manquants sur routes.depart_code / arrivee_code.

    Sans ces index, la recherche de vols avec escales fait jusqu'à 3000 scans
    complets de la table sur 182k routes (15 s pour Paris-NYC).
    """
    from app.database import engine
    from sqlalchemy import text
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_routes_depart_code ON routes(depart_code)",
        "CREATE INDEX IF NOT EXISTS ix_routes_arrivee_code ON routes(arrivee_code)",
        "CREATE INDEX IF NOT EXISTS ix_routes_type_depart_code ON routes(type, depart_code)",
        "CREATE INDEX IF NOT EXISTS ix_routes_type_arrivee_code ON routes(type, arrivee_code)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    logger.info("Index routes vérifiés (depart_code, arrivee_code, composites).")


def _index_cgv() -> None:
    """Indexe les CGV dans le store RAG (si pas déjà fait)."""
    from pathlib import Path
    from app.services import rag
    if rag.is_indexed("cgv:01_annulation"):
        logger.info("CGV déjà indexées (%d chunks dans le store)", rag.store_size())
        return
    cgv_folder = Path(__file__).resolve().parent.parent / "data" / "cgv"
    count = rag.index_cgv_folder(cgv_folder)
    logger.info("CGV indexées : %d chunks", count)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


app.include_router(auth.router)
app.include_router(lieux.router)
app.include_router(trajets.router)
app.include_router(billets.router)
app.include_router(reclamations.router)
app.include_router(chat.router)
app.include_router(images.router)
app.include_router(stats.router)
app.include_router(admin.router)
