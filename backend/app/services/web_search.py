"""Recherche web DuckDuckGo (exigence pédagogique du SAE2).

Utilise la lib `ddgs` (fork maintenu de duckduckgo-search) qui rotate entre
plusieurs backends DDG (api, html, lite) pour contourner le rate-limiting.

Tag affiché côté chatbot : `web_search` (= DuckDuckGo).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


# Mots-clés qui déclenchent une recherche web (versions sans accents)
SEARCH_TRIGGERS = (
    # Tarifs / prix
    "prix", "coute", "cout", "tarif", "combien", "couterait",
    # Grèves / trafic
    "greve", "trafic", "perturbation", "annulation de train", "annulation de vol",
    # Météo / climat
    "meteo", "temps", "climat", "temperature", "pluie", "soleil", "neige",
    # Événements / actualité
    "evenement", "festival", "concert", "match",
    "actualite", "recent", "derniere", "dernieres", "info ",
    # Formalités voyage
    "visa", "passeport", "vaccin", "covid",
    # États
    "ouvert", "ferme", "fermeture",
    # Compagnies / nouveauté
    "nouvelle ligne", "compagnie",
)


def _strip_accents(s: str) -> str:
    """Retire les accents pour matcher 'meteo' / 'météo' / 'metéo' indifféremment."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def should_search(message: str) -> bool:
    """Détecte si la question justifie une recherche web (insensible aux accents)."""
    m = _strip_accents(message.lower())
    return any(t in m for t in SEARCH_TRIGGERS)


def search(query: str, max_results: int = 4) -> list[dict]:
    """Recherche DuckDuckGo via la lib `ddgs` (multi-backend, gère le rate-limit)."""
    try:
        from ddgs import DDGS
    except ImportError:
        logger.warning("ddgs non installé")
        return []

    backends_tried = []
    # ddgs gère automatiquement la rotation entre 'auto', 'html', 'lite', 'duckduckgo'
    # On essaie plusieurs backends explicitement pour maximiser la chance de succès
    for backend in ("auto", "html", "lite", "duckduckgo"):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query=query,
                    region="fr-fr",
                    safesearch="moderate",
                    max_results=max_results,
                    backend=backend,
                ))
            if results:
                logger.info("DuckDuckGo (%s) : %d résultats pour '%s'", backend, len(results), query)
                return [
                    {
                        "title": r.get("title", "")[:120],
                        "body": (r.get("body") or r.get("content") or "")[:400],
                        "href": r.get("href") or r.get("url", ""),
                    }
                    for r in results
                ]
            backends_tried.append(backend)
        except Exception as exc:
            logger.debug("DDG backend %s failed: %s", backend, exc)
            backends_tried.append(backend)
            continue

    logger.warning("DuckDuckGo : aucun backend n'a renvoyé de résultat (essayés: %s)", backends_tried)
    return []


def format_for_prompt(results: list[dict]) -> str:
    """Formate les résultats DuckDuckGo pour injection dans le prompt Gemini.

    Inclut explicitement les URL et instruit Gemini de citer en Markdown cliquable.
    """
    if not results:
        return ""
    lines = [
        "Résultats de recherche DuckDuckGo (à utiliser pour répondre) :",
        "",
    ]
    for i, r in enumerate(results, 1):
        title = r["title"][:120].strip()
        body = re.sub(r"\s+", " ", r["body"]).strip()
        url = r.get("href", "")
        lines.append(f"Source {i} :")
        lines.append(f"  Titre : {title}")
        lines.append(f"  URL   : {url}")
        lines.append(f"  Extrait : {body}")
        lines.append("")
    lines.append(
        "INSTRUCTIONS pour citer ces sources : utilise UNIQUEMENT le format Markdown "
        "cliquable [titre court](URL) dans le corps de ta réponse. JAMAIS de notation "
        "type [1], [2], [3]. Cite 1 à 3 sources max, en intégrant les liens naturellement "
        "dans tes phrases."
    )
    return "\n".join(lines)
