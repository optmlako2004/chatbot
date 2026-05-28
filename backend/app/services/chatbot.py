from __future__ import annotations

import logging
import random
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from sqlalchemy import func as sqlfunc

from app.config import settings
from app.models import Billet, ChatMessage, Reclamation, Route, Trajet, User
from app.services import gemini, ner, rag, reranker, web_search
from app.services.identity import verify_billet_identity
from app.services.numeros import generate_numero_reclamation

logger = logging.getLogger(__name__)

import html
import re

GREETINGS = {"bonjour", "salut", "hello", "hey", "coucou", "bonsoir", "yo", "hi"}
THANKS = {"merci", "thanks", "thx", "remercie"}
BYE = {"au revoir", "bye", "ciao", "à bientôt", "à plus", "salut"}

QUICK_REPLIES_HOME = [
    "Mon voyage a un problème",
    "Modifier ma réservation",
    "Faire une réclamation",
    "Poser une question",
]

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

# Mots indicateurs de destination dans la phrase ("je cherche un train à/pour/vers X")
_DEST_PREPS = re.compile(
    r"(?:pour|vers|à|a|jusqu['’]à|pour aller à|destination)\s+([A-Za-zÀ-ÖØ-öø-ÿ' -]{2,40})",
    re.IGNORECASE,
)
_FROM_PREPS = re.compile(
    r"(?:depuis|de|au départ de|à partir de|partant de)\s+([A-Za-zÀ-ÖØ-öø-ÿ' -]{2,40})",
    re.IGNORECASE,
)


def _extract_destination(text: str) -> tuple[str | None, str | None]:
    """Extrait (arrivee, depart) depuis une phrase en langage naturel."""
    arr = _DEST_PREPS.search(text)
    dep = _FROM_PREPS.search(text)
    arrivee = arr.group(1).strip().rstrip("?.,!") if arr else None
    depart  = dep.group(1).strip().rstrip("?.,!") if dep else None
    return arrivee, depart


