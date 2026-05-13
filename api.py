"""
API REST FastAPI pour le chatbot.

Cette API expose le chatbot via HTTP pour que le frontend React puisse
l'appeler. Elle s'occupe aussi du CORS pour accepter les requêtes du dev
server React (par défaut http://localhost:5173 pour Vite, 3000 pour CRA).

Lancement :
    uvicorn api:app --reload --port 8000

Endpoints :
    POST /chat                 → envoie un message, reçoit la réponse
    POST /chat/reset           → vide l'historique d'un thread
    GET  /health               → vérifie que le bot est chargé
"""

import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chatbot import build_agent, chat_with_trace

app = FastAPI(title="Chatbot Finance API", version="1.0")

# CORS — autoriser le frontend React à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Create React App
        "http://localhost:5173",   # Vite
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("⏳ Chargement de l'agent au démarrage de l'API...")
agent = build_agent()
print("✅ Agent prêt.")


# ---------- Schémas Pydantic ----------

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None  # si None, on en génère un


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str]
    thread_id: str


# ---------- Endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok", "model": "llama3.2:3b"}


@app.post("/chat", response_model=ChatResponse)
def post_chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message vide.")
    thread_id = req.thread_id or str(uuid.uuid4())
    result = chat_with_trace(agent, req.message, thread_id=thread_id)
    return ChatResponse(
        answer=result["answer"],
        tools_used=result["tools_used"],
        thread_id=thread_id,
    )


@app.post("/chat/reset")
def reset_chat():
    """Renvoie un nouveau thread_id. Côté client, remplacer l'ancien par
    celui-ci → conversation repartie de zéro."""
    return {"thread_id": str(uuid.uuid4())}
