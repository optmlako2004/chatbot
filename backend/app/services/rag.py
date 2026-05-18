"""Service RAG (Retrieval-Augmented Generation).

Indexation et recherche par similarité cosinus, avec embeddings Gemini
(text-embedding-004) et store JSON persisté.

Deux sources de documents :
- CGV statiques (politique annulation, bagages, remboursement)
- Billets utilisateur générés à la volée

Le store est volontairement simple (in-memory + JSON), suffisant pour la
volumétrie d'un projet pédagogique. Pour un usage prod, on remplacerait
par ChromaDB / Pinecone / pgvector.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

STORE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "rag_store.json"
EMBED_MODEL = "models/gemini-embedding-001"
CHUNK_SIZE = 400  # mots par chunk
CHUNK_OVERLAP = 60

_store: list[dict] = []
_disabled = False


# =====================================================================
# Embeddings
# =====================================================================
def _embed(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[list[float]]:
    """Retourne le vecteur d'embedding via Gemini, ou None si indisponible."""
    global _disabled
    if _disabled or not settings.gemini_api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        result = genai.embed_content(
            model=EMBED_MODEL,
            content=text,
            task_type=task_type,
        )
        return result["embedding"]
    except Exception as exc:
        logger.warning("Embedding Gemini échoué : %s", exc)
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# =====================================================================
# Chunking
# =====================================================================
def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Découpe un texte en chunks de ~size mots avec recouvrement."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    words = text.split()
    if len(words) <= size:
        return [text]
    chunks = []
    step = size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + size])
        if chunk:
            chunks.append(chunk)
        if i + size >= len(words):
            break
    return chunks


# =====================================================================
# Persistance
# =====================================================================
def _save() -> None:
    try:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(json.dumps(_store, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.error("Sauvegarde RAG échouée : %s", exc)


def _load() -> None:
    global _store
    if STORE_PATH.exists():
        try:
            _store = json.loads(STORE_PATH.read_text(encoding="utf-8"))
            logger.info("RAG store chargé : %d chunks", len(_store))
        except Exception as exc:
            logger.error("Chargement RAG échoué : %s", exc)
            _store = []


# =====================================================================
# API publique
# =====================================================================
def index_text(text: str, *, doc_id: str, meta: Optional[dict] = None) -> int:
    """Indexe un texte (le découpe en chunks, l'embed et le stocke).

    Si un document avec ce doc_id existe déjà, il est remplacé.
    Retourne le nombre de chunks indexés.
    """
    global _store
    # Suppression de l'éventuel ancien document
    _store = [c for c in _store if c.get("doc_id") != doc_id]

    chunks = _chunk_text(text)
    indexed = 0
    for i, chunk in enumerate(chunks):
        vec = _embed(chunk, task_type="RETRIEVAL_DOCUMENT")
        if vec is None:
            logger.warning("Skip chunk %d de %s (embedding indisponible)", i, doc_id)
            continue
        _store.append({
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}#{i}",
            "text": chunk,
            "embedding": vec,
            "meta": meta or {},
        })
        indexed += 1
    _save()
    logger.info("Indexé %s : %d chunks", doc_id, indexed)
    return indexed


def search(
    query: str,
    *,
    k: int = 3,
    user_id: Optional[int] = None,
    doc_type: Optional[str] = None,
) -> list[dict]:
    """Recherche les k chunks les plus pertinents pour `query`.

    Filtres optionnels :
    - user_id : ne retourne que les billets de cet utilisateur + tous les CGV
    - doc_type : "cgv" ou "billet"
    """
    if not _store:
        return []
    q_vec = _embed(query, task_type="RETRIEVAL_QUERY")
    if q_vec is None:
        return []

    candidates = _store
    if doc_type:
        candidates = [c for c in candidates if c.get("meta", {}).get("type") == doc_type]
    if user_id is not None:
        candidates = [
            c for c in candidates
            if c.get("meta", {}).get("type") == "cgv"
            or c.get("meta", {}).get("user_id") == user_id
        ]

    scored = [(c, _cosine(q_vec, c["embedding"])) for c in candidates]
    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:k]
    return [
        {"text": c["text"], "score": score, "meta": c.get("meta", {})}
        for c, score in top if score > 0.3  # seuil de pertinence
    ]


def format_context(results: list[dict]) -> str:
    """Formate les résultats RAG pour injection dans le prompt Gemini."""
    if not results:
        return ""
    parts = ["CONNAISSANCES DOCUMENTAIRES (extraits pertinents, à utiliser pour répondre) :"]
    for i, r in enumerate(results, 1):
        meta = r.get("meta", {})
        source = meta.get("source") or meta.get("type", "document")
        parts.append(f"\n[Source {i} — {source}]\n{r['text']}")
    parts.append("\nFin des extraits. Réponds en t'appuyant sur ces informations quand pertinent.")
    return "\n".join(parts)


def index_cgv_folder(folder: Path) -> int:
    """Indexe tous les .md / .txt d'un dossier comme CGV."""
    if not folder.exists():
        logger.warning("Dossier CGV introuvable : %s", folder)
        return 0
    total = 0
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            count = index_text(
                text,
                doc_id=f"cgv:{path.stem}",
                meta={"type": "cgv", "source": path.name},
            )
            total += count
        except Exception as exc:
            logger.error("Indexation %s échouée : %s", path.name, exc)
    return total


def is_indexed(doc_id: str) -> bool:
    return any(c.get("doc_id") == doc_id for c in _store)


def store_size() -> int:
    return len(_store)


# Chargement au import
_load()
