"""
Chatbot RAG Finance + Recherche Web
====================================

Module principal du chatbot. Expose `build_agent()` qui retourne un agent
LangGraph avec :
  - Outil `rag_finance` : recherche dans l'index FAISS local (PDFs Banque de
    France / INC).
  - Outil `web_search`  : recherche internet via DuckDuckGo (BONUS du sujet).
  - Mémoire conversationnelle persistante par `thread_id` (gérée par LangGraph).

Utilisation :

    from chatbot import build_agent, chat
    agent = build_agent()
    reponse = chat(agent, "C'est quoi un livret A ?", thread_id="user-42")
"""

from __future__ import annotations

import os
import sqlite3
from functools import lru_cache

from dotenv import load_dotenv
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

# ---------- Configuration ----------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "thenlper/gte-small")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "faiss_index")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
CHECKPOINT_DB = os.getenv("CHECKPOINT_DB", "conversations.db")

SYSTEM_PROMPT = (
    "Tu es un assistant français sympathique, spécialisé en éducation financière. "
    "Tu réponds toujours en français, de façon claire, naturelle et chaleureuse.\n\n"
    "TON COMPORTEMENT :\n"
    "- Pour une salutation (bonjour, salut, hello...) → réponds chaleureusement, "
    "présente-toi en une phrase, et propose ton aide. N'utilise AUCUN outil.\n"
    "- Pour un remerciement / au revoir / petite conversation → réponds "
    "naturellement, sans utiliser d'outil.\n"
    "- Pour une question de finance (définition, produit, budget, arnaques...) "
    "→ utilise l'outil rag_finance puis reformule la réponse de façon pédagogique.\n"
    "- Pour un chiffre actuel (taux, cours, actualité 2025-2026) → utilise web_search.\n"
    "- Pour une question vraiment hors finance (cuisine, sport...) → dis "
    "gentiment que ce n'est pas ton domaine et propose de revenir à un sujet "
    "financier. Reste poli et utile.\n"
    "- N'invente JAMAIS de chiffres. Si tu ne sais pas, dis-le."
)

# ---------- Singletons (chargés une seule fois) ----------

@lru_cache(maxsize=1)
def _get_retriever():
    """Charge l'index FAISS une seule fois (coûteux : modèle d'embeddings)."""
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = FAISS.load_local(
        FAISS_INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    return vectorstore.as_retriever(search_kwargs={"k": RAG_TOP_K})


@lru_cache(maxsize=1)
def _get_ddg():
    return DuckDuckGoSearchRun()


# ---------- Outils exposés à l'agent ----------

@tool
def rag_finance(query: str) -> str:
    """Recherche dans la base de connaissances officielle d'éducation financière
    (Banque de France, INC). À utiliser pour les définitions, concepts financiers
    généraux, produits d'épargne (livret A, PEL, LDDS...), crédit, budget,
    arnaques, gestion personnelle.
    """
    docs = _get_retriever().invoke(query)
    if not docs:
        return "Aucun document pertinent trouvé dans la base finance."
    return "\n\n".join(
        f"[Source: {d.metadata.get('source', '?').split('/')[-1]}]\n{d.page_content[:500]}"
        for d in docs
    )


@tool
def web_search(query: str) -> str:
    """Recherche sur Internet via DuckDuckGo. À utiliser UNIQUEMENT pour des
    informations récentes : taux d'intérêt actuels, cours de bourse, actualité
    2025-2026, dernières lois, chiffres datés. Ne pas utiliser pour des
    définitions générales.
    """
    return _get_ddg().invoke(query)


# ---------- Construction de l'agent ----------

def _build_checkpointer(persistent: bool):
    """Crée le checkpointer (mémoire conversationnelle).

    - persistent=True  → SQLite, l'historique survit aux redémarrages.
    - persistent=False → InMemorySaver, plus rapide mais perdu au restart.
    """
    if not persistent:
        return InMemorySaver()
    conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()  # crée les tables si besoin (idempotent)
    return saver


def build_agent(model: str | None = None, persistent_memory: bool = True):
    """Construit l'agent LangGraph avec mémoire conversationnelle.

    Args:
        model: nom d'un modèle Ollama (ex. "llama3.2:3b", "llama3.1:8b").
            Doit supporter le tool calling natif (llama3.1+, mistral-nemo, qwen2.5...).
        persistent_memory: si True, l'historique est stocké dans SQLite
            (`conversations.db`) et survit aux redémarrages. Si False, RAM seulement.

    Returns:
        Agent LangGraph compilé. Invocable via `agent.invoke({"messages": [...]})`.
    """
    llm = ChatOllama(
        model=model or OLLAMA_MODEL,
        temperature=0.1,
        base_url=OLLAMA_URL,
    )
    return create_react_agent(
        llm,
        tools=[rag_finance, web_search],
        prompt=SYSTEM_PROMPT,
        checkpointer=_build_checkpointer(persistent_memory),
    )


def chat(agent, message: str, thread_id: str = "default") -> str:
    """Envoie un message à l'agent et retourne la réponse texte.

    Le `thread_id` isole les conversations : deux thread_id différents
    n'ont pas accès au même historique.
    """
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    return result["messages"][-1].content


def chat_with_trace(agent, message: str, thread_id: str = "default") -> dict:
    """Variante de chat() qui retourne aussi la trace des outils appelés.
    Utile pour debug et pour afficher 'cherché sur le web' dans l'UI."""
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    tools_used = []
    for m in result["messages"]:
        for tc in getattr(m, "tool_calls", []) or []:
            tools_used.append(tc["name"])
    return {
        "answer": result["messages"][-1].content,
        "tools_used": tools_used,
    }


if __name__ == "__main__":
    print("Chargement de l'agent...")
    agent = build_agent()
    print("OK. Tape 'q' pour quitter.\n")
    tid = "cli-test"
    while True:
        q = input("> ").strip()
        if q.lower() in {"q", "quit", "exit"}:
            break
        if not q:
            continue
        r = chat_with_trace(agent, q, thread_id=tid)
        if r["tools_used"]:
            print(f"  [outils: {', '.join(r['tools_used'])}]")
        print(f"\n{r['answer']}\n")
