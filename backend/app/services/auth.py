from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User


def _hash_password(password: str) -> str:
    salt = settings.app_name + "::auth"
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 50_000).hex()


def verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(_hash_password(plain), hashed)


def hash_password(password: str) -> str:
    return _hash_password(password)


_SECRET = os.environ.get("AUTH_SECRET", "dev-secret-change-me")


def create_token(user_id: str, ttl_days: int = 30) -> str:
    exp = int(time.time()) + ttl_days * 86400
    body = f"{user_id}:{exp}"
    sig = hmac.new(_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}:{sig}"


def parse_token(token: str) -> Optional[str]:
    try:
        user_id, exp_str, sig = token.rsplit(":", 2)
    except ValueError:
        return None
    body = f"{user_id}:{exp_str}"
    expected = hmac.new(_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    if int(exp_str) < int(time.time()):
        return None
    return user_id


def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> Optional[User]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    user_id = parse_token(token)
    if not user_id:
        return None
    return db.get(User, user_id)


def get_current_user(
    user: Annotated[Optional[User], Depends(get_optional_user)],
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise.")
    return user
