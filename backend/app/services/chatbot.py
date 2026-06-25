from __future__ import annotations

import logging
import random
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from sqlalchemy import func as sqlfunc

from app.config import settings
from app.models import Billet, ChatMessage, Reclamation, Route, Trajet, User
from app.services import gemini, ner, rag, reranker, travel_apis, web_search
from app.services.i18n import t
from app.services.identity import verify_billet_dob, verify_billet_identity
from app.services.numeros import generate_numero_reclamation

logger = logging.getLogger(__name__)

import html
import re
import unicodedata


def _norm(s: str) -> str:
    """Minuscule sans accents, pour comparaisons robustes."""
    return "".join(
        c for c in unicodedata.normalize("NFD", (s or "").lower())
        if unicodedata.category(c) != "Mn"
    ).strip()

GREETINGS = {"bonjour", "salut", "hello", "hey", "coucou", "bonsoir", "yo", "hi"}
THANKS = {"merci", "thanks", "thx", "remercie"}
BYE = {"au revoir", "bye", "ciao", "à bientôt", "à plus", "salut"}

QUICK_REPLIES_HOME = [
    "Rechercher un voyage",
    "Mon voyage a un problème",
    "Modifier ma réservation",
    "Faire une réclamation",
    "Poser une question",
]

# Mots-clés déclenchant la recherche conversationnelle de voyage (slot-filling).
_SEARCH_KEYWORDS = (
    "rechercher un voyage", "recherche un voyage", "chercher un voyage",
    "je veux aller", "je voudrais aller", "j'aimerais aller", "je souhaite aller",
    "aller à", "aller a", "aller en", "aller au", "partir à", "partir a",
    "partir pour", "partir en", "trouver un trajet", "trouver un voyage",
    "réserver un voyage", "reserver un voyage", "billet pour", "trajet pour",
    "voyage à", "voyager à",
    # anglais
    "i want to go", "i'd like to go", "i would like to go", "go to", "travel to",
    "trip to", "ticket to", "fly to", "i want to travel", "search a trip", "find a trip",
    # espagnol
    "quiero ir a", "ir a", "me gustaría ir", "viajar a", "quiero viajar",
    "billete para", "buscar un viaje", "un viaje a",
)

# Mode de transport -> type BDD, pour repérer le transport dans une phrase de recherche.
_TRANSPORT_MAP = {
    "avion": "avion", "vol": "avion", "aérien": "avion", "aerien": "avion",
    "train": "train", "tgv": "train", "eurostar": "train", "ter": "train",
    "bateau": "bateau", "ferry": "bateau", "traversée": "bateau",
    "bus": "bus", "autocar": "bus", "car": "bus", "flixbus": "bus",
}

# Mots-clés des flows : utilisés pour détecter un changement de flow en plein
# parcours d'identité (l'utilisateur a manifestement renoncé au flow courant).
_FLOW_KEYWORDS = {
    "flow_retard": ("mon voyage a un problème", "problème avec mon voyage", "retard", "info trafic"),
    "flow_modif":  ("modifier ma réservation", "modifier mon billet", "changer mon billet", "changer ma résa"),
    "flow_recla":  ("faire une réclamation", "déposer une réclamation", "bagage perdu"),
}

# Insultes / langage agressif : on désescalade poliment sans répéter.
_OFFENSIVE_PATTERNS = re.compile(
    r"\b(con(nard|ne|ard)?|salop[ea]|enfoir[ée]|abruti[e]?|imb[ée]cile|crétin[e]?|nul(?:le|s)?\s+(?:à\s+chier|de\s+chez)|"
    r"merde|fuck|shit|sucker|asshole|bitch|t[ae]\s*gueul|ferme\s*ta|va\s*te\s+faire|nique|p[ée]d[ée]?|fdp)\b",
    re.IGNORECASE,
)

# Sujets dangereux / hors-périmètre transport.
_HARMFUL_PATTERNS = re.compile(
    r"\b(bombe|explosif|terroris(?:te|me)|arme|drogue|cocaïne|h[ée]ro[ïi]ne|cannabis|piratage|hack(?:er|ing)?|"
    r"phishing|malware|carte\s+bancaire\s+vol[ée]|fraude|contrefa[çc]on)\b",
    re.IGNORECASE,
)

# Tentatives d'injection de prompt (cas évidents).
_PROMPT_INJECTION = re.compile(
    r"(ignore\s+(?:tes?|les?)\s+(?:consignes?|instructions?|previous|prior)|"
    r"ignore\s+previous\s+instructions|"
    r"system\s*[:=]\s*nouveau\s+prompt|"
    r"###\s*system\s*[:=]|"
    r"jailbreak|do\s+anything\s+now|dan\s+mode|developer\s+mode|admin\s+mode|"
    r"r[ée]v[èe]le\s+(?:ton|tes)\s+(?:syst[èe]me|prompt|consigne)|"
    r"montre[\s-]moi\s+tous\s+les\s+billets|donne[\s-]moi\s+(?:tous\s+les\s+|l[ae]\s+liste\s+des\s+)billets)",
    re.IGNORECASE,
)

# Demandes d'accès à un billet par numéro sans passer par le flow guidé.
_BILLET_REFERENCE = re.compile(r"\bTRV-\d{4}-[A-Z0-9]{4,}\b", re.IGNORECASE)


def _extract_billet_number(message: str) -> str:
    """Extrait le numéro de billet d'une phrase libre.

    L'utilisateur écrit souvent « voici mon billet : TRV-2026-ABC123 » plutôt que
    le code seul : on récupère le motif TRV-AAAA-XXXX où qu'il soit dans la phrase,
    on le met en majuscules et on retire les espaces parasites. Repli : message
    entier nettoyé (compat. ancien comportement quand on colle juste le code)."""
    m = _BILLET_REFERENCE.search(message)
    if m:
        return m.group(0).upper().replace(" ", "")
    return message.strip().upper().replace(" ", "")


_DEST_KEYWORDS = (
    "destination", "où aller", "ou aller", "top", "populaire", "recommande",
    "conseil", "quelle ville", "quels endroits", "que visiter", "voyage à",
    "partir pour", "envie de",
)
_ROUTE_KEYWORDS = (
    "train", "avion", "bateau", "bus", "vol", "trajet", "ligne",
    "aller à", "aller en", "aller au", "comment aller", "comment se rendre",
    "dessert", "relie", "liaison", "navette",
)

# Prépositions introduisant une DESTINATION (« aller à/en/au X », « vers X »…).
# NB : « pour » seul est volontairement exclu (capte des compléments de but du
# genre « pour les vacances »). On garde « pour aller à/en/au ».
_DEST_PREP_RE = re.compile(
    r"\b(?:pour aller (?:à|a|au|aux|en)|aller (?:à|a|au|aux|en)|jusqu['’]?(?:à|a)|"
    r"destination(?: de)?|direction|vers|à|a|au|aux|en|pour|"
    r"go(?:ing)? to|travel to|fly to|trip to|ticket to|head(?:ing)? to|"
    r"ir a|viajar a|billete para)\s+",
    re.IGNORECASE,
)
# Prépositions introduisant un DÉPART.
_FROM_PREP_RE = re.compile(
    r"\b(?:au départ de|à partir de|en partant de|partant de|depuis|from|desde|de|du|d['’])\s*",
    re.IGNORECASE,
)

