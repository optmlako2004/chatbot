"""
Authentification : email/password + Google OAuth (stub) + mode anonyme.

Système de tokens : JWT signé avec une clé secrète (variable d'env JWT_SECRET).
Le frontend stocke le token et l'envoie dans le header `Authorization: Bearer <token>`.

Pour les utilisateurs anonymes (pas connectés), le frontend stocke un UUID
en cookie/localStorage et l'envoie dans le header `X-Anonymous-Id` ; le
backend crée automatiquement un User correspondant à la première requête.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from db import get_db
from models import User

# ---------- Config ----------
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-prod")
JWT_ALGO = "HS256"
JWT_EXPIRE_DAYS = 30

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- Mot de passe ----------

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ---------- JWT ----------

def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_access_token(token: str) -> Optional[str]:
    """Retourne le user_id ou None si invalide."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload.get("sub")
    except JWTError:
        return None


# ---------- Dépendances FastAPI ----------

def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    x_anonymous_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Récupère le user courant.

    Ordre de priorité :
    1. JWT dans `Authorization: Bearer <token>` → user authentifié (email/Google)
    2. `X-Anonymous-Id: <uuid>` → user anonyme (créé à la volée si inconnu)
    3. Sinon → 401
    """
    # 1. JWT
    token = _extract_bearer(authorization)
    if token:
        user_id = decode_access_token(token)
        if user_id:
            user = db.get(User, user_id)
            if user:
                return user

    # 2. Anonyme par header
    if x_anonymous_id:
        user = db.get(User, x_anonymous_id)
        if user is None:
            user = User(id=x_anonymous_id, is_anonymous=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise (token JWT ou X-Anonymous-Id).",
    )


# ---------- Inscription / Connexion email-password ----------

def signup_email(db: Session, email: str, password: str, name: Optional[str] = None) -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé.")
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name or email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_email(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    return user


# ---------- Google OAuth (STUB - à brancher quand les clés sont dispo) ----------

def login_or_create_google(db: Session, google_sub: str, email: str, name: str, picture: str) -> User:
    """Crée le user s'il n'existe pas, sinon retourne l'existant.

    Cette fonction est appelée APRÈS validation du token Google côté backend.
    Pour l'instant l'endpoint `/auth/google` est un stub qui appelle
    directement cette fonction avec des données mockées.
    """
    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user:
        return user
    # Cas où l'user s'était déjà inscrit en email/password avec le même mail :
    # on lie son compte Google à son user existant.
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.google_sub = google_sub
        user.picture = picture
        db.commit()
        return user
    user = User(
        google_sub=google_sub,
        email=email,
        name=name,
        picture=picture,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
