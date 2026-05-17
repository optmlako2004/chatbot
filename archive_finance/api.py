"""
API REST FastAPI complète : auth + sessions + chat + feedback.

Lancement :
    uvicorn api:app --reload --port 8000

Doc interactive : http://localhost:8000/docs

Auth :
    - email/password : POST /auth/signup → POST /auth/login → token JWT
    - Google OAuth   : POST /auth/google (stub pour le moment)
    - anonyme        : POST /auth/anonymous → UUID à mettre en header X-Anonymous-Id

Pour toutes les routes protégées, envoyer SOIT :
    Authorization: Bearer <jwt_token>
SOIT (mode anonyme) :
    X-Anonymous-Id: <uuid>
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    get_current_user,
    login_email,
    login_or_create_google,
    signup_email,
)
from chatbot import build_agent, chat_with_trace
from db import get_db, init_db
from models import ChatSession, Feedback, Message, User

# ---------- App + middleware ----------

app = FastAPI(title="Chatbot Finance API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Init au démarrage ----------

print("🗄️  Initialisation BDD...")
init_db()

print("🤖 Chargement de l'agent...")
agent = build_agent()
print("✅ API prête.")


# ---------- Schémas Pydantic ----------

class UserOut(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    is_anonymous: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    token: str
    user: UserOut


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """STUB : en attendant les clés OAuth, on accepte directement les infos
    Google côté client. À remplacer par la vérif d'un vrai id_token Google."""
    google_sub: str
    email: EmailStr
    name: str
    picture: Optional[str] = ""


class SessionOut(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    ended_at: Optional[datetime]
    rating: Optional[int] = None  # rempli si feedback existe

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    tool_used: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str]
    message_id: str


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class EndSessionResponse(BaseModel):
    farewell: str
    session_id: str


# ---------- Helpers ----------

CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[Session, Depends(get_db)]


def _get_user_session(db: Session, user: User, session_id: str) -> ChatSession:
    """Récupère une session du user, ou 404 si elle n'existe pas / pas à lui."""
    sess = db.get(ChatSession, session_id)
    if sess is None or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session introuvable.")
    return sess


def _make_title(message: str) -> str:
    msg = message.strip().replace("\n", " ")
    return (msg[:40] + "…") if len(msg) > 40 else msg


# ---------- Health ----------

@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


# ---------- Auth ----------

@app.post("/auth/signup", response_model=TokenResponse, status_code=201)
def auth_signup(payload: SignupRequest, db: DBSession):
    user = signup_email(db, payload.email, payload.password, payload.name)
    return TokenResponse(token=create_access_token(user.id), user=UserOut.model_validate(user))


@app.post("/auth/login", response_model=TokenResponse)
def auth_login(payload: LoginRequest, db: DBSession):
    user = login_email(db, payload.email, payload.password)
    return TokenResponse(token=create_access_token(user.id), user=UserOut.model_validate(user))


@app.post("/auth/google", response_model=TokenResponse)
def auth_google(payload: GoogleAuthRequest, db: DBSession):
    """STUB : à brancher quand les clés Google seront dispo. Pour l'instant
    on fait confiance aux infos envoyées par le client. NE PAS UTILISER EN PROD."""
    user = login_or_create_google(
        db,
        google_sub=payload.google_sub,
        email=payload.email,
        name=payload.name,
        picture=payload.picture or "",
    )
    return TokenResponse(token=create_access_token(user.id), user=UserOut.model_validate(user))


@app.post("/auth/anonymous")
def auth_anonymous():
    """Génère un UUID que le frontend stockera en localStorage et enverra
    dans X-Anonymous-Id. À la première requête, le User est créé en BDD."""
    return {"anonymous_id": str(uuid.uuid4())}


@app.get("/auth/me", response_model=UserOut)
def auth_me(user: CurrentUser):
    return UserOut.model_validate(user)


# ---------- Sessions ----------

@app.get("/sessions", response_model=list[SessionOut])
def list_sessions(user: CurrentUser, db: DBSession):
    """Toutes les conversations du user, plus récentes d'abord."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    out = []
    for s in sessions:
        d = SessionOut.model_validate(s)
        d.rating = s.feedback.rating if s.feedback else None
        out.append(d)
    return out


@app.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: CreateSessionRequest, user: CurrentUser, db: DBSession):
    sess = ChatSession(
        user_id=user.id,
        title=payload.title or "Nouvelle conversation",
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return SessionOut.model_validate(sess)


@app.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str, user: CurrentUser, db: DBSession):
    sess = _get_user_session(db, user, session_id)
    out = SessionOut.model_validate(sess)
    out.rating = sess.feedback.rating if sess.feedback else None
    return out


@app.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def get_session_messages(session_id: str, user: CurrentUser, db: DBSession):
    """Pour reconstituer le chat après refresh de la page."""
    sess = _get_user_session(db, user, session_id)
    return [MessageOut.model_validate(m) for m in sess.messages]


@app.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, user: CurrentUser, db: DBSession):
    sess = _get_user_session(db, user, session_id)
    db.delete(sess)
    db.commit()


@app.post("/sessions/{session_id}/end", response_model=EndSessionResponse)
def end_session(session_id: str, user: CurrentUser, db: DBSession):
    """Termine la session. Renvoie un message de clôture au front."""
    sess = _get_user_session(db, user, session_id)
    if sess.status == "ended":
        raise HTTPException(status_code=400, detail="Session déjà terminée.")
    sess.status = "ended"
    sess.ended_at = datetime.now(timezone.utc)
    db.commit()
    return EndSessionResponse(
        farewell="Heureux d'avoir pu vous aider ! Avant de partir, donnez-moi une note sur cette conversation 🙂",
        session_id=sess.id,
    )


@app.post("/sessions/{session_id}/feedback", status_code=201)
def post_feedback(
    session_id: str,
    payload: FeedbackRequest,
    user: CurrentUser,
    db: DBSession,
):
    sess = _get_user_session(db, user, session_id)
    if sess.feedback:
        raise HTTPException(status_code=400, detail="Feedback déjà donné pour cette session.")
    fb = Feedback(session_id=sess.id, rating=payload.rating, comment=payload.comment)
    db.add(fb)
    db.commit()
    return {"ok": True, "rating": fb.rating}


# ---------- Chat ----------

@app.post("/sessions/{session_id}/chat", response_model=ChatResponse)
def chat_in_session(
    session_id: str,
    payload: ChatRequest,
    user: CurrentUser,
    db: DBSession,
):
    sess = _get_user_session(db, user, session_id)
    if sess.status == "ended":
        raise HTTPException(status_code=400, detail="Session terminée. Crée-en une nouvelle.")

    # Sauvegarde du message user
    user_msg = Message(session_id=sess.id, role="user", content=payload.message)
    db.add(user_msg)

    # Si pas encore de titre custom, on génère depuis le 1er message
    if sess.title in ("Nouvelle conversation", ""):
        sess.title = _make_title(payload.message)

    # Appel de l'agent (mémoire LangGraph indexée par thread_id)
    result = chat_with_trace(agent, payload.message, thread_id=sess.thread_id)

    # Sauvegarde de la réponse
    asst_msg = Message(
        session_id=sess.id,
        role="assistant",
        content=result["answer"],
        tool_used=",".join(set(result["tools_used"])) or None,
    )
    db.add(asst_msg)
    db.commit()
    db.refresh(asst_msg)

    return ChatResponse(
        answer=result["answer"],
        tools_used=result["tools_used"],
        message_id=asst_msg.id,
    )