# Mots qui ARRÊTENT la capture d'un nom de lieu (prépositions, liaisons, langues).
_SCAN_STOP = {
    "pour", "depuis", "pendant", "durant", "afin", "avec", "via", "car", "puis",
    "ensuite", "et", "ou", "mais", "donc", "a", "au", "aux", "en", "vers", "jusqu",
    "direction", "un", "une", "this", "for", "with", "and", "or", "to", "from",
    "para", "desde", "con", "porque", "because", "y",
    # démonstratifs / possessifs (ne font pas partie d'un nom de lieu)
    "ce", "cet", "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes",
    "notre", "nos", "votre", "vos", "leur", "leurs", "that", "these", "those",
    "my", "mi", "mis", "este", "esta", "estos",
}
# Mots de temps / motif → ce n'est pas un lieu.
_TIME_PURPOSE = {
    "vacances", "vacance", "ete", "hiver", "printemps", "automne", "weekend",
    "week-end", "semaine", "semaines", "mois", "jour", "jours", "journee",
    "journees", "travail", "boulot", "affaires", "business", "demain",
    "aujourdhui", "noel", "paques", "nuit", "soir", "matin", "pont", "ponts",
    "summer", "winter", "spring", "autumn", "holiday", "holidays", "vacation",
    "work", "verano", "invierno",
}
# Petits mots de liaison tolérés À L'INTÉRIEUR d'un nom (Le Havre, La Rochelle, Saint-…).
_SMALL_INTERNAL = {"de", "du", "des", "le", "la", "les", "d", "saint", "sainte", "san", "santa", "el", "los", "las"}


def _scan_place(rest: str) -> str | None:
    """À partir du texte qui suit une préposition, isole un nom de lieu plausible
    (s'arrête au premier mot de liaison / temps / transport)."""
    place: list[str] = []
    for raw in rest.split():
        tok = raw.strip("?.,!;:«»\"'’()")
        w = _norm(tok)
        if not w:
            break
        if w in _SCAN_STOP or w in _TIME_PURPOSE or w in _TRANSPORT_MAP:
            break
        place.append(tok)
        if len(place) >= 4:
            break
    while place and _norm(place[-1]) in _SMALL_INTERNAL:
        place.pop()
    out = " ".join(place).strip()
    return out or None


def _extract_destination(text: str) -> tuple[str | None, str | None]:
    """Extrait (arrivee, depart) depuis une phrase en langage naturel.

    Robuste : ignore les compléments de but/temps (« pour les vacances d'été »),
    gère « en/au/aux/vers » et les noms composés (Le Havre, La Rochelle)."""
    arrivee = None
    for m in _DEST_PREP_RE.finditer(text):
        cand = _scan_place(text[m.end():])
        if cand:
            arrivee = cand
            break
    depart = None
    for m in _FROM_PREP_RE.finditer(text):
        cand = _scan_place(text[m.end():])
        if cand:
            depart = cand
            break
    return arrivee, depart


# Alias de pays courants (EN/ES → nom FR du catalogue _CITY_TO_PAYS).
_COUNTRY_ALIASES = {
    "espagne": "Espagne", "spain": "Espagne", "espana": "Espagne",
    "france": "France",
    "italie": "Italie", "italy": "Italie", "italia": "Italie",
    "portugal": "Portugal",
    "allemagne": "Allemagne", "germany": "Allemagne", "deutschland": "Allemagne", "alemania": "Allemagne",
    "royaume-uni": "Royaume-Uni", "angleterre": "Royaume-Uni", "uk": "Royaume-Uni",
    "england": "Royaume-Uni", "royaume uni": "Royaume-Uni",
    "belgique": "Belgique", "belgium": "Belgique",
    "pays-bas": "Pays-Bas", "netherlands": "Pays-Bas", "hollande": "Pays-Bas", "pays bas": "Pays-Bas",
    "suisse": "Suisse", "switzerland": "Suisse",
    "maroc": "Maroc", "morocco": "Maroc",
    "etats-unis": "États-Unis", "usa": "États-Unis", "united states": "États-Unis", "etats unis": "États-Unis",
}


def _match_country(name: str) -> str | None:
    """Si `name` désigne un pays, renvoie son nom FR (sinon None)."""
    n = _norm(name)
    if n in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[n]
    try:
        from app.routers.trajets import _CITY_TO_PAYS
        pays_set = {_norm(p): p for p in _CITY_TO_PAYS.values()}
        if n in pays_set:
            return pays_set[n]
    except Exception:
        pass
    return None


def _cities_in_country(pays: str, n: int = 6) -> list[str]:
    """Quelques villes du catalogue situées dans `pays` (pour suggestion)."""
    try:
        from app.routers.trajets import _CITY_TO_PAYS
    except Exception:
        return []
    target = _norm(pays)
    villes = [c.title() for c, p in _CITY_TO_PAYS.items() if _norm(p) == target]
    return villes[:n]


def _detect_transport(text: str) -> str | None:
    """Repère un mode de transport (avion/train/bateau/bus) dans une phrase."""
    low = text.lower()
    for word, ttype in _TRANSPORT_MAP.items():
        if re.search(rf"\b{re.escape(word)}\b", low):
            return ttype
    return None


def _is_search_intent(message_lower: str) -> bool:
    """Détecte une intention de recherche de voyage."""
    return any(k in message_lower for k in _SEARCH_KEYWORDS)


# Clés exactes d'un item GET /trajets exposées au front (le reste est ignoré côté UI).
_TRAJET_OUT_KEYS = (
    "id", "type", "compagnie", "classe", "date_depart", "date_arrivee",
    "depart", "arrivee", "prix", "stops", "escales",
    "has_wifi", "has_prise", "retard_minutes", "places_dispo",
)


def _search_trajets_results(
    db: Session, depart: str, arrivee: str, limit: int = 8
) -> list[dict]:
    """Recherche des trajets (tous modes) et renvoie des dicts shape GET /trajets.

    Réutilise la logique du routeur trajets (_search_routes + _make_trajet_out)
    pour garantir un format identique. On ne pré-filtre PAS par transport :
    le front filtre côté client."""
    from datetime import timedelta, timezone

    from app.routers.trajets import _make_trajet_out, _search_routes

    date_dt = datetime.now(timezone.utc) + timedelta(days=1)
    routes = _search_routes(db, None, depart, arrivee, limit=40)
    trajets = [_make_trajet_out(r, date_dt) for r in routes]
    trajets.sort(key=lambda x: x.date_depart)
    out: list[dict] = []
    for tr in trajets[:limit]:
        d = tr.model_dump(mode="json")
        out.append({k: d[k] for k in _TRAJET_OUT_KEYS})
    return out


_MY_BILLETS_KEYWORDS = (
    "mes billets", "mes réservations", "mes reservations", "mes voyages",
    "mes trajets", "ma réservation", "ma reservation", "mon billet",
    "mon voyage", "mon trajet", "prochain voyage", "prochaine réservation",
    # Synonymes par mode de transport (« combien dure mon vol ? », « mon train part quand ? »)
    "mon vol", "mes vols", "mon train", "mes trains", "mon avion",
    "mon bus", "mon car", "mon bateau", "mon ferry", "ma ligne",
    "mon départ", "mon retour", "mon embarquement", "ma destination",
    "tout est ok", "tout va bien", "confirme", "confirmé", "vérifier ma",
    "verifier ma", "statut de ma", "état de ma", "etat de ma",
    "j'ai réservé", "j ai reserve", "j'ai booké", "quels sont mes",
    "qu'est-ce que j'ai", "qu est ce que j ai",
    "voir mes réservations", "voir mes reservations",
    "mon prochain voyage", "ma prochaine réservation",
)

