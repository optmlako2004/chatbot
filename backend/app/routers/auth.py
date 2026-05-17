from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    date_naissance: date
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    telephone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """STUB : accepte les infos Google côté client. À remplacer par une vraie
    vérification de l'id_token Google quand le client_id sera configuré."""

    google_sub: str
    email: EmailStr
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = ""


class UserOut(BaseModel):
    id: str
    nom: str
    prenom: str
    email: EmailStr
    picture: Optional[str] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserOut


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Un compte existe déjà avec cet email.")
    user = User(
        nom=payload.nom,
        prenom=payload.prenom,
        date_naissance=payload.date_naissance,
        email=payload.email,
        telephone=payload.telephone,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=create_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    return AuthResponse(token=create_token(user.id), user=UserOut.model_validate(user))


@router.post("/google", response_model=AuthResponse)
def auth_google(payload: GoogleAuthRequest, db: Annotated[Session, Depends(get_db)]):
    """STUB Google OAuth : crée ou retrouve un user à partir des infos Google.
    En prod, remplacer par une vérification du id_token via google-auth-library."""
    user = db.query(User).filter(User.google_sub == payload.google_sub).first()
    if user is None:
        user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        user = User(
            nom=payload.family_name or payload.name.split(" ")[-1] if payload.name else "Google",
            prenom=payload.given_name or payload.name.split(" ")[0] if payload.name else "User",
            date_naissance=date(2000, 1, 1),
            email=payload.email,
            google_sub=payload.google_sub,
            picture=payload.picture,
        )
        db.add(user)
    else:
        if not user.google_sub:
            user.google_sub = payload.google_sub
        if payload.picture and not user.picture:
            user.picture = payload.picture
    db.commit()
    db.refresh(user)
    return AuthResponse(token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return UserOut.model_validate(user)
