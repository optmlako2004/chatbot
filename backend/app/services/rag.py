"""Service RAG (Retrieval-Augmented Generation) — version LangChain + FAISS + HF embeddings.

Architecture (alignée Séance 1) :
- Embeddings : thenlper/gte-small (HuggingFace, local, multilingue, 384 dim)
- Vector store : FAISS (sauvegardé sur disque dans settings.rag_index_dir)
- Chunking : RecursiveCharacterTextSplitter (chunk_size=512, overlap=51)
- Distance : L2 sur vecteurs normalisés, convertie en similarité cosinus

Deux sources de documents :
- CGV statiques (politique annulation, bagages, remboursement)
- Billets utilisateur générés à la volée

L'API publique (is_indexed, store_size, index_text, index_cgv_folder, search,
format_context) reste identique à la version précédente : main.py, chatbot.py
et routers/billets.py n'ont rien à changer.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# =====================================================================
# Configuration
# =====================================================================
EMBED_MODEL_NAME = "thenlper/gte-small"   # 384 dim, multilingue, vu en Séance 1
CHUNK_SIZE = 512
CHUNK_OVERLAP = 51
SCORE_THRESHOLD = 0.50   # similarité cosinus minimale (gte-small a un baseline ~0.78 donc on garde bas)

_p = Path(settings.rag_index_dir)
if not _p.is_absolute():
    # Résolution stable : relative au dossier `backend/` (parent de `app/`),
    # peu importe le CWD au lancement.
    _p = Path(__file__).resolve().parent.parent.parent / _p
_INDEX_DIR = _p.resolve()
_MAPPING_PATH = _INDEX_DIR / "doc_mapping.json"

# Etat module (chargé paresseusement)
_embeddings = None        # langchain HuggingFaceEmbeddings (lazy)
_vectorstore = None       # langchain FAISS (lazy)
_doc_chunks: dict[str, list[str]] = {}   # doc_id -> liste d'ids FAISS
_lock = threading.Lock()
_disabled = False


# =====================================================================
# Chargement paresseux des modèles
# =====================================================================
def _get_embeddings():
    """Charge gte-small la première fois qu'on en a besoin (~70 Mo)."""
    global _embeddings, _disabled
    if _embeddings is not None or _disabled:
        return _embeddings
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL_NAME,
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embeddings HF chargés : %s", EMBED_MODEL_NAME)
    except Exception as exc:
        logger.error("Impossible de charger les embeddings HF : %s", exc)
        _disabled = True
    return _embeddings


def _splitter():
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _get_vectorstore():
    """Charge ou crée le vector store FAISS."""
    global _vectorstore, _doc_chunks
    if _vectorstore is not None:
        return _vectorstore
    emb = _get_embeddings()
    if emb is None:
        return None
    from langchain_community.vectorstores import FAISS
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if (_INDEX_DIR / "index.faiss").exists():
        _vectorstore = FAISS.load_local(
            str(_INDEX_DIR), emb, allow_dangerous_deserialization=True,
        )
        if _MAPPING_PATH.exists():
            try:
                _doc_chunks = json.loads(_MAPPING_PATH.read_text(encoding="utf-8"))
            except Exception:
                _doc_chunks = {}
        logger.info("FAISS index chargé (%d vecteurs, %d documents)",
                    _vectorstore.index.ntotal, len(_doc_chunks))
    return _vectorstore


def _persist() -> None:
    if _vectorstore is None:
        return
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    _vectorstore.save_local(str(_INDEX_DIR))
    _MAPPING_PATH.write_text(
        json.dumps(_doc_chunks, ensure_ascii=False), encoding="utf-8",
    )


# =====================================================================
# API publique
# =====================================================================
def index_text(text: str, *, doc_id: str, meta: Optional[dict] = None) -> int:
    """Indexe un texte (chunking récursif + embeddings + ajout FAISS).

    Si un document avec ce doc_id existe déjà, ses anciens chunks sont
    supprimés avant insertion.
    """
    global _vectorstore, _doc_chunks
    if _disabled:
        return 0
    with _lock:
        emb = _get_embeddings()
        if emb is None:
            return 0
        chunks = _splitter().split_text(text)
        if not chunks:
            return 0

        from langchain_community.vectorstores import FAISS

        # 1) Si le doc existe déjà, on supprime ses chunks
        vs = _get_vectorstore()
        if vs is not None and doc_id in _doc_chunks:
            try:
                vs.delete(ids=_doc_chunks[doc_id])
            except Exception as exc:
                logger.warning("Suppression doc %s impossible : %s", doc_id, exc)
            _doc_chunks.pop(doc_id, None)

        # 2) Préparer les nouveaux chunks (ids stables + metadata)
        new_ids = [f"{doc_id}#{i}" for i in range(len(chunks))]
        base_meta = dict(meta or {})
        base_meta["doc_id"] = doc_id
        metadatas = [
            {**base_meta, "chunk_id": cid, "chunk_index": i}
            for i, cid in enumerate(new_ids)
        ]

        # 3) Ajout au vector store (création si premier doc)
        if vs is None:
            vs = FAISS.from_texts(chunks, emb, metadatas=metadatas, ids=new_ids)
            _vectorstore = vs
        else:
            vs.add_texts(chunks, metadatas=metadatas, ids=new_ids)

        _doc_chunks[doc_id] = new_ids
        _persist()
        logger.info("Indexé %s : %d chunks (FAISS, gte-small)", doc_id, len(chunks))
        return len(chunks)


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
    if _disabled:
        return []
    vs = _get_vectorstore()
    if vs is None:
        return []

    def _filter(meta: dict) -> bool:
        if doc_type and meta.get("type") != doc_type:
            return False
        if user_id is not None and meta.get("type") != "cgv":
            if meta.get("user_id") != user_id:
                return False
        return True

    # FAISS renvoie une L2 distance sur vecteurs normalisés.
    # cos_sim = 1 - L2² / 2  (vecteurs unitaires)
    raw = vs.similarity_search_with_score(query, k=k * 4)
    results: list[dict] = []
    for doc, l2 in raw:
        if not _filter(doc.metadata or {}):
            continue
        cos = 1.0 - float(l2) / 2.0
        if cos < SCORE_THRESHOLD:
            continue
        results.append({
            "text": doc.page_content,
            "score": cos,
            "meta": doc.metadata or {},
        })
        if len(results) >= k:
            break
    return results


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
    _get_vectorstore()  # force le chargement pour peupler _doc_chunks
    return doc_id in _doc_chunks


def store_size() -> int:
    vs = _get_vectorstore()
    if vs is None:
        return 0
    return vs.index.ntotal