_IATA_RE = re.compile(r'\s+[A-Z]{2,4}(?=\s|$)')
_STATION_SUFFIXES = (
    " Hbf", " Hauptbahnhof", " Termini", " Centrale", " Centraal",
    " Sants", " Atocha", " St Pancras", " Victoria", " Waterloo",
    " Rive Droite", " Rive Gauche", " Matabiau", " Part-Dieu",
    " Perrache", " Montparnasse", " Saint-Charles", " Saint-Lazare",
    " Gare de Lyon", " Oriente", " Porta Susa", " Santa Lucia",
)


def _build_user_billets_context(db: Session, user: User) -> str:
    """Formate les réservations d'un utilisateur connecté pour injection dans Gemini."""
    billets = (
        db.query(Billet)
        .filter(Billet.user_id == user.id)
        .order_by(Billet.created_at.desc())
        .limit(10)
        .all()
    )
    if not billets:
        return f"L'utilisateur {user.prenom} {user.nom} n'a aucune réservation."
    JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    MOIS  = ["janvier", "février", "mars", "avril", "mai", "juin",
             "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    lines = [
        f"RÉSERVATIONS DE {user.prenom.upper()} {user.nom.upper()} (utilisateur connecté — identité déjà vérifiée) :"
    ]
    for b in billets:
        t = b.trajet
        if t is None:
            lines.append(f"- Billet {b.numero_billet} · trajet introuvable · statut : {b.statut}")
            continue
        dd = t.date_depart
        date_fr = f"{JOURS[dd.weekday()]} {dd.day} {MOIS[dd.month-1]} {dd.year} à {dd:%H:%M}"
        retard = f", {t.retard_minutes} min de retard" if t.retard_minutes else ""
        duree_txt = ""
        if t.date_arrivee:
            duree_min = int((t.date_arrivee - t.date_depart).total_seconds() // 60)
            if duree_min > 0:
                dh, dm = divmod(duree_min, 60)
                duree_str = f"{dh} h {dm:02d}" if dh else f"{dm} min"
                duree_txt = f" · arrivée prévue à {t.date_arrivee:%H:%M} · durée du trajet {duree_str}"
        lines.append(
            f"- {b.numero_billet} · {t.type.capitalize()} {t.compagnie} · "
            f"{t.depart} → {t.arrivee} · {date_fr}{duree_txt} · "
            f"classe {t.classe or 'Standard'} · {b.prix_paye:.0f} € · statut : {b.statut}{retard}"
        )
    return "\n".join(lines)


def _clean_city_name(name: str) -> str:
    """Supprime codes IATA et suffixes de gare pour l'affichage dans le chatbot."""
    c = _IATA_RE.sub('', name).strip()
    for sfx in _STATION_SUFFIXES:
        if c.lower().endswith(sfx.lower()):
            c = c[:-len(sfx)].strip()
    return c


def _query_routes_for_dest(db: Session, arrivee: str, depart: str | None = None, transport: str | None = None) -> str:
    """Requête la table routes pour trouver les liaisons vers `arrivee`."""
    q = db.query(Route).filter(Route.arrivee.ilike(f"%{arrivee}%"))
    if depart:
        q = q.filter(Route.depart.ilike(f"%{depart}%"))
    if transport:
        q = q.filter(Route.type == transport)
    rows = q.order_by(sqlfunc.random()).limit(8).all()
    if not rows:
        return ""
    lines = [
        f"- {r.type.capitalize()} {r.compagnie} : {_clean_city_name(r.depart)} → {_clean_city_name(r.arrivee)} (à partir de {r.base_price:.0f} €)"
        for r in rows
    ]
    return "ROUTES DISPONIBLES DANS NOTRE CATALOGUE :\n" + "\n".join(lines)


def _query_top_destinations(db: Session, depart: str = "Paris", n: int = 10) -> str:
    """Renvoie les n destinations les plus représentées depuis `depart`."""
    rows = (
        db.query(Route.arrivee, sqlfunc.count(Route.id).label("nb"), sqlfunc.min(Route.base_price).label("prix"))
        .filter(Route.depart.ilike(f"%{depart}%"))
        .group_by(Route.arrivee)
        .order_by(sqlfunc.random())
        .limit(n * 5)
        .all()
    )
    seen: set[str] = set()
    selected = []
    for r in rows:
        name = _clean_city_name(r.arrivee).lower()
        if name not in seen:
            seen.add(name)
            selected.append(r)
        if len(selected) >= n:
            break
    if not selected:
        return ""
    lines = [f"- {_clean_city_name(r.arrivee)} · dès {r.prix:.0f} €" for r in selected]
    return f"DESTINATIONS DISPONIBLES AU DÉPART DE {depart.upper()} :\n" + "\n".join(lines)


def _sanitize_user_input(s: str) -> str:
    """Nettoie l'entrée utilisateur : trim, suppression des tags HTML, normalisation."""
    if not s:
        return ""
    # Supprime les tags HTML potentiels (XSS / injection visuelle)
    s = re.sub(r"<[^>]+>", " ", s)
    # Décode les entités HTML (au cas où)
    s = html.unescape(s)
    # Normalise les espaces et casse les caractères de contrôle
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _detect_flow_switch(message_lower: str) -> str | None:
    """Détecte si le message ressemble à un nouveau flow alors qu'on est en plein parcours."""
    for flow, keywords in _FLOW_KEYWORDS.items():
        if any(k in message_lower for k in keywords):
            return flow
    return None


def _greet_prefix() -> str:
    h = datetime.now().hour
    if 5 <= h < 12:
        return "Bonjour"
    if 12 <= h < 18:
        return "Bon après-midi"
    if 18 <= h < 23:
        return "Bonsoir"
    return "Bonsoir"


def _detect_intent(message: str, context: dict[str, Any]) -> str:
    if context.get("awaiting"):
        return context["awaiting"]

    m = message.lower().strip()
    # Pure greeting : seulement le mot, ou suivi d'une simple ponctuation finale
    pure_greeting = any(
        m == g or m == g + " !" or m == g + "." or m == g + "!"
        for g in GREETINGS
    )
    if pure_greeting:
        return "greeting"
    if m in BYE:
        return "bye"
    if any(t == m or m.endswith(" " + t) for t in THANKS):
        return "thanks"
    # Flows BDD (prioritaires : nécessitent un parcours guidé)
    if any(k in m for k in ("retard", "annulé", "mon voyage a un problème", "problème avec mon voyage", "info trafic")):
        return "flow_retard"
    if any(k in m for k in ("modifier ma réservation", "modifier mon billet", "échanger mon billet", "changer mon billet", "changer ma résa")):
        return "flow_modif"
    if any(k in m for k in ("faire une réclamation", "faire une reclamation", "déposer une réclamation", "bagage perdu")):
        return "flow_recla"
    # Sinon Gemini gère tout (questions générales, demandes d'info, etc.)
    return "freeform"


# Noms de mois FR / EN / ES (avec et sans accents) -> numéro de mois.
_MONTHS = {
    # français
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "aout": 8, "août": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
    # anglais
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # espagnol
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
_MONTHS_ALT = "|".join(sorted((re.escape(m) for m in _MONTHS), key=len, reverse=True))
# Date numérique : 10/01/2004, 10-01-2004, 10.01.2004, 10 01 2004
_DATE_NUM = re.compile(r"\b(\d{1,2})[\s/.\-](\d{1,2})[\s/.\-](\d{4})\b")
# Date ISO : 2004-01-10
_DATE_ISO = re.compile(r"\b(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})\b")
# Date en lettres FR/ES : « 10 janvier 2004 », « 10 de enero de 2004 »
_DATE_WORD = re.compile(
    r"\b(\d{1,2})(?:er|ère|ème|e|º|ª)?\s*(?:de\s+)?(" + _MONTHS_ALT + r")\.?\s*(?:de\s+|,\s*)?(\d{4})\b",
    re.IGNORECASE,
)
# Date en lettres EN : « January 10, 2004 » / « Jan 10 2004 »
_DATE_WORD_EN = re.compile(
    r"\b(" + _MONTHS_ALT + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE,
)


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_date_fr(s: str) -> date | None:
    """Extrait une date de naissance d'une phrase libre (FR/EN/ES).

    Accepte le code seul (« 10/01/2004 ») comme une phrase entière
    (« ma date de naissance est le 10 janvier 2004 », « I was born on January 10, 2004 »,
    « nací el 10 de enero de 2004 »). On cherche le motif n'importe où dans le texte,
    tous séparateurs et mois en toutes lettres confondus."""
    if not s:
        return None
    s = s.strip()

    m = _DATE_ISO.search(s)
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            return d

    m = _DATE_NUM.search(s)
    if m:
        d = _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))  # JJ MM AAAA
        if d:
            return d

    m = _DATE_WORD.search(s)
    if m:
        mois = _MONTHS.get(m.group(2).lower())
        if mois:
            d = _safe_date(int(m.group(3)), mois, int(m.group(1)))
            if d:
                return d

    m = _DATE_WORD_EN.search(s)
    if m:
        mois = _MONTHS.get(m.group(1).lower())
        if mois:
            d = _safe_date(int(m.group(3)), mois, int(m.group(2)))
            if d:
                return d

    return None