_MY_BILLETS_KEYWORDS = (
    "mes billets", "mes réservations", "mes reservations", "mes voyages",
    "mes trajets", "ma réservation", "ma reservation", "mon billet",
    "mon voyage", "mon trajet", "prochain voyage", "prochaine réservation",
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
        lines.append(
            f"- {b.numero_billet} · {t.type.capitalize()} {t.compagnie} · "
            f"{t.depart} → {t.arrivee} · {date_fr} · "
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


def _parse_date_fr(s: str) -> date | None:
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
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
) -> dict[str, Any]:
    raw = message
    # Sanitization sauf pour les champs où l'on attend une valeur littérale (nom, etc.)
    # On garde la valeur brute pour `nom`/`prenom`/`date_naissance` car le strip change rien d'utile.
    message = _sanitize_user_input(raw)

    # 0. Entrée vide après sanitization
    if not message or len(message) < 1:
        return {
            "answer": "Je n'ai pas reçu de message lisible. Pouvez-vous reformuler votre demande ?",
            "quick_replies": QUICK_REPLIES_HOME if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 1. Trop court pour être interprétable hors d'un flow guidé
    if not context.get("awaiting") and len(message) < 2:
        return {
            "answer": "Pouvez-vous préciser votre demande en quelques mots ? Je peux vous aider à modifier un billet, signaler un retard ou répondre à une question voyage.",
            "quick_replies": QUICK_REPLIES_HOME,
            "context": context,
            "tool_used": None,
        }

    # 2. Insulte / langage agressif → désescalade fixe (on évite Gemini pour ne pas amplifier)
    if _OFFENSIVE_PATTERNS.search(message):
        return {
            "answer": (
                "Je comprends que vous puissiez être frustré, mais je ne peux pas répondre à ce type de langage. "
                "Je suis ici pour vous aider sur vos voyages — si vous avez un problème concret avec un billet, "
                "dites-moi ce qui ne va pas et je ferai de mon mieux pour le résoudre."
            ),
            "quick_replies": QUICK_REPLIES_HOME if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 3. Sujet dangereux / illégal hors-périmètre
    if _HARMFUL_PATTERNS.search(message):
        return {
            "answer": (
                "Je suis l'assistant Voyage et je ne peux répondre qu'aux questions liées à vos déplacements "
                "(billets, horaires, destinations, démarches voyage). Pour le sujet que vous évoquez, "
                "merci de vous adresser aux autorités ou services compétents."
            ),
            "quick_replies": QUICK_REPLIES_HOME if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 4. Tentative d'injection de prompt
    if _PROMPT_INJECTION.search(message):
        return {
            "answer": (
                "Mes consignes de sécurité ne sont pas modifiables. Je peux vous aider sur un billet précis "
                "après une vérification d'identité, ou répondre à vos questions de voyage."
            ),
            "quick_replies": QUICK_REPLIES_HOME if not context.get("awaiting") else [],
            "context": context,
            "tool_used": None,
        }

    # 5. Mention d'un numéro de billet hors du flow guidé → on guide vers la procédure
    if not context.get("awaiting") and _BILLET_REFERENCE.search(message) and any(
        k in message.lower() for k in ("info", "détail", "details", "donne", "montre", "affiche", "propriétaire", "qui est")
    ):
        return {
            "answer": (
                "Pour accéder aux détails d'un billet, je dois d'abord vérifier votre identité. "
                "Cliquez sur l'action qui correspond à votre besoin, je vous demanderai ensuite "
                "votre numéro, votre nom, votre prénom et votre date de naissance."
            ),
            "quick_replies": QUICK_REPLIES_HOME,
            "context": context,
            "tool_used": "identity_check",
        }

    # 6. Changement de flow en plein parcours d'identité : on demande confirmation
    if context.get("awaiting") in {"numero_billet", "nom", "prenom", "date_naissance"}:
        switch = _detect_flow_switch(message.lower())
        if switch and switch != context.get("flow"):
            return {
                "answer": (
                    "Vous étiez en train d'ouvrir un dossier. Voulez-vous abandonner ce parcours "
                    "et démarrer un nouveau ? Si oui, choisissez ci-dessous ; sinon je continue le parcours actuel."
                ),
                "quick_replies": ["Abandonner et recommencer", "Continuer le parcours actuel"],
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
                "answer": "Très bien, on recommence. Donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).",
                "quick_replies": [],
                "context": {"flow": new_flow, "awaiting": "numero_billet"},
                "tool_used": None,
            }
        resume = context.get("resume_awaiting", "numero_billet")
        msg_map = {
            "numero_billet": "votre numéro de billet (format TRV-2026-XXXXXX) ?",
            "nom": "votre nom de famille ?",
            "prenom": "votre prénom ?",
            "date_naissance": "votre date de naissance au format JJ/MM/AAAA ?",
        }
        next_ctx = {k: v for k, v in context.items() if k not in ("pending_flow", "resume_awaiting")}
        next_ctx["awaiting"] = resume
        return {
            "answer": "Parfait, on continue. Reprenons : " + msg_map.get(resume, msg_map["numero_billet"]),
            "quick_replies": [],
            "context": next_ctx,
            "tool_used": None,
        }

    intent = _detect_intent(message, context)
    prenom = (user.prenom if user else "").strip()

    # === Greetings ===
    if intent == "greeting":
        greet = _greet_prefix()
        salutation = f"{greet}{', ' + prenom if prenom else ''} ! "
        suite = random.choice([
            "Comment puis-je vous aider aujourd'hui ?",
            "Que puis-je faire pour vous ?",
            "En quoi puis-je vous être utile ?",
            "Sur quoi puis-je vous aider ?",
        ])
        return {
            "answer": salutation + suite,
            "quick_replies": QUICK_REPLIES_HOME,
            "context": {},
            "tool_used": None,
        }

    if intent == "thanks":
        return {
            "answer": random.choice([
                "Avec plaisir ! N'hésitez pas si vous avez d'autres questions.",
                "Je vous en prie. Autre chose pour ce voyage ?",
                "De rien ! Je reste à votre disposition.",
            ]),
            "quick_replies": QUICK_REPLIES_HOME,
            "context": {},
            "tool_used": None,
        }

    if intent == "bye":
        return {
            "answer": random.choice([
                "Bon voyage ! À bientôt.",
                "À bientôt sur Voyage Assistant !",
                "Bonne route et à très vite.",
            ]),
            "quick_replies": [],
            "context": {},
            "tool_used": None,
        }

    # === Flows BDD ===
    if intent in ("flow_retard", "flow_modif", "flow_recla") and not context.get("awaiting"):
        context["flow"] = intent

        # Fast-path NER (Séance 4) : si l'utilisateur balance déjà tout en une phrase,
        # on extrait numero/prenom/nom/date d'un coup et on saute les questions
        # une-par-une. Filet de sécurité regex conservé dans ner.extract_entities.
        try:
            ents = ner.extract_entities(message)
        except Exception as exc:
            logger.warning("NER extract a échoué : %s", exc)
            ents = {}
        if ents.get("numero_billet"):
            context["numero_billet"] = ents["numero_billet"]
        if ents.get("prenom"):
            context["prenom"] = ents["prenom"]
        if ents.get("nom"):
            context["nom"] = ents["nom"]
        if ents.get("date_iso"):
            try:
                context["date_naissance_iso"] = ents["date_iso"]
            except Exception:
                pass

        # Choix de la prochaine étape selon ce qui manque
        if not context.get("numero_billet"):
            context["awaiting"] = "numero_billet"
            return {
                "answer": "Bien sûr. Pour ouvrir votre dossier, donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).",
                "quick_replies": [], "context": context, "tool_used": None,
            }
        # Vérifier l'existence du billet
        billet = db.query(Billet).filter(Billet.numero_billet == context["numero_billet"]).first()
        if billet is None:
            context["awaiting"] = "numero_billet"
            context.pop("numero_billet", None)
            return {
                "answer": "Je n'ai pas trouvé ce numéro de billet. Pouvez-vous me le redonner (format TRV-2026-XXXXXX) ?",
                "quick_replies": [], "context": context, "tool_used": "query_billet",
            }
        if not context.get("nom"):
            context["awaiting"] = "nom"
            return {
                "answer": f"Parfait, billet {billet.numero_billet} trouvé. Pour la sécurité, indiquez-moi votre nom de famille.",
                "quick_replies": [], "context": context, "tool_used": "query_billet",
            }
        if not context.get("prenom"):
            context["awaiting"] = "prenom"
            return {
                "answer": "Merci. Et votre prénom ?",
                "quick_replies": [], "context": context, "tool_used": None,
            }
        if not context.get("date_naissance_iso"):
            context["awaiting"] = "date_naissance"
            return {
                "answer": "Et enfin, votre date de naissance au format JJ/MM/AAAA.",
                "quick_replies": [], "context": context, "tool_used": None,
            }
        # Tout est là d'un coup : on vérifie et on enchaîne le flow
        from datetime import datetime as _dt
        try:
            dt = _dt.fromisoformat(context["date_naissance_iso"])
        except Exception:
            dt = None
        if dt is None:
            context["awaiting"] = "date_naissance"
            return {
                "answer": "Merci. Pour confirmer, votre date de naissance au format JJ/MM/AAAA ?",
                "quick_replies": [], "context": context, "tool_used": None,
            }
        billet_ok = verify_billet_identity(
            db, context["numero_billet"], context["nom"], context["prenom"], dt
        )
        if billet_ok is None:
            return {
                "answer": (
                    "Les informations fournies ne correspondent pas à ce billet. "
                    "Pour des raisons de sécurité, je ne peux pas donner suite."
                ),
                "quick_replies": [], "context": {}, "tool_used": "identity_check",
            }
        result = _handle_flow(db, billet_ok, context["flow"], context)
        result["context"] = {**result.get("context", {}), "last_billet_id": billet_ok.id}
        return result

    if context.get("awaiting") == "numero_billet":
        num = message.strip().upper()
        billet = db.query(Billet).filter(Billet.numero_billet == num).first()
        if billet is None:
            return {
                "answer": "Hm, je ne trouve pas ce billet en base. Vérifiez l'orthographe (format TRV-2026-XXXXXX) ou essayez à nouveau.",
                "quick_replies": [],
                "context": context,
                "tool_used": "query_billet",
            }
        context["numero_billet"] = num
        context["awaiting"] = "nom"
        return {
            "answer": "Parfait, je l'ai trouvé. Pour la sécurité de votre dossier, indiquez-moi votre nom de famille.",
            "quick_replies": [],
            "context": context,
            "tool_used": "query_billet",
        }

    if context.get("awaiting") == "nom":
        context["nom"] = message.strip()
        context["awaiting"] = "prenom"
        return {
            "answer": "Merci. Et votre prénom ?",
            "quick_replies": [],
            "context": context,
            "tool_used": None,
        }

    if context.get("awaiting") == "prenom":
        context["prenom"] = message.strip()
        context["awaiting"] = "date_naissance"
        return {
            "answer": "Et enfin, votre date de naissance au format JJ/MM/AAAA.",
            "quick_replies": [],
            "context": context,
            "tool_used": None,
        }

    if context.get("awaiting") == "date_naissance":
        dt = _parse_date_fr(message)
        if dt is None:
            return {
                "answer": "Format de date invalide. Merci d'utiliser JJ/MM/AAAA (par exemple 14/03/1995).",
                "quick_replies": [],
                "context": context,
                "tool_used": None,
            }
        billet = verify_billet_identity(
            db, context["numero_billet"], context["nom"], context["prenom"], dt
        )
        if billet is None:
            return {
                "answer": (
                    "Les informations fournies ne correspondent pas à ce billet. "
                    "Pour des raisons de sécurité, je ne peux pas donner suite. "
                    "Vérifiez vos informations ou contactez le service client."
                ),
                "quick_replies": [],
                "context": {},
                "tool_used": "identity_check",
            }
        result = _handle_flow(db, billet, context["flow"], context)
        # Mémorise le billet vérifié pour les questions libres ultérieures
        result["context"] = {**result.get("context", {}), "last_billet_id": billet.id}
        return result

    # === Choix d'une alternative pour modifier le billet ===
    if context.get("awaiting") == "pick_alt":
        alt_map = context.get("alt_map") or {}
        billet_id = context.get("billet_id")
        nouveau_trajet_id = alt_map.get(message.strip())
        billet = db.get(Billet, billet_id) if billet_id else None
        nouveau = db.get(Trajet, nouveau_trajet_id) if nouveau_trajet_id else None
        if billet is None or nouveau is None:
            return {
                "answer": "Je n'ai pas reconnu cette option. Merci de cliquer sur l'un des choix proposés.",
                "quick_replies": list(alt_map.keys()),
                "context": context,
                "tool_used": None,
            }
        if nouveau.places_dispo <= 0:
            return {
                "answer": "Ce trajet vient d'être complet. Souhaitez-vous voir d'autres alternatives ?",
                "quick_replies": QUICK_REPLIES_HOME,
                "context": {},
                "tool_used": "query_trajet",
            }
        # Effectue la modification
        ancien_trajet = billet.trajet
        ancien_trajet.places_dispo += 1
        nouveau.places_dispo -= 1
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
            )
        except Exception as exc:
            logger.warning("Mail de modification échoué : %s", exc)

        return {
            "answer": (
                f"C'est fait ! Votre billet {billet.numero_billet} est maintenant sur le vol "
                f"{nouveau.compagnie} du {nouveau.date_depart:%d/%m/%Y à %H:%M} "
                f"({nouveau.depart} → {nouveau.arrivee}). "
                f"Nouveau montant : {billet.prix_paye:.0f} €. "
                f"Un email de confirmation avec le billet mis à jour vient de partir. Autre chose ?"
            ),
            "quick_replies": QUICK_REPLIES_HOME,
            "context": {"last_billet_id": billet.id},
            "tool_used": "query_trajet",
        }

    # === Choix d'action après détection d'un retard ===
    if context.get("awaiting") == "retard_action":
        billet = db.get(Billet, context.get("billet_id"))
        if billet is None:
            return {
                "answer": "Je n'ai plus accès à votre dossier. Recommençons depuis le début.",
                "quick_replies": QUICK_REPLIES_HOME, "context": {}, "tool_used": None,
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
                "answer": (
                    f"Votre demande d'indemnité est enregistrée sous le numéro {rec.numero_suivi}. "
                    "Le service client traite ces dossiers sous 72 h et vous répondra par email. Autre chose ?"
                ),
                "quick_replies": QUICK_REPLIES_HOME, "context": {"last_billet_id": billet.id}, "tool_used": "create_reclamation",
            }
        if "annul" in choice or "rembours" in choice:
            ancien_trajet = billet.trajet
            ancien_trajet.places_dispo += 1
            billet.statut = "annule"
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
                )
            except Exception as exc:
                logger.warning("Mail annulation échoué : %s", exc)
            return {
                "answer": (
                    f"Votre billet {billet.numero_billet} est annulé. Le remboursement de "
                    f"{billet.prix_paye:.0f} € sera crédité sous 5 à 7 jours ouvrés sur votre moyen de paiement. "
                    "Un email de confirmation vient de partir."
                ),
                "quick_replies": QUICK_REPLIES_HOME, "context": {"last_billet_id": billet.id}, "tool_used": "query_billet",
            }
        if "rien" in choice or "merci" in choice or "non" in choice:
            return {
                "answer": "Pas de souci, je reste à votre disposition si la situation évolue. Bon voyage.",
                "quick_replies": QUICK_REPLIES_HOME, "context": {"last_billet_id": billet.id}, "tool_used": None,
            }
        return {
            "answer": "Je n'ai pas reconnu cette option. Choisissez l'une des actions proposées :",
            "quick_replies": ["Demander une indemnité", "Annuler et me faire rembourser", "Rien, merci"],
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
                t = b.trajet
                duree_min = int((t.date_arrivee - t.date_depart).total_seconds() // 60)
                duree_h, duree_m = divmod(duree_min, 60)
                duree_str = f"{duree_h} h {duree_m:02d}"
                destination_city = t.arrivee
                billet_context = (
                    f"CONTEXTE BILLET (l'utilisateur a déjà vérifié son identité, tu peux y faire référence) :\n"
                    f"- Numéro de billet : {b.numero_billet}\n"
                    f"- Voyageur : {b.user.prenom} {b.user.nom}\n"
                    f"- Mode de transport : {t.type}\n"
                    f"- Trajet : {t.depart} → {t.arrivee}\n"
                    f"- Date de départ : {t.date_depart:%d/%m/%Y à %H:%M}\n"
                    f"- Date d'arrivée prévue : {t.date_arrivee:%d/%m/%Y à %H:%M}\n"
                    f"- Durée du trajet : {duree_str}\n"
                    f"- Retard éventuel : {t.retard_minutes} min\n"
                    f"- Compagnie : {t.compagnie} · Classe : {t.classe or 'Standard'} · Escales : {t.stops or 'direct'}\n"
                    f"- Wi-Fi : {'oui' if t.has_wifi else 'non'} · Prise : {'oui' if t.has_prise else 'non'}\n"
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

        # Concatène DB routes + RAG + billet_context + web_context dans l'ordre logique
        full_context = "\n\n".join(x for x in [db_context, rag_context, billet_context, web_context] if x)
        gem = gemini.ask(message, history=history, web_context=full_context)
        if gem:
            if used_rag and used_web:
                tool = "rag+web"
            elif used_rag:
                tool = "rag"
            elif used_web:
                tool = "web_search"
            else:
                tool = "gemini"
            return {
                "answer": gem,
                "quick_replies": [],
                # On préserve last_billet_id pour la suite des questions
                "context": {"last_billet_id": last_id} if last_id else {},
                "tool_used": tool,
            }
        return _fallback_question(message)

    return _fallback_question(message)


def _handle_flow(db: Session, billet: Billet, flow: str, context: dict) -> dict:
    trajet: Trajet = billet.trajet

    if flow == "flow_retard":
        if trajet.retard_minutes > 0:
            msg = (
                f"Votre {trajet.type} n°{billet.numero_billet} ({trajet.depart} → {trajet.arrivee} "
                f"du {trajet.date_depart:%d/%m/%Y à %H:%M}) a {trajet.retard_minutes} minutes de retard. "
                "Que souhaitez-vous faire ?"
            )
            return {
                "answer": msg,
                "quick_replies": [
                    "Demander une indemnité",
                    "Annuler et me faire rembourser",
                    "Rien, merci",
                ],
                "context": {"awaiting": "retard_action", "billet_id": billet.id},
                "tool_used": "query_trajet",
            }
        return {
            "answer": f"Bonne nouvelle : votre {trajet.type} est à l'heure (départ {trajet.date_depart:%d/%m/%Y à %H:%M}).",
            "quick_replies": QUICK_REPLIES_HOME,
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
                "answer": "Aucun trajet alternatif disponible pour cette destination pour le moment. Voulez-vous que je vous alerte dès qu'un créneau se libère ?",
                "quick_replies": QUICK_REPLIES_HOME,
                "context": {},
                "tool_used": "query_trajet",
            }
        options = [
            f"{t.date_depart:%d/%m %H:%M} - {t.compagnie} - {t.prix:.0f}€" for t in autres
        ]
        return {
            "answer": "Voici 3 alternatives disponibles. Sélectionnez celle qui vous convient :",
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
            "answer": (
                f"C'est noté. Votre réclamation est enregistrée sous le numéro {rec.numero_suivi}. "
                "Vous recevrez une réponse par email sous 72 heures. Autre chose ?"
            ),
            "quick_replies": QUICK_REPLIES_HOME,
            "context": {},
            "tool_used": "create_reclamation",
        }

    return {
        "answer": "Action non reconnue.",
        "quick_replies": QUICK_REPLIES_HOME,
        "context": {},
        "tool_used": None,
    }


def _fallback_question(message: str) -> dict:
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
        "answer": ans,
        "quick_replies": QUICK_REPLIES_HOME,
        "context": {},
        "tool_used": "rag_stub",
    }


def process_message(
    db: Session,
    message: str,
    context: dict[str, Any] | None = None,
    user: User | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Wrapper qui préserve last_billet_id à travers tous les flows et fallbacks."""
    context = dict(context or {})
    incoming_last_billet = context.get("last_billet_id")
    result = _process_message_inner(db, message, context, user, session_id)
    out_ctx = dict(result.get("context") or {})
    # Préserve last_billet_id si on est encore en plein flow (awaiting != None et clé déjà absente)
    # ou si on revient à un état neutre — sauf si flow_*** vient de poser un nouveau last_billet_id
    if "last_billet_id" not in out_ctx and incoming_last_billet is not None and not out_ctx.get("awaiting"):
        out_ctx["last_billet_id"] = incoming_last_billet
    result["context"] = out_ctx
    return result

