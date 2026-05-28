"""Extraction d'entités via NER CamemBERT (vu en Séance 4 — pipelines HF).

Remplace l'extraction par regex pure : à partir d'un message libre comme
"Je suis Jean Dupont, mon billet est TRV-2026-AB12CD, né le 14/03/1995",
on récupère :
- prenom, nom (NER CamemBERT, entité PER)
- numero_billet (regex spécifique, filet de sécurité conservé)
- date (regex + dateparser)

Le modèle est chargé paresseusement au premier appel (~440 Mo).
"""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

NER_MODEL = "Jean-Baptiste/camembert-ner"

_pipe = None
_lock = threading.Lock()
_disabled = False

# Regex finales (filets de sécurité même si NER tombe)
_BILLET_RE = re.compile(r"\bTRV-\d{4}-[A-Z0-9]{4,}\b")
_DATE_PATTERNS = [
    (re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"), "dmy"),
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "ymd"),
]


def _get_pipeline():
    global _pipe, _disabled
    if _pipe is not None or _disabled:
        return _pipe
    with _lock:
        if _pipe is not None:
            return _pipe
        try:
            from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
            tok = AutoTokenizer.from_pretrained(NER_MODEL)
            mdl = AutoModelForTokenClassification.from_pretrained(NER_MODEL)
            _pipe = pipeline(
                "ner", model=mdl, tokenizer=tok,
                aggregation_strategy="simple",
            )
            logger.info("NER CamemBERT chargé : %s", NER_MODEL)
        except Exception as exc:
            logger.error("NER indisponible : %s", exc)
            _disabled = True
    return _pipe


def _extract_date(text: str) -> Optional[str]:
    """Renvoie une date au format ISO YYYY-MM-DD si trouvée."""
    for rgx, fmt in _DATE_PATTERNS:
        m = rgx.search(text)
        if not m:
            continue
        try:
            if fmt == "dmy":
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y < 100:
                    y += 2000 if y < 50 else 1900
            else:  # ymd
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return datetime(y, mo, d).date().isoformat()
        except ValueError:
            continue
    return None


def extract_entities(text: str) -> dict:
    """Extrait {prenom, nom, numero_billet, date_iso} d'un message libre.

    Toutes les clés sont optionnelles (None si non trouvé).
    """
    out: dict = {"prenom": None, "nom": None, "numero_billet": None, "date_iso": None}

    if not text:
        return out

    # 1) Numéro de billet : regex (filet de sécurité, insensible à la casse)
    m = _BILLET_RE.search(text.upper())
    if m:
        out["numero_billet"] = m.group(0)

    # 2) Date : regex multi-format
    d = _extract_date(text)
    if d:
        out["date_iso"] = d

    # 3) Personne : NER CamemBERT
    pipe = _get_pipeline()
    if pipe is None:
        return out
    try:
        ents = pipe(text)
    except Exception as exc:
        logger.warning("NER inference a échoué : %s", exc)
        return out

    persons = [e for e in ents if e.get("entity_group") == "PER"]
    if persons:
        # Prendre la plus longue / plus confiante
        best = max(persons, key=lambda e: (e.get("score", 0), len(e.get("word", ""))))
        tokens = best.get("word", "").strip().split()
        if len(tokens) >= 2:
            out["prenom"] = tokens[0]
            out["nom"] = " ".join(tokens[1:])
        elif len(tokens) == 1:
            # Une seule partie : on la met en nom par défaut
            out["nom"] = tokens[0]

    return out