def _history_from_session(db: Session, session_id: str, limit: int = 10) -> list[dict]:
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in reversed(msgs)]


def _process_message_inner(
    db: Session,
    message: str,
    context: dict[str, Any],
    user: User | None,
    session_id: str | None,
    lang: str = "fr",
) -> dict[str, Any]:
    raw = message
    # Sanitization sauf pour les champs où l'on attend une valeur littérale (nom, etc.)
    # On garde la valeur brute pour `nom`/`prenom`/`date_naissance` car le strip change rien d'utile.
    message = _sanitize_user_input(raw)

    # 0. Entrée vide après sanitization
    if not message or len(message) < 1:
        return {
            "answer": t("Je n'ai pas reçu de message lisible. Pouvez-vous reformuler votre demande ?", lang),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME] if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 1. Trop court pour être interprétable hors d'un flow guidé
    if not context.get("awaiting") and len(message) < 2:
        return {
            "answer": t("Pouvez-vous préciser votre demande en quelques mots ? Je peux vous aider à modifier un billet, signaler un retard ou répondre à une question voyage.", lang),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
            "context": context,
            "tool_used": None,
        }

    # 2. Insulte / langage agressif → désescalade fixe (on évite Gemini pour ne pas amplifier)
    if _OFFENSIVE_PATTERNS.search(message):
        return {
            "answer": t(
                "Je comprends que vous puissiez être frustré, mais je ne peux pas répondre à ce type de langage. "
                "Je suis ici pour vous aider sur vos voyages — si vous avez un problème concret avec un billet, "
                "dites-moi ce qui ne va pas et je ferai de mon mieux pour le résoudre.",
                lang,
            ),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME] if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 3. Sujet dangereux / illégal hors-périmètre
    if _HARMFUL_PATTERNS.search(message):
        return {
            "answer": t(
                "Je suis l'assistant Voyage et je ne peux répondre qu'aux questions liées à vos déplacements "
                "(billets, horaires, destinations, démarches voyage). Pour le sujet que vous évoquez, "
                "merci de vous adresser aux autorités ou services compétents.",
                lang,
            ),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME] if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 4. Tentative d'injection de prompt
    if _PROMPT_INJECTION.search(message):
        return {
            "answer": t(
                "Mes consignes de sécurité ne sont pas modifiables. Je peux vous aider sur un billet précis "
                "après une vérification d'identité, ou répondre à vos questions de voyage.",
                lang,
            ),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME] if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 5. Mention d'un numéro de billet hors du flow guidé → on lance le
    # déverrouillage par date de naissance (chemin d'entrée « billet collé »).
    if not context.get("awaiting"):
        num_ref = _BILLET_REFERENCE.search(message)
        if num_ref:
            numero = num_ref.group(0).upper().replace(" ", "")
            return _start_billet_unlock(db, numero, context, user, lang=lang)

    # 6. Changement de flow en plein parcours d'identité : on demande confirmation
    if context.get("awaiting") in {"numero_billet", "date_naissance", "unlock_billet", "unlock_dob"}:
        switch = _detect_flow_switch(message.lower())
        if switch and switch != context.get("flow"):
            return {
                "answer": t(
                    "Vous étiez en train d'ouvrir un dossier. Voulez-vous abandonner ce parcours "
                    "et démarrer un nouveau ? Si oui, choisissez ci-dessous ; sinon je continue le parcours actuel.",
                    lang,
                ),
                "quick_replies": [t("Abandonner et recommencer", lang), t("Continuer le parcours actuel", lang)],
                "context": {
                    **context, "awaiting": "confirm_switch",
                    "pending_flow": switch, "resume_awaiting": context.get("awaiting"),
                },
                "tool_used": None,
            }

    if context.get("awaiting") == "confirm_switch":
        low = message.lower()
        if "abandon" in low or "recommencer" in low:
            new_flow = context.get("pending_flow")
            return {
                "answer": t("Très bien, on recommence. Donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).", lang),
                "quick_replies": [],
                "context": {"flow": new_flow, "awaiting": "numero_billet"},
                "tool_used": None,
            }
        resume = context.get("resume_awaiting", "numero_billet")
        msg_map = {
            "numero_billet": "votre numéro de billet (format TRV-2026-XXXXXX) ?",
            "unlock_billet": "votre numéro de billet (format TRV-2026-XXXXXX) ?",
            "date_naissance": "votre date de naissance au format JJ/MM/AAAA ?",
            "unlock_dob": "votre date de naissance au format JJ/MM/AAAA ?",
        }
        next_ctx = {k: v for k, v in context.items() if k not in ("pending_flow", "resume_awaiting")}
        next_ctx["awaiting"] = resume
        suite = t(msg_map.get(resume, msg_map["numero_billet"]), lang)
        return {
            "answer": t("Parfait, on continue. Reprenons : {suite}", lang, suite=suite),
            "quick_replies": [],
            "context": next_ctx,
            "tool_used": None,
        }

    intent = _detect_intent(message, context)
    prenom = (user.prenom if user else "").strip()

    # === Greetings ===
    if intent == "greeting":
        greet = t(_greet_prefix(), lang)
        salutation = f"{greet}{', ' + prenom if prenom else ''} ! "
        suite = t(random.choice([
            "Comment puis-je vous aider aujourd'hui ?",
            "Que puis-je faire pour vous ?",
            "En quoi puis-je vous être utile ?",
            "Sur quoi puis-je vous aider ?",
        ]), lang)
        return {
            "answer": salutation + suite,
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
            "context": {},
            "tool_used": None,
        }

    if intent == "thanks":
        return {
            "answer": t(random.choice([
                "Avec plaisir ! N'hésitez pas si vous avez d'autres questions.",
                "Je vous en prie. Autre chose pour ce voyage ?",
                "De rien ! Je reste à votre disposition.",
            ]), lang),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
            "context": {},
            "tool_used": None,
        }

    if intent == "bye":
        return {
            "answer": t(random.choice([
                "Bon voyage ! À bientôt.",
                "À bientôt sur Voyage Assistant !",
                "Bonne route et à très vite.",
            ]), lang),
            "quick_replies": [],
            "context": {},
            "tool_used": None,
        }

    # === Recherche conversationnelle (slot-filling) ===
    # On entre dans le flow recherche si l'intention est détectée et qu'on n'est
    # pas déjà au milieu d'un autre parcours guidé.
    if (
        not context.get("awaiting")
        and intent not in ("flow_retard", "flow_modif", "flow_recla", "greeting", "thanks", "bye")
        and _is_search_intent(message.lower())
    ):
        arrivee, depart_city = _extract_destination(message)
        transport = _detect_transport(message)
        date_dn = _parse_date_fr(message)
        search_ctx: dict[str, Any] = {"flow": "flow_search"}
        if arrivee:
            search_ctx["search_arrivee"] = arrivee
        if depart_city:
            search_ctx["search_depart"] = depart_city
        if transport:
            search_ctx["search_transport"] = transport
        if date_dn:
            search_ctx["search_date"] = date_dn.isoformat()
        return _run_search_flow(db, search_ctx, lang=lang)

    if context.get("awaiting") == "search_dest":
        arrivee, depart_city = _extract_destination(message)
        # Repli : si pas de préposition, on prend le message entier comme destination.
        if not arrivee:
            arrivee = message.strip().rstrip("?.,!")
        context.pop("awaiting", None)
        context["search_arrivee"] = arrivee
        if depart_city and not context.get("search_depart"):
            context["search_depart"] = depart_city
        tr = _detect_transport(message)
        if tr:
            context["search_transport"] = tr
        return _run_search_flow(db, context, lang=lang)

    if context.get("awaiting") == "search_depart":
        arrivee, depart_city = _extract_destination(message)
        # L'utilisateur peut changer de destination en cours de route.
        if arrivee:
            context["search_arrivee"] = arrivee
        if not depart_city:
            depart_city = message.strip().rstrip("?.,!")
        context.pop("awaiting", None)
        context["search_depart"] = depart_city
        tr = _detect_transport(message)
        if tr:
            context["search_transport"] = tr
        return _run_search_flow(db, context, lang=lang)

    # === Flows BDD (actions sensibles : déverrouillage par date de naissance) ===
    if intent in ("flow_retard", "flow_modif", "flow_recla") and not context.get("awaiting"):
        context["flow"] = intent

        # Fast-path : si un numéro de billet est déjà dans la phrase (NER ou regex),
        # on enchaîne directement vers le déverrouillage.
        try:
            ents = ner.extract_entities(message)
        except Exception as exc:
            logger.warning("NER extract a échoué : %s", exc)
            ents = {}
        numero = ents.get("numero_billet")
        if not numero:
            num_in_msg = _BILLET_REFERENCE.search(message)
            if num_in_msg:
                numero = num_in_msg.group(0).upper().replace(" ", "")
        if numero:
            return _start_billet_unlock(db, numero, context, user, lang=lang)

        context["awaiting"] = "unlock_billet"
        return {
            "answer": t("Bien sûr. Pour ouvrir votre dossier, donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).", lang),
            "quick_replies": [], "context": context, "tool_used": None,
        }

    if context.get("awaiting") == "unlock_billet":
        numero = _extract_billet_number(message)
        return _start_billet_unlock(db, numero, context, user, lang=lang)

    if context.get("awaiting") == "unlock_dob":
        dt = _parse_date_fr(message)
        if dt is None:
            return {
                "answer": t("Format de date invalide. Merci d'utiliser JJ/MM/AAAA (par exemple 14/03/1995).", lang),
                "quick_replies": [],
                "context": context,
                "tool_used": None,
            }
        numero = context.get("pending_billet")
        billet = verify_billet_dob(db, numero, dt) if numero else None
        if billet is None:
            return {
                "answer": t(
                    "Cette date de naissance ne correspond pas à ce billet. "
                    "Pour des raisons de sécurité, je ne peux pas donner suite. "
                    "Réessayez (par exemple 14/03/1995) ou contactez le service client.",
                    lang,
                ),
                "quick_replies": [],
                "context": context,
                "tool_used": "identity_check",
            }
        context.pop("awaiting", None)
        context.pop("pending_billet", None)
        return _unlock_and_act(db, billet, context, lang=lang)

    # === Choix d'une alternative pour modifier le billet ===
    if context.get("awaiting") == "pick_alt":
        alt_map = context.get("alt_map") or {}
        billet_id = context.get("billet_id")
        nouveau_trajet_id = alt_map.get(message.strip())
        billet = db.get(Billet, billet_id) if billet_id else None
        nouveau = db.get(Trajet, nouveau_trajet_id) if nouveau_trajet_id else None
        if billet is None or nouveau is None:
            return {
                "answer": t("Je n'ai pas reconnu cette option. Merci de cliquer sur l'un des choix proposés.", lang),
                "quick_replies": list(alt_map.keys()),
                "context": context,
                "tool_used": None,
            }
        places = billet.nb_places or 1
        if nouveau.places_dispo < places:
            return {
                "answer": t("Ce trajet vient d'être complet. Souhaitez-vous voir d'autres alternatives ?", lang),
                "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
                "context": {},
                "tool_used": "query_trajet",
            }
        # Effectue la modification
        ancien_trajet = billet.trajet
        ancien_trajet.places_dispo += places
        nouveau.places_dispo -= places
        billet.trajet_id = nouveau.id
        billet.prix_paye = nouveau.prix
        db.commit()
        db.refresh(billet)

        # Envoi du mail de confirmation avec nouveau PDF
        try:
            from app.services.billet_pdf import build_billet_pdf
            from app.services.email import send_confirmation_email
            JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
                    "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            dd = nouveau.date_depart
            date_fr = f"{JOURS[dd.weekday()]} {dd.day} {MOIS[dd.month - 1]} {dd.year} à {dd:%H:%M}"
            pdf = build_billet_pdf(
                numero_billet=billet.numero_billet,
                voyageur_nom=billet.user.nom,
                voyageur_prenom=billet.user.prenom,
                trajet_type=nouveau.type,
                depart=nouveau.depart,
                arrivee=nouveau.arrivee,
                date_depart=dd.strftime("%d/%m/%Y · %H:%M"),
                date_arrivee=nouveau.date_arrivee.strftime("%d/%m/%Y · %H:%M"),
                compagnie=nouveau.compagnie,
                classe=nouveau.classe or "Standard",
                prix_paye=billet.prix_paye,
                siege=billet.siege,
            )
            send_confirmation_email(
                to_email=billet.user.email,
                to_name=f"{billet.user.prenom} {billet.user.nom}",
                numero_billet=billet.numero_billet,
                trajet_resume=f"{nouveau.type.capitalize()} {nouveau.compagnie} · {nouveau.depart} → {nouveau.arrivee} · {date_fr}",
                chatbot_url=f"{settings.frontend_url}/assistant",
                pdf_bytes=pdf,
                montant=f"{billet.prix_paye:.2f} EUR",
                classe=nouveau.classe or "Standard",
                lang=lang,
            )
        except Exception as exc:
            logger.warning("Mail de modification échoué : %s", exc)

        return {
            "answer": t(
                "C'est fait ! Votre billet {numero} est maintenant sur le vol "
                "{compagnie} du {date} "
                "({depart} → {arrivee}). "
                "Nouveau montant : {prix} €. "
                "Un email de confirmation avec le billet mis à jour vient de partir. Autre chose ?",
                lang,
                numero=billet.numero_billet,
                compagnie=nouveau.compagnie,
                date=f"{nouveau.date_depart:%d/%m/%Y à %H:%M}",
                depart=nouveau.depart,
                arrivee=nouveau.arrivee,
                prix=f"{billet.prix_paye:.0f}",
            ),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
            "context": {"last_billet_id": billet.id},
            "tool_used": "query_trajet",
        }

    # === Choix d'action après détection d'un retard ===
    if context.get("awaiting") == "retard_action":
        billet = db.get(Billet, context.get("billet_id"))
        if billet is None:
            return {
                "answer": t("Je n'ai plus accès à votre dossier. Recommençons depuis le début.", lang),
                "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME], "context": {}, "tool_used": None,
            }
        choice = message.strip().lower()
        if "indemnit" in choice:
            rec = Reclamation(
                user_id=billet.user_id,
                billet_id=billet.id,
                type="retard",
                description=(
                    f"Demande d'indemnité pour retard de {billet.trajet.retard_minutes} minutes "
                    f"sur le {billet.trajet.type} {billet.trajet.compagnie} "
                    f"({billet.trajet.depart} → {billet.trajet.arrivee})."
                ),
                numero_suivi=generate_numero_reclamation(),
            )
            db.add(rec)
            db.commit()
            return {
                "answer": t(
                    "Votre demande d'indemnité est enregistrée sous le numéro {numero}. "
                    "Le service client traite ces dossiers sous 72 h et vous répondra par email. Autre chose ?",
                    lang,
                    numero=rec.numero_suivi,
                ),
                "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME], "context": {"last_billet_id": billet.id}, "tool_used": "create_reclamation",
            }
        if "annul" in choice or "rembours" in choice:
            ancien_trajet = billet.trajet
            ancien_trajet.places_dispo += billet.nb_places or 1
            billet.statut = "rembourse"
            db.commit()
            db.refresh(billet)
            try:
                from app.services.email import send_confirmation_email
                send_confirmation_email(
                    to_email=billet.user.email,
                    to_name=f"{billet.user.prenom} {billet.user.nom}",
                    numero_billet=billet.numero_billet,
                    trajet_resume=(
                        f"ANNULÉ — {ancien_trajet.type.capitalize()} {ancien_trajet.compagnie} · "
                        f"{ancien_trajet.depart} → {ancien_trajet.arrivee} · "
                        f"Remboursement de {billet.prix_paye:.2f} EUR en cours"
                    ),
                    chatbot_url=f"{settings.frontend_url}/assistant",
                    montant=f"{billet.prix_paye:.2f} EUR remboursés",
                    classe=ancien_trajet.classe or "Standard",
                    lang=lang,
                )
            except Exception as exc:
                logger.warning("Mail annulation échoué : %s", exc)
            return {
                "answer": t(
                    "Votre billet {numero} est annulé. Le remboursement de "
                    "{prix} € sera crédité sous 5 à 7 jours ouvrés sur votre moyen de paiement. "
                    "Un email de confirmation vient de partir.",
                    lang,
                    numero=billet.numero_billet,
                    prix=f"{billet.prix_paye:.0f}",
                ),
                "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME], "context": {"last_billet_id": billet.id}, "tool_used": "query_billet",
            }
        if "rien" in choice or "merci" in choice or "non" in choice:
            return {
                "answer": t("Pas de souci, je reste à votre disposition si la situation évolue. Bon voyage.", lang),
                "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME], "context": {"last_billet_id": billet.id}, "tool_used": None,
            }
        return {
            "answer": t("Je n'ai pas reconnu cette option. Choisissez l'une des actions proposées :", lang),
            "quick_replies": [t("Demander une indemnité", lang), t("Annuler et me faire rembourser", lang), t("Rien, merci", lang)],
            "context": context, "tool_used": None,
        }

    # === Question / freeform — DuckDuckGo si pertinent + Gemini ===
    if intent in ("question", "freeform"):
        history = _history_from_session(db, session_id, limit=12) if session_id else None
        used_web = False
        web_context = ""

        # Injecte le contexte du dernier billet vérifié (si encore en session)
        billet_context = ""
        destination_city = None
        last_id = context.get("last_billet_id")
        if last_id:
            b = db.get(Billet, last_id)
            if b is not None and b.trajet is not None:
                trj = b.trajet
                duree_min = int((trj.date_arrivee - trj.date_depart).total_seconds() // 60)
                duree_h, duree_m = divmod(duree_min, 60)
                duree_str = f"{duree_h} h {duree_m:02d}"
                destination_city = trj.arrivee
                billet_context = (
                    f"CONTEXTE BILLET (l'utilisateur a déjà vérifié son identité, tu peux y faire référence) :\n"
                    f"- Numéro de billet : {b.numero_billet}\n"
                    f"- Voyageur : {b.user.prenom} {b.user.nom}\n"
                    f"- Mode de transport : {trj.type}\n"
                    f"- Trajet : {trj.depart} → {trj.arrivee}\n"
                    f"- Date de départ : {trj.date_depart:%d/%m/%Y à %H:%M}\n"
                    f"- Date d'arrivée prévue : {trj.date_arrivee:%d/%m/%Y à %H:%M}\n"
                    f"- Durée du trajet : {duree_str}\n"
                    f"- Retard éventuel : {trj.retard_minutes} min\n"
                    f"- Compagnie : {trj.compagnie} · Classe : {trj.classe or 'Standard'} · Escales : {trj.stops or 'direct'}\n"
                    f"- Wi-Fi : {'oui' if trj.has_wifi else 'non'} · Prise : {'oui' if trj.has_prise else 'non'}\n"
                    f"- Statut : {b.statut} · Prix payé : {b.prix_paye:.2f} €\n"
                )

        # Réservations de l'utilisateur connecté : injection automatique si demande explicite
        # ou si l'utilisateur est connecté et pose une question qui pourrait concerner ses billets
        m_lower_billets = message.lower()
        if user and any(k in m_lower_billets for k in _MY_BILLETS_KEYWORDS):
            billets_ctx = _build_user_billets_context(db, user)
            billet_context = billets_ctx + ("\n\n" + billet_context if billet_context else "")
            logger.info("Réservations utilisateur injectées (user_id=%s)", user.id)

        # Recherche web systématique pour toutes les questions freeform voyage.
        # On enrichit la requête avec la ville de destination si le contexte billet est connu.
        search_query = message
        if destination_city and destination_city.lower() not in message.lower():
            search_query = f"{message} {destination_city}"
        results = web_search.search(search_query, max_results=5)
        if results:
            used_web = True
            web_context = web_search.format_for_prompt(results)
            logger.info("DuckDuckGo : %d résultats injectés (query: %r)", len(results), search_query)
        # === RAG : recherche dans CGV + billets indexés ===
        rag_context = ""
        used_rag = False
        try:
            user_id_for_rag = user.id if user else None
            # Pipeline 2 étapes (cf. Séance 1) :
            # 1) bi-encoder gte-small récupère 10 candidats
            # 2) cross-encoder ms-marco re-trie et garde les 3 meilleurs
            candidates = rag.search(message, k=10, user_id=user_id_for_rag)
            results = reranker.rerank(message, candidates, top_k=3) if candidates else []
            if results:
                rag_context = rag.format_context(results)
                used_rag = True
                logger.info(
                    "RAG : %d/%d chunks injectés après rerank (scores CE %s)",
                    len(results),
                    len(candidates),
                    [f"{r['score']:.2f}" for r in results],
                )
        except Exception as exc:
            logger.warning("RAG search échouée : %s", exc)

        # === DB routes : questions sur destinations / liaisons ===
        db_context = ""
        m_lower = message.lower()
        is_route_q  = any(k in m_lower for k in _ROUTE_KEYWORDS)
        is_dest_q   = any(k in m_lower for k in _DEST_KEYWORDS)
        if is_route_q or is_dest_q:
            arrivee, depart_city = _extract_destination(message)
            transport_map = {
                "avion": "avion", "vol": "avion", "aérien": "avion",
                "train": "train", "tgv": "train", "eurostar": "train", "ter": "train",
                "bateau": "bateau", "ferry": "bateau",
                "bus": "bus", "autocar": "bus", "flixbus": "bus",
            }
            transport_type = next((v for k, v in transport_map.items() if k in m_lower), None)
            if arrivee:
                db_context = _query_routes_for_dest(db, arrivee, depart_city, transport_type)
            elif is_dest_q:
                depart_city = depart_city or "Paris"
                db_context = _query_top_destinations(db, depart_city)
            if db_context:
                logger.info("DB routes injectées (%d chars)", len(db_context))

        # === APIs voyage temps réel : météo + heure locale + change ===
        # Données structurées et fiables que ni le LLM ni le RAG ne peuvent fournir.
        # Ville cible = destination extraite du message, sinon destination du billet vérifié.
        api_context = ""
        used_apis: list[str] = []
        try:
            api_context, used_apis = travel_apis.build_context(message, fallback_city=destination_city)
            if api_context:
                logger.info("APIs voyage injectées : %s", used_apis)
        except Exception as exc:
            logger.warning("APIs voyage échouées : %s", exc)

        # Concatène DB routes + RAG + billet_context + API temps réel + web_context
        full_context = "\n\n".join(
            x for x in [db_context, rag_context, billet_context, api_context, web_context] if x
        )
        gem = gemini.ask(message, history=history, web_context=full_context, lang=lang)
        if gem:
            sources = []
            if used_apis:
                sources.append("api")
            if used_rag:
                sources.append("rag")
            if used_web:
                sources.append("web")
            tool = "+".join(sources) if sources else "gemini"
            return {
                "answer": gem,
                "quick_replies": [],
                # On préserve last_billet_id pour la suite des questions
                "context": {"last_billet_id": last_id} if last_id else {},
                "tool_used": tool,
            }
        return _fallback_question(message, lang)

    return _fallback_question(message, lang)


def _run_search_flow(db: Session, context: dict, lang: str = "fr") -> dict:
    """Slot-filling de la recherche de voyage.

    Slots dans context : search_arrivee (requis), search_depart (requis),
    search_transport (optionnel), search_date (optionnel). Demande le prochain
    slot requis manquant ; quand arrivée + départ sont connus, lance la recherche
    et renvoie des résultats structurés sous la clé "results"."""
    arrivee = (context.get("search_arrivee") or "").strip()
    depart = (context.get("search_depart") or "").strip()

    # 1) Destination manquante → on la demande (on reste dans le flux).
    if not arrivee:
        context["awaiting"] = "search_dest"
        return {
            "answer": t("Où souhaitez-vous aller ?", lang),
            "quick_replies": [],
            "context": context,
            "tool_used": None,
            "results": [],
        }

    # 2) Destination = un PAYS → on demande une ville précise (le départ est conservé).
    pays = _match_country(arrivee)
    if pays:
        villes = _cities_in_country(pays)
        context.pop("search_arrivee", None)
        context["awaiting"] = "search_dest"
        if villes:
            answer = t(
                "{pays} : dans quelle ville souhaitez-vous aller ? Par exemple : {villes}.",
                lang, pays=pays, villes=", ".join(villes),
            )
        else:
            answer = t("{pays} : dans quelle ville souhaitez-vous aller ?", lang, pays=pays)
        return {
            "answer": answer,
            "quick_replies": [],
            "context": context,
            "tool_used": None,
            "results": [],
        }

    # 3) Départ manquant → on le demande (on garde la destination).
    if not depart:
        context["awaiting"] = "search_depart"
        return {
            "answer": t("D'où partez-vous ? (votre ville, ou pays)", lang),
            "quick_replies": [],
            "context": context,
            "tool_used": None,
            "results": [],
        }

    # 4) Tout est là → recherche.
    results = _search_trajets_results(db, depart, arrivee, limit=8)
    if not results:
        # Aucun résultat : on propose des alternatives ET on RESTE en recherche
        # (le départ est conservé) pour que l'utilisateur n'ait qu'à donner une
        # autre destination.
        top = _query_top_destinations(db, depart)
        suggestion = ("\n\n" + top) if top else ""
        context.pop("search_arrivee", None)
        context["awaiting"] = "search_dest"  # la prochaine réponse = nouvelle destination
        return {
            "answer": t(
                "Je n'ai pas trouvé de trajet de {depart} à {arrivee}. "
                "Voici des destinations possibles au départ de {depart} — "
                "dites-moi laquelle vous intéresse :",
                lang, depart=depart, arrivee=arrivee,
            ) + suggestion,
            "quick_replies": [],
            "context": context,
            "tool_used": "query_trajet",
            "results": [],
        }

    # Succès : on garde le départ pour une éventuelle recherche enchaînée.
    context.pop("awaiting", None)
    context.pop("search_arrivee", None)
    return {
        "answer": t("Voici les trajets de {depart} à {arrivee} :", lang, depart=depart, arrivee=arrivee),
        "quick_replies": [],
        "context": context,
        "tool_used": "query_trajet",
        "results": results,
    }


def _unlock_and_act(db: Session, billet: Billet, context: dict, lang: str = "fr") -> dict:
    """Billet déverrouillé (identité confirmée) : cache + propose les actions."""
    trajet = billet.trajet
    new_ctx = {"verified_billet": billet.numero_billet, "last_billet_id": billet.id}
    flow = context.get("flow")
    if flow in ("flow_retard", "flow_modif", "flow_recla"):
        result = _handle_flow(db, billet, flow, context, lang=lang)
        result_ctx = dict(result.get("context") or {})
        result_ctx.setdefault("verified_billet", billet.numero_billet)
        result_ctx.setdefault("last_billet_id", billet.id)
        result["context"] = result_ctx
        result.setdefault("results", [])
        return result
    # Pas de flow précis : on confirme et on propose les actions sensibles.
    resume = ""
    if trajet is not None:
        resume = f" ({trajet.depart} → {trajet.arrivee})"
    return {
        "answer": t(
            "C'est confirmé, votre identité est validée pour le billet {numero}{resume}. "
            "Que souhaitez-vous faire ?",
            lang, numero=billet.numero_billet, resume=resume,
        ),
        "quick_replies": [
            t("Mon voyage a un problème", lang),
            t("Modifier ma réservation", lang),
            t("Faire une réclamation", lang),
        ],
        "context": new_ctx,
        "tool_used": "identity_check",
        "results": [],
    }


def _start_billet_unlock(
    db: Session, numero: str, context: dict, user: User | None, lang: str = "fr"
) -> dict:
    """Point d'entrée commun quand un numéro de billet est fourni.

    - Billet inexistant → on le signale.
    - Déjà déverrouillé dans cette conversation → on enchaîne directement.
    - Connecté + billet lui appartient → déverrouillage immédiat, aucune question.
    - Sinon → on demande UNIQUEMENT la date de naissance.
    """
    billet = db.query(Billet).filter(Billet.numero_billet == numero).first()
    if billet is None:
        context["awaiting"] = "unlock_billet"
        context.pop("pending_billet", None)
        return {
            "answer": t("Je n'ai pas trouvé ce numéro de billet. Pouvez-vous me le redonner (format TRV-2026-XXXXXX) ?", lang),
            "quick_replies": [],
            "context": context,
            "tool_used": "query_billet",
            "results": [],
        }

    # Déjà vérifié dans cette conversation
    if context.get("verified_billet") == billet.numero_billet:
        context.pop("awaiting", None)
        return _unlock_and_act(db, billet, context, lang=lang)

    # Connecté et propriétaire → déverrouillage immédiat
    if user is not None and billet.user_id == user.id:
        context.pop("awaiting", None)
        return _unlock_and_act(db, billet, context, lang=lang)

    # Sinon, on demande la date de naissance uniquement
    context["pending_billet"] = billet.numero_billet
    context["awaiting"] = "unlock_dob"
    return {
        "answer": t("Pour confirmer que c'est bien vous, quelle est votre date de naissance ?", lang),
        "quick_replies": [],
        "context": context,
        "tool_used": "identity_check",
        "results": [],
    }


def _handle_flow(db: Session, billet: Billet, flow: str, context: dict, lang: str = "fr") -> dict:
    trajet: Trajet = billet.trajet

    if flow == "flow_retard":
        if trajet.retard_minutes > 0:
            msg = t(
                "Votre {type} n°{numero} ({depart} → {arrivee} du {date}) a {retard} minutes de retard. "
                "Que souhaitez-vous faire ?",
                lang,
                type=trajet.type,
                numero=billet.numero_billet,
                depart=trajet.depart,
                arrivee=trajet.arrivee,
                date=f"{trajet.date_depart:%d/%m/%Y à %H:%M}",
                retard=trajet.retard_minutes,
            )
            return {
                "answer": msg,
                "quick_replies": [
                    t("Demander une indemnité", lang),
                    t("Annuler et me faire rembourser", lang),
                    t("Rien, merci", lang),
                ],
                "context": {"awaiting": "retard_action", "billet_id": billet.id},
                "tool_used": "query_trajet",
            }
        return {
            "answer": t("Bonne nouvelle : votre {type} est à l'heure (départ {date}).", lang, type=trajet.type, date=f"{trajet.date_depart:%d/%m/%Y à %H:%M}"),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
            "context": {},
            "tool_used": "query_trajet",
        }

    if flow == "flow_modif":
        autres = (
            db.query(Trajet)
            .filter(
                Trajet.depart == trajet.depart,
                Trajet.arrivee == trajet.arrivee,
                Trajet.id != trajet.id,
                Trajet.statut == "actif",
                Trajet.places_dispo > 0,
            )
            .order_by(Trajet.date_depart.asc())
            .limit(3)
            .all()
        )
        if not autres:
            return {
                "answer": t("Aucun trajet alternatif disponible pour cette destination pour le moment. Voulez-vous que je vous alerte dès qu'un créneau se libère ?", lang),
                "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
                "context": {},
                "tool_used": "query_trajet",
            }
        options = [
            f"{t.date_depart:%d/%m %H:%M} - {t.compagnie} - {t.prix:.0f}€" for t in autres
        ]
        return {
            "answer": t("Voici 3 alternatives disponibles. Sélectionnez celle qui vous convient :", lang),
            "quick_replies": options,
            "context": {
                "awaiting": "pick_alt",
                "billet_id": billet.id,
                "alt_map": {opt: autres[i].id for i, opt in enumerate(options)},
            },
            "tool_used": "query_trajet",
        }

    if flow == "flow_recla":
        rec = Reclamation(
            user_id=billet.user_id,
            billet_id=billet.id,
            type="autre",
            description=f"Réclamation déposée via chatbot pour le billet {billet.numero_billet}",
            numero_suivi=generate_numero_reclamation(),
        )
        db.add(rec)
        db.commit()
        return {
            "answer": t(
                "C'est noté. Votre réclamation est enregistrée sous le numéro {numero}. "
                "Vous recevrez une réponse par email sous 72 heures. Autre chose ?",
                lang,
                numero=rec.numero_suivi,
            ),
            "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
            "context": {},
            "tool_used": "create_reclamation",
        }

    return {
        "answer": t("Action non reconnue.", lang),
        "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
        "context": {},
        "tool_used": None,
    }


def _fallback_question(message: str, lang: str = "fr") -> dict:
    """Réponses utiles quand Gemini est indisponible."""
    m = message.lower()
    if any(k in m for k in ("bagage", "valise")):
        ans = (
            "Les règles bagages varient selon la compagnie : généralement 1 bagage cabine "
            "(8 à 12 kg en avion, libre en train) et 1 bagage en soute (23 kg en avion, illimité en train). "
            "Consultez les conditions de votre billet pour le détail exact."
        )
    elif any(k in m for k in ("tarif", "prix")):
        ans = (
            "Les tarifs dépendent du mode, de la compagnie et de la classe. En général : "
            "bus dès 9 €, train dès 19 €, bateau dès 35 €, avion dès 49 €. Le mieux est de "
            "lancer une recherche depuis l'accueil pour voir les vrais prix."
        )
    elif any(k in m for k in ("wifi", "wi-fi", "internet")):
        ans = (
            "La plupart des trains, bus longue distance et avions proposent du Wi-Fi à bord, "
            "souvent gratuit. Vérifiez la fiche du trajet (icône Wi-Fi) avant de réserver."
        )
    elif any(k in m for k in ("modifier", "changer", "échanger")):
        ans = (
            "Pour modifier un billet, tapez « Modifier ma réservation » et donnez-moi votre numéro de billet, "
            "je vous propose les alternatives disponibles."
        )
    elif any(k in m for k in ("annulation", "annuler", "remboursement")):
        ans = (
            "Pour annuler ou demander un remboursement, tapez « Faire une réclamation » et indiquez votre numéro de billet. "
            "Les conditions de remboursement dépendent du tarif choisi (Loisir / Pro / Premium)."
        )
    else:
        ans = (
            "Bonne question ! Pour vous donner une réponse précise, sélectionnez le sujet "
            "qui correspond le mieux à votre besoin parmi les suggestions, ou reformulez en précisant "
            "le mode de transport ou la compagnie."
        )
    return {
        "answer": t(ans, lang),
        "quick_replies": [t(q, lang) for q in QUICK_REPLIES_HOME],
        "context": {},
        "tool_used": "rag_stub",
    }


def process_message(
    db: Session,
    message: str,
    context: dict[str, Any] | None = None,
    user: User | None = None,
    session_id: str | None = None,
    lang: str = "fr",
) -> dict[str, Any]:
    """Wrapper qui préserve last_billet_id à travers tous les flows et fallbacks."""
    context = dict(context or {})
    incoming_last_billet = context.get("last_billet_id")
    result = _process_message_inner(db, message, context, user, session_id, lang=lang)
    out_ctx = dict(result.get("context") or {})
    # Préserve verified_billet sur toute la conversation (déverrouillage unique).
    incoming_verified = context.get("verified_billet")
    if "verified_billet" not in out_ctx and incoming_verified is not None and not out_ctx.get("awaiting"):
        out_ctx["verified_billet"] = incoming_verified
    # Préserve last_billet_id si on est encore en plein flow (awaiting != None et clé déjà absente)
    # ou si on revient à un état neutre — sauf si flow_*** vient de poser un nouveau last_billet_id
    if "last_billet_id" not in out_ctx and incoming_last_billet is not None and not out_ctx.get("awaiting"):
        out_ctx["last_billet_id"] = incoming_last_billet
    result["context"] = out_ctx
    # Résultats de recherche : transients, défaut liste vide partout.
    result.setdefault("results", [])
    return result

