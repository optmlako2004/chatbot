"""Reranker CrossEncoder pour le RAG.

Pipeline classique RAG en deux étapes (vu en Séance 1) :
1. Bi-encoder (gte-small) : rapide, retrieve k=10 candidats par similarité cosinus.
2. Cross-encoder (ms-marco-MiniLM-L-6-v2) : lent mais précis, re-score chaque
   paire (query, chunk) en attention croisée et garde top_k=3.

Le cross-encoder voit la query et le chunk ensemble, donc il capture des
relations sémantiques fines que les bi-encoders ratent.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model = None
_lock = threading.Lock()
_disabled = False


def _get_model():
    """Charge le CrossEncoder paresseusement (~80 Mo)."""
    global _model, _disabled
    if _model is not None or _disabled:
        return _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from sentence_transformers import CrossEncoder
            _model = CrossEncoder(RERANKER_MODEL)
            logger.info("Reranker chargé : %s", RERANKER_MODEL)
        except Exception as exc:
            logger.error("Reranker indisponible : %s", exc)
            _disabled = True
    return _model


def rerank(
    query: str,
    candidates: list[dict],
    *,
    top_k: int = 3,
) -> list[dict]:
    """Re-trie les candidats RAG par score CrossEncoder, garde top_k.

    Chaque candidat doit avoir au moins {'text': str}. Le score CrossEncoder
    remplace 'score' (les anciens scores cosinus deviennent 'score_bi').
    """
    if not candidates:
        return []
    model = _get_model()
    if model is None:
        return candidates[:top_k]

    pairs = [(query, c["text"]) for c in candidates]
    try:
        scores = model.predict(pairs)
    except Exception as exc:
        logger.warning("CrossEncoder.predict a échoué : %s", exc)
        return candidates[:top_k]

    reranked = []
    for cand, score in zip(candidates, scores):
        item = dict(cand)
        if "score" in item:
            item["score_bi"] = item["score"]
        item["score"] = float(score)
        reranked.append(item)

    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked[:top_k]
