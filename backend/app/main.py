from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import admin, auth, billets, chat, lieux, reclamations, trajets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

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


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


app.include_router(auth.router)
app.include_router(lieux.router)
app.include_router(trajets.router)
app.include_router(billets.router)
app.include_router(reclamations.router)
app.include_router(chat.router)
app.include_router(admin.router)
