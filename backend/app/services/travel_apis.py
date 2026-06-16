"""APIs voyage temps réel — données structurées que ni le LLM ni le RAG ne peuvent fournir.

Le LLM (Gemini) et le RAG sont figés dans le temps : ils ne connaissent ni la météo
d'aujourd'hui, ni l'heure qu'il est, ni le taux de change du jour. Ce module comble
ce trou avec deux APIs gratuites et sans clé :

- Open-Meteo  : météo actuelle + heure locale + fuseau d'une ville (geocoding + forecast)
- Frankfurter : taux de change du jour (Banque centrale européenne)

Les infos *stables* (capitale, langue, monnaie nominale d'un pays) ne sont PAS ici :
Gemini les connaît déjà depuis son entraînement.

API publique : build_context(message, city) -> (texte_pour_prompt, liste_apis_utilisées)
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0
_HEADERS = {"User-Agent": "voyage-assistant-sae2/1.0"}

# Déclencheurs (sans accents : on normalise le message avant de tester)
_WEATHER_TRIGGERS = (
    "meteo", "temps qu", "quel temps", "temperature", "climat", "pluie", "soleil",
    "neige", "fait-il", "fait il", "degre", "chaud", "froid", "orage", "vent", "ensoleille",
)
_TIME_TRIGGERS = (
    "heure", "quelle heure", "decalage", "fuseau", "heure locale", "heure est-il", "heure est il",
)
_CURRENCY_TRIGGERS = (
    "convert", "conversion", "taux", "change ", "combien font", "combien fait",
    "vaut", "en euro", "en dollar", "en yen", "en livre",
)

# Codes météo WMO -> description française
_WMO = {
    0: "ciel dégagé", 1: "globalement dégagé", 2: "partiellement nuageux", 3: "couvert",
    45: "brouillard", 48: "brouillard givrant",
    51: "bruine légère", 53: "bruine", 55: "bruine dense",
    56: "bruine verglaçante", 57: "bruine verglaçante dense",
    61: "pluie faible", 63: "pluie modérée", 65: "pluie forte",
    66: "pluie verglaçante", 67: "pluie verglaçante forte",
    71: "neige faible", 73: "neige modérée", 75: "neige forte", 77: "grésil",
    80: "averses faibles", 81: "averses", 82: "averses violentes",
    85: "averses de neige", 86: "fortes averses de neige",
    95: "orage", 96: "orage avec grêle", 99: "orage violent avec grêle",
}

# Devises : noms/symboles FR -> code ISO 4217
_CURRENCIES = {
    "euro": "EUR", "euros": "EUR", "eur": "EUR", "€": "EUR",
    "dollar": "USD", "dollars": "USD", "usd": "USD", "$": "USD",
    "yen": "JPY", "yens": "JPY", "jpy": "JPY", "¥": "JPY",
    "livre": "GBP", "livres": "GBP", "gbp": "GBP", "sterling": "GBP", "£": "GBP",
    "franc suisse": "CHF", "chf": "CHF",
    "dollar canadien": "CAD", "cad": "CAD",
    "yuan": "CNY", "cny": "CNY", "renminbi": "CNY",
    "roupie": "INR", "inr": "INR",
    "real": "BRL", "brl": "BRL",
    "won": "KRW", "krw": "KRW",
    "zloty": "PLN", "pln": "PLN",
    "rouble": "RUB", "rub": "RUB",
    "livre turque": "TRY", "try": "TRY",
    "dollar australien": "AUD", "aud": "AUD",
    "peso mexicain": "MXN", "mxn": "MXN",
}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    return _strip_accents(s.lower())


# Ville après une préposition : on capture une suite de mots Capitalisés
# ("New York", "San Francisco", "Barcelone"). Comme les mots parasites
# ("en ce moment", "aujourd'hui") sont en minuscules, la capture s'arrête
# naturellement avant eux.
_PREP_CITY = re.compile(
    r"(?:à|a|pour|vers|de|sur|dans|en)\s+"
    r"([A-ZÀ-Ÿ][\wÀ-ÿ'’-]+(?:[ -][A-ZÀ-Ÿ][\wÀ-ÿ'’-]+){0,3})"
)


def _extract_city(message: str) -> Optional[str]:
    """Extrait un nom de ville d'un message (séquence de mots capitalisés après une préposition)."""
    m = _PREP_CITY.search(message)
    if m:
        return m.group(1).strip().rstrip("?.,!")
    return None


# =====================================================================
# Open-Meteo : géocodage -> météo + heure locale
# =====================================================================
def _geocode(city: str) -> Optional[dict]:
    """Ville -> {name, country, lat, lon, timezone} via l'API geocoding Open-Meteo."""
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS) as client:
            r = client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "fr", "format": "json"},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("Open-Meteo geocoding échec (%s) : %s", city, exc)
        return None
    results = data.get("results") or []
    if not results:
        return None
    g = results[0]
    return {
        "name": g.get("name", city),
        "country": g.get("country", ""),
        "lat": g.get("latitude"),
        "lon": g.get("longitude"),
        "timezone": g.get("timezone", "auto"),
    }


