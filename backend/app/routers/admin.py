from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Admin, Billet, ChatSession, Reclamation, User
from app.schemas import AdminLogin, AdminStats, BilletOut, ReclamationOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _hash_password(password: str) -> str:
    salt = settings.app_name
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(_hash_password(plain), hashed)


_TOKENS: dict[str, str] = {}  # token -> admin_id (in-memory; dev only)


def _require_admin(
    x_admin_token: Annotated[str | None, Header()] = None,
) -> str:
    if not x_admin_token or x_admin_token not in _TOKENS:
        raise HTTPException(status_code=401, detail="Authentification admin requise.")
    return _TOKENS[x_admin_token]


@router.post("/login")
def admin_login(payload: AdminLogin, db: Annotated[Session, Depends(get_db)]):
    admin = db.query(Admin).filter(Admin.email == payload.email).first()
    if admin is None or not _verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    token = secrets.token_urlsafe(32)
    _TOKENS[token] = admin.id
    return {"token": token}


@router.get("/stats", response_model=AdminStats)
def stats(
    _admin_id: Annotated[str, Depends(_require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return AdminStats(
        total_users=db.query(User).count(),
        total_billets=db.query(Billet).count(),
        total_reclamations=db.query(Reclamation).count(),
        total_chat_sessions=db.query(ChatSession).count(),
        reclamations_en_attente=db.query(Reclamation).filter(Reclamation.statut == "en_attente").count(),
    )


@router.get("/billets", response_model=list[BilletOut])
def list_billets(
    _admin_id: Annotated[str, Depends(_require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.query(Billet).order_by(Billet.created_at.desc()).limit(100).all()


@router.get("/reclamations", response_model=list[ReclamationOut])
def list_reclamations(
    _admin_id: Annotated[str, Depends(_require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.query(Reclamation).order_by(Reclamation.created_at.desc()).limit(100).all()
