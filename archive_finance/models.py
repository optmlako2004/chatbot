"""
Modèles SQLAlchemy pour le chatbot.

Architecture :
- User : un utilisateur (auth email/password OU Google OAuth OU anonyme par cookie)
- ChatSession : une conversation. Un user peut en avoir plusieurs.
  Liée à un thread_id LangGraph qui contient la mémoire conversationnelle.
- Message : un message dans une session (user ou assistant).
- Feedback : note + commentaire donnés à la fin d'une session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    """Un utilisateur du chatbot.

    Trois modes d'authentification, mutuellement exclusifs :
    - email + password_hash         → mode "email"
    - google_sub                    → mode "google" (sub = identifiant Google unique)
    - rien (anonymous=True)         → mode "anonymous", identifié par cookie côté client
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)

    # Auth email/password
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Auth Google OAuth
    google_sub: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)

    # Profil
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    picture: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Mode anonyme (pas d'email ni de Google)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    sessions: Mapped[list[ChatSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        ident = self.email or self.google_sub or f"anon-{self.id[:8]}"
        return f"<User {ident}>"


class ChatSession(Base):
    """Une conversation entre un user et le chatbot.

    `thread_id` est l'identifiant utilisé par LangGraph pour stocker la
    mémoire conversationnelle dans `conversations.db`. Garder le mapping
    session_id ↔ thread_id permet de retrouver la mémoire de l'agent.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String, default=_uuid)

    title: Mapped[str] = mapped_column(String, default="Nouvelle conversation")
    status: Mapped[str] = mapped_column(String, default="active")  # "active" | "ended"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list[Message]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    feedback: Mapped[Optional[Feedback]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.id[:8]} '{self.title}' ({self.status})>"


class Message(Base):
    """Un message dans une conversation.

    On garde `tool_used` pour pouvoir afficher dans l'UI un badge
    \"cherché sur le web\" ou \"base finance\" sur les réponses.
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id"), index=True)

    role: Mapped[str] = mapped_column(String)  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text)
    tool_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # ex: "rag_finance", "web_search", ou plusieurs séparés par virgule

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class Feedback(Base):
    """Note et commentaire donnés à la fin d'une session.

    rating : 1 à 5 étoiles.
    comment : texte libre, optionnel.
    """

    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("chat_sessions.id"), unique=True, index=True
    )

    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[ChatSession] = relationship(back_populates="feedback")
