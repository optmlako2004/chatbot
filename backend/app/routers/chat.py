from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Billet, ChatMessage, ChatSession, User
from app.schemas import ChatMessage as ChatMessageIn
from app.schemas import ChatMessageOut, ChatResponse, ChatStart
from app.services.auth import get_current_user, get_optional_user
from app.services.chatbot import QUICK_REPLIES_HOME, process_message
from app.services.i18n import LANGS, t

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionSummary(BaseModel):
    session_token: str
    title: str
    created_at: str
    message_count: int


@router.post("/start", response_model=ChatResponse)
def start_chat(
    payload: ChatStart,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
):
    """Crée une nouvelle session de chat (ou reprend une existante).
    Si un user est authentifié, la session lui est rattachée."""
    lang = payload.lang if payload.lang in LANGS else "fr"
    if payload.session_token:
        session = db.query(ChatSession).filter(ChatSession.session_token == payload.session_token).first()
        if session is None:
            raise HTTPException(status_code=404, detail="Session introuvable.")
        if session.user_id and (user is None or session.user_id != user.id):
            raise HTTPException(status_code=403, detail="Accès refusé à cette session.")
        # Relie la session anonyme à l'utilisateur connecté
        if session.user_id is None and user is not None:
            session.user_id = user.id
            db.commit()
    else:
        session = ChatSession(user_id=user.id if user else None)
        db.add(session)
        db.commit()
        db.refresh(session)

    # Billet le plus récent de l'utilisateur connecté (pour une accroche utile)
    recent_billet = None
    if user:
        recent_billet = (
            db.query(Billet)
            .filter(Billet.user_id == user.id)
            .order_by(Billet.created_at.desc())
            .first()
        )

    if not session.messages:
        if user:
            greeting_text = t(
                "Bonjour {prenom}, comment puis-je vous aider ?",
                lang,
                prenom=user.prenom,
            )
            if recent_billet is not None and recent_billet.trajet is not None:
                trj = recent_billet.trajet
                greeting_text += " " + t(
                    "Je vois votre billet {numero} ({depart} → {arrivee}) — c'est à ce sujet ?",
                    lang,
                    numero=recent_billet.numero_billet,
                    depart=trj.depart,
                    arrivee=trj.arrivee,
                )
        else:
            greeting_text = t(
                "Bonjour ! Je suis votre assistant Voyage. Comment puis-je vous aider ?",
                lang,
            )
        greeting = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=greeting_text,
        )
        db.add(greeting)
        db.commit()
        db.refresh(greeting)

    quick = [t(q, lang) for q in QUICK_REPLIES_HOME]
    if user and len(session.messages) <= 1:
        quick = [t("Voir mes réservations", lang), t("Mon prochain voyage", lang)] + quick

    last = session.messages[-1] if session.messages else greeting
    return ChatResponse(
        session_token=session.session_token,
        answer=last.content,
        tools_used=[],
        message_id=last.id,
        quick_replies=quick if len(session.messages) <= 1 else [],
    )


@router.post("/message", response_model=ChatResponse)
def send_message(
    payload: ChatMessageIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
):
    lang = payload.lang if payload.lang in LANGS else "fr"
    session = db.query(ChatSession).filter(ChatSession.session_token == payload.session_token).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session introuvable.")
    if session.user_id and (user is None or session.user_id != user.id):
        raise HTTPException(status_code=403, detail="Accès refusé à cette session.")

    # Compte les messages user existants AVANT d'ajouter celui-ci
    user_msgs_before = sum(1 for m in session.messages if m.role == "user")

    # Tronque proprement si l'utilisateur a collé un pavé énorme
    MAX_CHAT_MESSAGE = 4000
    raw_message = payload.message
    was_truncated = len(raw_message) > MAX_CHAT_MESSAGE
    message_for_bot = raw_message[:MAX_CHAT_MESSAGE]

    user_msg = ChatMessage(session_id=session.id, role="user", content=message_for_bot)
    db.add(user_msg)
    db.flush()

    # Auto-titre = première phrase de l'utilisateur
    if user_msgs_before == 0:
        title = message_for_bot.strip().split("\n")[0]
        session.title = (title[:60] + "…") if len(title) > 60 else title

    result = process_message(
        db,
        message_for_bot,
        context=session.contexte or {},
        user=user,
        session_id=session.id,
        lang=lang,
    )

    # Si on a tronqué, on préfixe la réponse du bot d'une note transparente
    answer_text = result["answer"]
    if was_truncated:
        answer_text = (
            t(
                "(Votre message faisait {len} caractères, j'ai gardé les {max} premiers.) ",
                lang,
                len=len(raw_message),
                max=MAX_CHAT_MESSAGE,
            )
            + answer_text
        )

    asst_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer_text,
        tool_used=result.get("tool_used"),
    )
    session.contexte = result["context"]
    db.add(asst_msg)
    db.commit()
    db.refresh(asst_msg)

    return ChatResponse(
        session_token=session.session_token,
        answer=asst_msg.content,
        tools_used=[result["tool_used"]] if result.get("tool_used") else [],
        message_id=asst_msg.id,
        quick_replies=result.get("quick_replies", []),
        results=result.get("results", []),
    )


@router.get("/sessions", response_model=list[SessionSummary])
def list_my_sessions(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Toutes les conversations de l'utilisateur connecté, plus récentes d'abord."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        SessionSummary(
            session_token=s.session_token,
            title=s.title,
            created_at=s.created_at.isoformat(),
            message_count=len(s.messages),
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_token}", status_code=204)
def delete_session(
    session_token: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Supprime une session de chat et tous ses messages (réservé au propriétaire)."""
    session = db.query(ChatSession).filter(ChatSession.session_token == session_token).first()
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session introuvable.")
    db.delete(session)
    db.commit()
    return None


class EndSessionPayload(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: Optional[str] = Field(default="", max_length=1000)


@router.post("/sessions/{session_token}/end", status_code=204)
def end_session(
    session_token: str,
    payload: EndSessionPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
):
    """Termine une session de chat et enregistre la note / feedback de l'utilisateur."""
    session = db.query(ChatSession).filter(ChatSession.session_token == session_token).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session introuvable.")
    if session.user_id and (user is None or session.user_id != user.id):
        raise HTTPException(status_code=403, detail="Accès refusé à cette session.")
    session.ended_at = datetime.now(timezone.utc)
    session.rating = payload.rating
    session.feedback = (payload.feedback or "").strip() or None
    db.commit()
    return None


@router.get("/{session_token}/history", response_model=list[ChatMessageOut])
def history(
    session_token: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
):
    session = db.query(ChatSession).filter(ChatSession.session_token == session_token).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session introuvable.")
    if session.user_id and (user is None or session.user_id != user.id):
        raise HTTPException(status_code=403, detail="Accès refusé.")
    return session.messages
