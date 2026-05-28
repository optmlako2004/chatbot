from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


TRANSPORT_TYPES = ("avion", "train", "bateau", "bus")


class Route(Base):
    """Route de base sans date — sert à la génération dynamique des trajets."""
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(SAEnum(*("avion", "train", "bateau", "bus"), name="route_type"), nullable=False, index=True)
    depart: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    arrivee: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    depart_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    arrivee_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    compagnie: Mapped[str] = mapped_column(String(100), nullable=False)
    duree_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    dep_heure: Mapped[int] = mapped_column(Integer, default=8)
    dep_minute: Mapped[int] = mapped_column(Integer, default=0)
    has_wifi: Mapped[bool] = mapped_column(default=False)
    has_prise: Mapped[bool] = mapped_column(default=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
BILLET_STATUTS = ("confirme", "annule", "utilise", "rembourse")
TRAJET_STATUTS = ("actif", "annule", "complet")
RECLAMATION_TYPES = ("bagage", "incident", "remboursement", "autre")
RECLAMATION_STATUTS = ("en_attente", "en_cours", "resolu", "clos")
MESSAGE_ROLES = ("user", "assistant", "system", "tool")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    date_naissance: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    telephone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    google_sub: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True, index=True)
    picture: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    billets: Mapped[list["Billet"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reclamations: Mapped[list["Reclamation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")


class Trajet(Base):
    __tablename__ = "trajets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(SAEnum(*TRANSPORT_TYPES, name="transport_type"), nullable=False, index=True)
    depart: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    arrivee: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    date_depart: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    date_arrivee: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    compagnie: Mapped[str] = mapped_column(String(100), nullable=False)
    prix: Mapped[float] = mapped_column(Float, nullable=False)
    places_dispo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retard_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    statut: Mapped[str] = mapped_column(SAEnum(*TRAJET_STATUTS, name="trajet_statut"), default="actif")
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    has_wifi: Mapped[bool] = mapped_column(default=True, nullable=False)
    has_prise: Mapped[bool] = mapped_column(default=True, nullable=False)
    stops: Mapped[str] = mapped_column(String(20), default="direct")  # "direct" | "1 arrêt"
    classe: Mapped[str] = mapped_column(String(50), default="Standard")

    billets: Mapped[list["Billet"]] = relationship(back_populates="trajet")


class Billet(Base):
    __tablename__ = "billets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    trajet_id: Mapped[str] = mapped_column(String, ForeignKey("trajets.id"), index=True)
    numero_billet: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    statut: Mapped[str] = mapped_column(SAEnum(*BILLET_STATUTS, name="billet_statut"), default="confirme")
    siege: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    voiture: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tarif: Mapped[str] = mapped_column(String(50), default="Loisir")
    prix_paye: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="billets")
    trajet: Mapped[Trajet] = relationship(back_populates="billets")
    reclamations: Mapped[list["Reclamation"]] = relationship(back_populates="billet")


class Reclamation(Base):
    __tablename__ = "reclamations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    billet_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("billets.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(SAEnum(*RECLAMATION_TYPES, name="reclamation_type"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    statut: Mapped[str] = mapped_column(SAEnum(*RECLAMATION_STATUTS, name="reclamation_statut"), default="en_attente")
    numero_suivi: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="reclamations")
    billet: Mapped[Optional[Billet]] = relationship(back_populates="reclamations")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True, index=True)
    session_token: Mapped[str] = mapped_column(String, unique=True, index=True, default=_uuid)
    contexte: Mapped[dict] = mapped_column(JSON, default=dict)
    title: Mapped[str] = mapped_column(String(120), default="Nouvelle conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(SAEnum(*MESSAGE_ROLES, name="message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