def get_weather_and_time(city: str) -> Optional[dict]:
    """Météo actuelle + heure locale d'une ville (un geocoding + un forecast)."""
    geo = _geocode(city)
    if not geo or geo["lat"] is None:
        return None
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS) as client:
            r = client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": geo["lat"],
                    "longitude": geo["lon"],
                    "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                    "timezone": "auto",
                },
            )
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("Open-Meteo forecast échec (%s) : %s", city, exc)
        return None
    cur = data.get("current") or {}
    offset_h = data.get("utc_offset_seconds", 0) / 3600
    return {
        "city": geo["name"],
        "country": geo["country"],
        "temperature": cur.get("temperature_2m"),
        "ressenti": cur.get("apparent_temperature"),
        "vent": cur.get("wind_speed_10m"),
        "condition": _WMO.get(cur.get("weather_code"), "conditions inconnues"),
        "heure_locale": (cur.get("time", "") or "").replace("T", " à "),
        "timezone": data.get("timezone", ""),
        "utc_offset_h": offset_h,
    }


# =====================================================================
# Frankfurter : taux de change du jour
# =====================================================================
def _detect_currencies(message: str) -> Optional[tuple[float, str, str]]:
    """Extrait (montant, devise_source, devise_cible) d'un message, ou None."""
    m = _norm(message)

    # Devises citées, dans l'ordre d'apparition
    found: list[tuple[int, str]] = []
    for name, code in _CURRENCIES.items():
        idx = m.find(name)
        if idx != -1:
            found.append((idx, code))
    found.sort()
    # Dédoublonne en gardant l'ordre
    codes: list[str] = []
    for _, code in found:
        if code not in codes:
            codes.append(code)
    if not codes:
        return None

    # Montant (premier nombre du message, ex "100", "49,50", "1 200")
    amount_match = re.search(r"(\d[\d\s]*(?:[.,]\d+)?)", m)
    amount = 1.0
    if amount_match:
        raw = amount_match.group(1).replace(" ", "").replace(",", ".")
        try:
            amount = float(raw)
        except ValueError:
            amount = 1.0

    # "X en Y" -> la cible est après "en"
    base = codes[0]
    target = codes[1] if len(codes) > 1 else ("EUR" if base != "EUR" else "USD")
    en_match = re.search(r"\ben\s+([a-z€$£¥]+)", m)
    if en_match:
        word = en_match.group(1)
        for name, code in _CURRENCIES.items():
            if name.startswith(word) or word.startswith(name):
                target = code
                if base == target:
                    base = next((c for c in codes if c != target), "EUR")
                break
    return amount, base, target


def convert_currency(amount: float, base: str, target: str) -> Optional[dict]:
    if base == target:
        return None
    # Deux hosts Frankfurter : si l'un renvoie une erreur transitoire (520 Cloudflare),
    # on bascule sur l'autre avant d'abandonner.
    data = None
    for host in ("https://api.frankfurter.dev/v1/latest", "https://api.frankfurter.app/latest"):
        try:
            with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS) as client:
                r = client.get(host, params={"base": base, "symbols": target})
                r.raise_for_status()
                data = r.json()
            break
        except Exception as exc:
            logger.warning("Frankfurter échec (%s, %s->%s) : %s", host, base, target, exc)
            continue
    if data is None:
        return None
    rate = (data.get("rates") or {}).get(target)
    if rate is None:
        return None
    return {
        "amount": amount,
        "base": base,
        "target": target,
        "rate": rate,
        "converted": round(amount * rate, 2),
        "date": data.get("date", ""),
    }


# =====================================================================
# Orchestration : détecte l'intention, appelle les bonnes APIs
# =====================================================================
def build_context(message: str, fallback_city: Optional[str] = None) -> tuple[str, list[str]]:
    """Retourne (bloc de contexte pour le prompt Gemini, liste des APIs utilisées).

    La ville météo/heure est extraite du message ; à défaut on utilise `fallback_city`
    (typiquement la destination du billet déjà vérifié).
    """
    m = _norm(message)
    blocks: list[str] = []
    used: list[str] = []

    wants_weather = any(t in m for t in _WEATHER_TRIGGERS)
    wants_time = any(t in m for t in _TIME_TRIGGERS)
    city = _extract_city(message) or fallback_city
    if (wants_weather or wants_time) and city:
        wt = get_weather_and_time(city)
        if wt:
            used.append("meteo")
            sign = "+" if wt["utc_offset_h"] >= 0 else ""
            blocks.append(
                "DONNÉES MÉTÉO & HEURE EN TEMPS RÉEL (source Open-Meteo, fiables, à utiliser) :\n"
                f"- Lieu : {wt['city']}{', ' + wt['country'] if wt['country'] else ''}\n"
                f"- Heure locale actuelle : {wt['heure_locale']} (fuseau {wt['timezone']}, UTC{sign}{wt['utc_offset_h']:g})\n"
                f"- Température : {wt['temperature']} °C (ressenti {wt['ressenti']} °C)\n"
                f"- Conditions : {wt['condition']}\n"
                f"- Vent : {wt['vent']} km/h"
            )

    if any(t in m for t in _CURRENCY_TRIGGERS):
        cur = _detect_currencies(message)
        if cur:
            conv = convert_currency(*cur)
            if conv:
                used.append("change")
                blocks.append(
                    "TAUX DE CHANGE DU JOUR (source Frankfurter / BCE, à utiliser) :\n"
                    f"- {conv['amount']:g} {conv['base']} = {conv['converted']:g} {conv['target']} "
                    f"(taux : 1 {conv['base']} = {conv['rate']:g} {conv['target']}, au {conv['date']})"
                )

    return ("\n\n".join(blocks), used)
