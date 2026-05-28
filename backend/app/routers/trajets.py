from __future__ import annotations

import asyncio
import random
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Route, Trajet
from app.schemas import TrajetOut, TransportType
from app.services.pixabay import get_image

# ─── Capacités réelles par type ──────────────────────────────────────────────

_CAPACITE: dict[str, int] = {
    "avion":  186,   # moyen-courrier type A320
    "train":  509,   # TGV Duplex
    "bateau": 400,
    "bus":     52,
}

_CLASSES = {
    "avion":  ["Économique", "Premium Economy", "Business"],
    "train":  ["2nde · Loisir", "2nde · Pro", "1ère · Pro"],
    "bateau": ["Pont", "Cabine 2", "Cabine premium"],
    "bus":    ["Standard", "Premium"],
}


# ─── Coefficient saisonnier ───────────────────────────────────────────────────

def _saison_coeff(date: datetime) -> float:
    """Facteur de remplissage/prix selon la période (1.0 = normal)."""
    m = date.month
    d = date.day
    wd = date.weekday()   # 0=lundi … 6=dimanche

    coeff = 1.0

    # Haute saison : juillet–août
    if m in (7, 8):
        coeff *= 1.45
    # Vacances de Noël (20 déc → 5 jan)
    elif (m == 12 and d >= 20) or (m == 1 and d <= 5):
        coeff *= 1.35
    # Toussaint (22 oct → 5 nov)
    elif (m == 10 and d >= 22) or (m == 11 and d <= 5):
        coeff *= 1.20
    # Pâques (approximatif : 25 mars → 15 avr)
    elif (m == 3 and d >= 25) or (m == 4 and d <= 15):
        coeff *= 1.18
    # Pentecôte (approximatif : fin mai)
    elif m == 5 and d >= 25:
        coeff *= 1.10
    # Basse saison : jan–fév hors fêtes
    elif m in (1, 2) and d > 5:
        coeff *= 0.80

    # Week-end (vendredi + samedi + dimanche)
    if wd in (4, 5, 6):
        coeff *= 1.15

    return min(coeff, 2.2)


# ─── Disponibilité des places ─────────────────────────────────────────────────

def _places_dispo(route_id: str, transport: str, date_dep: datetime) -> int:
    """
    Simule le nombre de places restantes.
    - Déterministe : même résultat pour (route, date_départ, aujourd'hui).
    - Évolue chaque jour pour simuler les réservations progressives.
    """
    today = datetime.now(timezone.utc).date()
    days = (date_dep.date() - today).days
    cap  = _CAPACITE.get(transport, 150)
    sais = _saison_coeff(date_dep)
    rng  = random.Random(f"avail-{route_id}-{date_dep.date()}-{today}")

    if days < 0:
        return 0  # voyage passé

    if days == 0:
        # Jour J : quasi-complet en haute saison, quelques places en basse
        if sais >= 1.3:
            return rng.choice([0, 0, 0, 0, 1, 2, 3])
        elif sais >= 1.1:
            return rng.randint(0, 10)
        else:
            return rng.randint(3, 18)

    if days <= 3:
        fill = min(0.93 * sais, 0.99)
        used = int(cap * fill * rng.uniform(0.88, 1.00))
        return max(0, cap - used)

    if days <= 7:
        fill = min(0.82 * sais, 0.97)
        used = int(cap * fill * rng.uniform(0.82, 1.00))
        return max(0, cap - used)

    if days <= 30:
        # Remplissage linéaire de 15 % (J-30) à 78 % (J-7)
        base_fill = 0.15 + (30 - days) / 23 * 0.63
        fill = min(base_fill * sais, 0.95)
        used = int(cap * fill * rng.uniform(0.75, 1.00))
        return max(0, cap - used)

    if days <= 90:
        # Premières réservations early-bird
        fill = min(0.12 * sais, 0.40)
        used = int(cap * fill * rng.uniform(0.50, 1.00))
        return max(0, cap - used)

    # > 90 jours : à peine ouvert à la vente
    return cap - rng.randint(0, max(1, int(cap * 0.05)))


# ─── Prix dynamique ───────────────────────────────────────────────────────────

def _prix_dynamique(base: float, transport: str, date_dep: datetime, rng: random.Random) -> float:
    """
    Prix = base × saison × délai × bruit.
    - early-bird (> 60 j) : jusqu'à −20 %
    - last-minute (< 3 j) : jusqu'à +40 %
    - haute saison : jusqu'à +45 %
    """
    today = datetime.now(timezone.utc).date()
    days  = (date_dep.date() - today).days
    sais  = _saison_coeff(date_dep)

    if days < 0:
        delai = 1.0
    elif days == 0:
        delai = 1.45   # last-minute très cher
    elif days <= 3:
        delai = 1.32
    elif days <= 7:
        delai = 1.18
    elif days <= 14:
        delai = 1.06
    elif days <= 30:
        delai = 1.00   # prix standard
    elif days <= 60:
        delai = 0.90   # early-bird léger
    else:
        delai = 0.80   # early-bird fort

    return round(base * sais * delai * rng.uniform(0.92, 1.08), 2)


# ─── Construction d'un TrajetOut ──────────────────────────────────────────────

def _make_trajet_out(route: Route, date_recherche: datetime) -> TrajetOut:
    """Génère un TrajetOut dynamique depuis une Route + une date."""
    rng = random.Random(f"{route.id}{date_recherche.date()}")

    dep = date_recherche.replace(
        hour=route.dep_heure, minute=route.dep_minute,
        second=0, microsecond=0,
    )
    arr     = dep + timedelta(minutes=route.duree_minutes)
    prix    = _prix_dynamique(route.base_price, route.type, dep, rng)
    classes = _CLASSES.get(route.type, ["Standard"])
    retard  = rng.choice([0] * 8 + [5, 10, 15, 30])
    places  = _places_dispo(route.id, route.type, dep)

    return TrajetOut(
        id=f"dyn-{route.id}-{date_recherche.date()}",
        type=route.type,
        depart=route.depart,
        arrivee=route.arrivee,
        date_depart=dep,
        date_arrivee=arr,
        compagnie=route.compagnie,
        prix=prix,
        places_dispo=places,
        retard_minutes=retard,
        statut="complet" if places == 0 else "actif",
        photo_url=route.photo_url,
        has_wifi=route.has_wifi,
        has_prise=route.has_prise,
        stops="direct",
        classe=rng.choice(classes),
    )


# ─── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/trajets", tags=["trajets"])


def _fr_to_en_search(term: str) -> str:
    """Traduit un terme de recherche FR→EN pour matcher la BDD (ex: 'Londres' → 'London')."""
    t = term.strip().lower()
    for en, fr in _EN_TO_FR.items():
        if fr.lower() == t:
            return ' '.join(w.capitalize() for w in en.split())
    return term


def _search_routes(db: Session, type, depart, arrivee, limit=60) -> list[Route]:
    # Traduit FR→EN si nécessaire (la BDD stocke les noms en anglais)
    depart_q  = _fr_to_en_search(depart)  if depart  else depart
    arrivee_q = _fr_to_en_search(arrivee) if arrivee else arrivee

    q = db.query(Route)
    if type:
        q = q.filter(Route.type == type)
    if depart_q:
        q = q.filter(Route.depart.ilike(f"%{depart_q}%"))
    if arrivee_q:
        q = q.filter(Route.arrivee.ilike(f"%{arrivee_q}%"))
    return q.limit(limit).all()


def _search_connecting(
    db: Session,
    transport: str,
    depart: str,
    arrivee: str,
    date_dt: datetime,
    target_1stop: int = 3,
    target_2stop: int = 4,
) -> tuple[list[TrajetOut], list[TrajetOut]]:
    """Retourne (vols_1_escale, vols_2_escales). Toujours appelé, indépendamment des directs."""
    depart_q  = _fr_to_en_search(depart)
    arrivee_q = _fr_to_en_search(arrivee)

    hubs_dep = {
        r[0] for r in
        db.query(Route.arrivee_code)
        .filter(Route.depart.ilike(f"%{depart_q}%"), Route.type == transport, Route.arrivee_code != None)
        .distinct().all()
    }
    if not hubs_dep:
        return [], []

    routes_to_arr = (
        db.query(Route)
        .filter(Route.arrivee.ilike(f"%{arrivee_q}%"), Route.type == transport)
        .all()
    )
    if not routes_to_arr:
        return [], []

    # Codes IATA des aéroports du départ et de l'arrivée (pour éviter les hubs circulaires)
    origin_codes = {
        r[0] for r in db.query(Route.depart_code)
        .filter(Route.depart.ilike(f"%{depart_q}%"), Route.type == transport, Route.depart_code != None)
        .distinct().all()
    }
    dest_codes = {
        r[0] for r in db.query(Route.arrivee_code)
        .filter(Route.arrivee.ilike(f"%{arrivee_q}%"), Route.type == transport, Route.arrivee_code != None)
        .distinct().all()
    }

    # Durée max acceptable selon le mode (en heures)
    max_dur_1stop = 22 if transport == "avion" else 36
    max_dur_2stop = 32 if transport == "avion" else 52

    # --- 1 escale ---
    one_stop: list[TrajetOut] = []
    seen_hubs: set[str] = set()
    cap_1 = target_1stop * 4

    for leg2 in routes_to_arr:
        if len(one_stop) >= cap_1:
            break
        hub_code = leg2.depart_code
        # Exclure les hubs qui sont l'origine ou la destination (routage circulaire)
        if not hub_code or hub_code not in hubs_dep or hub_code in seen_hubs:
            continue
        if hub_code in origin_codes or hub_code in dest_codes:
            continue
        seen_hubs.add(hub_code)
        leg1_routes = (
            db.query(Route)
            .filter(Route.depart.ilike(f"%{depart_q}%"), Route.arrivee_code == hub_code, Route.type == transport)
            .limit(3).all()
        )
        for leg1 in leg1_routes:
            if len(one_stop) >= cap_1:
                break
            t1 = _make_trajet_out(leg1, date_dt)
            if t1.statut != "actif":
                continue
            layover = random.Random(f"{leg1.id}{leg2.id}").randint(90, 240)
            t2_start = t1.date_arrivee + timedelta(minutes=layover)
            t2 = _make_trajet_out(leg2, t2_start)
            if t2.statut != "actif":
                continue
            total_h = (t2.date_arrivee - t1.date_depart).total_seconds() / 3600
            if total_h > max_dur_1stop:
                continue
            hub_clean = _clean_dest_name(leg2.depart)
            one_stop.append(TrajetOut(
                id=f"conn-{leg1.id}-{leg2.id}-{date_dt.date()}",
                type=transport,
                depart=t1.depart, arrivee=t2.arrivee,
                date_depart=t1.date_depart, date_arrivee=t2.date_arrivee,
                compagnie=f"{t1.compagnie} + {t2.compagnie}",
                prix=round(t1.prix + t2.prix * 0.85, 2),
                places_dispo=min(t1.places_dispo, t2.places_dispo),
                retard_minutes=t1.retard_minutes + t2.retard_minutes,
                statut="actif", photo_url=t1.photo_url,
                has_wifi=t1.has_wifi and t2.has_wifi,
                has_prise=t1.has_prise or t2.has_prise,
                stops="1 escale", classe=t1.classe,
                escales=[hub_clean], duree_escale_min=layover,
            ))

    # --- 2 escales (toujours cherché) ---
    two_stop: list[TrajetOut] = []
    cap_2 = target_2stop * 4

    hubs_arr = {
        r[0] for r in
        db.query(Route.depart_code)
        .filter(Route.arrivee.ilike(f"%{arrivee_q}%"), Route.type == transport, Route.depart_code != None)
        .distinct().all()
    }

    for mid_code in list(hubs_dep)[:60]:
        if len(two_stop) >= cap_2:
            break
        # Exclure les hubs qui sont l'origine ou la destination
        if mid_code in origin_codes or mid_code in dest_codes:
            continue
        for arr_hub_code in hubs_arr:
            if len(two_stop) >= cap_2:
                break
            if arr_hub_code == mid_code or arr_hub_code in hubs_dep:
                continue
            if arr_hub_code in origin_codes or arr_hub_code in dest_codes:
                continue
            bridge = db.query(Route).filter(
                Route.depart_code == mid_code,
                Route.arrivee_code == arr_hub_code,
                Route.type == transport,
            ).first()
            if not bridge:
                continue
            leg1_routes = db.query(Route).filter(
                Route.depart.ilike(f"%{depart_q}%"),
                Route.arrivee_code == mid_code,
                Route.type == transport,
            ).limit(2).all()
            leg3_routes = db.query(Route).filter(
                Route.depart_code == arr_hub_code,
                Route.arrivee.ilike(f"%{arrivee_q}%"),
                Route.type == transport,
            ).limit(2).all()
            for leg1 in leg1_routes:
                if len(two_stop) >= cap_2:
                    break
                for leg3 in leg3_routes:
                    if len(two_stop) >= cap_2:
                        break
                    t1 = _make_trajet_out(leg1, date_dt)
                    if t1.statut != "actif":
                        continue
                    lay1 = random.Random(f"{leg1.id}{bridge.id}").randint(90, 180)
                    t2_start = t1.date_arrivee + timedelta(minutes=lay1)
                    t2 = _make_trajet_out(bridge, t2_start)
                    lay2 = random.Random(f"{bridge.id}{leg3.id}").randint(90, 180)
                    t3_start = t2.date_arrivee + timedelta(minutes=lay2)
                    t3 = _make_trajet_out(leg3, t3_start)
                    if t3.statut != "actif":
                        continue
                    total_h = (t3.date_arrivee - t1.date_depart).total_seconds() / 3600
                    if total_h > max_dur_2stop:
                        continue
                    hub1 = _clean_dest_name(bridge.depart)
                    hub2 = _clean_dest_name(leg3.depart)
                    two_stop.append(TrajetOut(
                        id=f"conn2-{leg1.id}-{bridge.id}-{leg3.id}-{date_dt.date()}",
                        type=transport,
                        depart=t1.depart, arrivee=t3.arrivee,
                        date_depart=t1.date_depart, date_arrivee=t3.date_arrivee,
                        compagnie=f"{t1.compagnie} + {t2.compagnie} + {t3.compagnie}",
                        prix=round((t1.prix + t2.prix + t3.prix) * 0.80, 2),
                        places_dispo=min(t1.places_dispo, t2.places_dispo, t3.places_dispo),
                        retard_minutes=t1.retard_minutes,
                        statut="actif", photo_url=t1.photo_url,
                        has_wifi=t1.has_wifi, has_prise=t1.has_prise,
                        stops="2 escales", classe=t1.classe,
                        escales=[hub1, hub2], duree_escale_min=lay1 + lay2,
                    ))

    return one_stop, two_stop


@router.get("", response_model=list[TrajetOut])
async def search_trajets(
    db: Annotated[Session, Depends(get_db)],
    type: TransportType | None = Query(default=None),
    depart: str | None = Query(default=None),
    arrivee: str | None = Query(default=None),
    date_str: str | None = Query(default=None, alias="date"),
):
    if date_str:
        try:
            day = datetime.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide (YYYY-MM-DD)")
    else:
        day = datetime.now(timezone.utc) + timedelta(days=1)

    date_dt = day.replace(tzinfo=timezone.utc) if day.tzinfo is None else day

    routes = _search_routes(db, type, depart, arrivee)
    directs = [_make_trajet_out(r, date_dt) for r in routes]

    if depart and arrivee:
        # Avec directs : min 3×1-escale + min 1×2-escales
        # Sans directs : min 3×1-escale + min 4×2-escales
        has_directs = bool(directs)
        one_stop, two_stop = _search_connecting(
            db, type or "avion", depart, arrivee, date_dt,
            target_1stop=3,
            target_2stop=1 if has_directs else 4,
        )
        all_results = directs + one_stop[:3] + two_stop[:( 1 if has_directs else 4)]
    else:
        all_results = directs

    if not all_results:
        return []

    all_results.sort(key=lambda t: t.date_depart)
    return all_results[:55]


import re as _re

_EN_TO_FR: dict[str, str] = {
    "london": "Londres", "london heathrow": "Londres", "london gatwick": "Londres",
    "london stansted": "Londres", "london luton": "Londres",
    "barcelona": "Barcelone", "lisbon": "Lisbonne", "athens": "Athènes",
    "vienna": "Vienne", "brussels": "Bruxelles", "copenhagen": "Copenhague",
    "edinburgh": "Édimbourg", "moscow": "Moscou", "warsaw": "Varsovie",
    "bucharest": "Bucarest", "frankfurt": "Francfort", "hamburg": "Hambourg",
    "munich": "Munich",
    "geneva": "Genève", "zurich": "Zurich", "basel": "Bâle",
    "venice": "Venise", "naples": "Naples", "florence": "Florence",
    "milan": "Milan", "rome": "Rome", "bologna": "Bologne",
    "seville": "Séville", "valencia": "Valence", "bilbao": "Bilbao",
    "prague": "Prague", "budapest": "Budapest", "bratislava": "Bratislava",
    "zagreb": "Zagreb", "belgrade": "Belgrade", "sofia": "Sofia",
    "bucharest": "Bucarest", "thessaloniki": "Thessalonique",
    "istanbul": "Istanbul", "ankara": "Ankara",
    "nuremberg": "Nuremberg", "nuernberg": "Nuremberg", "nürnberg": "Nuremberg",
    "st. petersburg": "Saint-Pétersbourg", "saint petersburg": "Saint-Pétersbourg",
    "rhodos": "Rhodes", "rhodes": "Rhodes",
    "krakow": "Cracovie", "krakau": "Cracovie", "cracow": "Cracovie",
    "cologne": "Cologne", "koeln": "Cologne",
    "gothenburg": "Göteborg", "göteborg": "Göteborg",
    "dusseldorf": "Düsseldorf", "duesseldorf": "Düsseldorf",
    "new york": "New York", "los angeles": "Los Angeles", "chicago": "Chicago",
    "miami": "Miami", "san francisco": "San Francisco", "boston": "Boston",
    "washington": "Washington", "montreal": "Montréal", "toronto": "Toronto",
    "vancouver": "Vancouver", "quebec": "Québec", "quebec city": "Québec",
    "mexico city": "Mexico", "bogota": "Bogotá", "lima": "Lima",
    "buenos aires": "Buenos Aires", "sao paulo": "São Paulo", "rio de janeiro": "Rio de Janeiro",
    "santiago": "Santiago",
    "dubai": "Dubaï", "abu dhabi": "Abou Dabi", "doha": "Doha",
    "riyadh": "Riyad", "amman": "Amman", "beirut": "Beyrouth",
    "tel aviv": "Tel-Aviv", "cairo": "Le Caire", "alexandria": "Alexandrie",
    "casablanca": "Casablanca", "tunis": "Tunis", "algiers": "Alger",
    "algier": "Alger", "marrakech": "Marrakech", "nairobi": "Nairobi",
    "cape town": "Le Cap", "johannesburg": "Johannesburg", "lagos": "Lagos",
    "accra": "Accra", "dakar": "Dakar",
    "beijing": "Pékin", "shanghai": "Shanghai", "hong kong": "Hong Kong",
    "tokyo": "Tokyo", "osaka": "Osaka", "seoul": "Séoul",
    "bangkok": "Bangkok", "singapore": "Singapour", "kuala lumpur": "Kuala Lumpur",
    "jakarta": "Jakarta", "manila": "Manille", "taipei": "Taipei",
    "delhi": "Delhi", "mumbai": "Mumbai", "kolkata": "Calcutta",
    "kathmandu": "Katmandou", "colombo": "Colombo", "dhaka": "Dacca",
    "sydney": "Sydney", "melbourne": "Melbourne", "auckland": "Auckland",
    "reykjavik": "Reykjavik", "oslo": "Oslo", "stockholm": "Stockholm",
    "helsinki": "Helsinki", "tallinn": "Tallinn", "riga": "Riga",
    "vilnius": "Vilnius", "minsk": "Minsk", "kyiv": "Kiev",
    "tbilisi": "Tbilissi", "yerevan": "Erevan", "baku": "Bakou",
    "tashkent": "Tachkent", "almaty": "Almaty",
    "palma": "Palma de Majorque", "palma de mallorca": "Palma de Majorque",
    "ibiza": "Ibiza", "tenerife": "Tenerife", "gran canaria": "Grande Canarie",
    "lanzarote": "Lanzarote", "fuerteventura": "Fuerteventura",
    "rhodes": "Rhodes", "corfu": "Corfou", "heraklion": "Héraklion",
    "mykonos": "Mykonos", "santorini": "Santorin",
    "dubrovnik": "Dubrovnik", "split": "Split", "zadar": "Zadar",
}

def _clean_dest_name(name: str) -> str:
    """Retire le code IATA et les suffixes de gare, traduit EN→FR."""
    cleaned = _re.sub(r'\s+[A-Z]{2,4}(?=\s|$)', '', name)
    for suffix in [
        "Matabiau", "Saint-Charles", "Saint-Lazare", "Gare de Lyon", "Montparnasse",
        "Part-Dieu", "Perrache", "Austerlitz", "Bercy Seine", "Bercy",
        "Rive Droite", "Rive Gauche", "Avenue de Paris", "Saint-Jean",
        "Saint-Gervais", "Saint-Roch", "Saint-Lazare",
        "Les Bénédictins", "Ville", "Centrale", "Centraal",
        "Hbf", "Hauptbahnhof", "Sants", "Termini",
        "Porta Susa", "Santa Lucia", "Keleti", "Hlavni", "Oriente",
        "Piraeus", "Atocha", "Joaquin Sorolla", "Santa Justa",
        "Victoria", "St Pancras", "Heathrow", "Gatwick", "Stansted",
        "Luton", "City Airport", "International",
    ]:
        cleaned = _re.sub(rf'\s+{_re.escape(suffix)}.*', '', cleaned, flags=_re.IGNORECASE)
    cleaned = cleaned.strip()
    return _EN_TO_FR.get(cleaned.lower(), cleaned)


@router.get("/destinations", response_model=list[dict])
async def get_popular_destinations(
    db: Annotated[Session, Depends(get_db)],
    depart: str = Query(default="Paris"),
    limit: int = Query(default=24, ge=1, le=60),
):
    """Mix mondial de destinations : proches, Europe, monde entier."""
    # Tierce par tranches de prix pour couvrir proche + Europe + monde
    tiers = [
        (0,    80,   6),   # proche / pas cher
        (80,   200,  8),   # Europe
        (200,  500,  6),   # long-courrier
        (500, 9999,  4),   # très long-courrier
    ]
    seen_names: set[str] = set()
    results = []

    for price_min, price_max, n in tiers:
        rows = (
            db.query(Route.arrivee, func.min(Route.base_price).label("prix_min"))
            .filter(
                Route.depart.ilike(f"%{depart}%"),
                Route.base_price >= price_min,
                Route.base_price < price_max,
            )
            .group_by(Route.arrivee)
            .order_by(func.random())
            .limit(n * 4)   # sur-échantillonne pour dédupliquer les noms
            .all()
        )
        for r in rows:
            clean = _clean_dest_name(r.arrivee)
            if clean.lower() in seen_names:
                continue
            seen_names.add(clean.lower())
            pays = _get_pays(clean)
            results.append({"ville": clean, "prix_min": round(r.prix_min, 2), "pays": pays, "photo_url": None})
            if len([x for x in results if x["prix_min"] >= price_min and x["prix_min"] < price_max]) >= n:
                break

    final = results[:limit]
    # Fetch images concurrently
    photos = await asyncio.gather(*[get_image(d["ville"]) for d in final], return_exceptions=True)
    for d, photo in zip(final, photos):
        if isinstance(photo, str):
            d["photo_url"] = photo

    return final


def _get_pays(ville: str) -> str:
    """Retourne le pays d'une ville (nom nettoyé FR)."""
    v = "".join(
        c for c in unicodedata.normalize("NFD", ville.lower())
        if unicodedata.category(c) != "Mn"
    )
    for key, pays in _CITY_TO_PAYS.items():
        if v.startswith(key) or key in v:
            return pays
    return ""


_CITY_TO_PAYS: dict[str, str] = {
    # France
    "paris": "France", "lyon": "France", "marseille": "France", "toulouse": "France",
    "nice": "France", "bordeaux": "France", "nantes": "France", "strasbourg": "France",
    "montpellier": "France", "rennes": "France", "lille": "France", "grenoble": "France",
    "toulon": "France", "rouen": "France", "reims": "France", "saint-etienne": "France",
    "le havre": "France", "dijon": "France", "angers": "France", "nimes": "France",
    "villeurbanne": "France", "le mans": "France", "aix-en-provence": "France",
    "clermont-ferrand": "France", "brest": "France", "tours": "France", "limoges": "France",
    "amiens": "France", "perpignan": "France", "metz": "France", "besancon": "France",
    "orleans": "France", "mulhouse": "France", "caen": "France", "nancy": "France",
    "pau": "France", "biarritz": "France", "bayonne": "France", "quimper": "France",
    "laon": "France", "calais": "France", "dunkerque": "France", "cherbourg": "France",
    "lorient": "France", "vannes": "France", "poitiers": "France", "la rochelle": "France",
    "chambery": "France", "annecy": "France", "lannion": "France", "rodez": "France",
    "aurillac": "France", "vesoul": "France", "chaumont": "France", "troyes": "France",
    "blois": "France", "montauban": "France", "agen": "France", "brive": "France",
    "nevers": "France", "auch": "France", "creil": "France", "cambrai": "France",
    "avignon": "France", "ajaccio": "France", "calvi": "France", "bastia": "France",
    "figari": "France", "castres": "France", "carcassonne": "France", "tarbes": "France",
    "bergerac": "France", "libourne": "France", "perigueux": "France", "angouleme": "France",
    "la defense": "France", "rambouillet": "France", "versailles": "France",
    "fort-de-france": "France", "pointe-a-pitre": "France", "saint-denis": "France",
    "cayenne": "France", "papeete": "France", "noumea": "France",
    # Belgique
    "bruxelles": "Belgique", "bruges": "Belgique", "gand": "Belgique", "liege": "Belgique",
    "anvers": "Belgique", "mons": "Belgique",
    # Luxembourg
    "luxembourg": "Luxembourg",
    # Suisse
    "geneve": "Suisse", "zurich": "Suisse", "bale": "Suisse", "berne": "Suisse",
    "lausanne": "Suisse", "lugano": "Suisse",
    # Allemagne
    "berlin": "Allemagne", "munich": "Allemagne", "francfort": "Allemagne",
    "hambourg": "Allemagne", "cologne": "Allemagne", "dusseldorf": "Allemagne",
    "nuremberg": "Allemagne", "stuttgart": "Allemagne", "hannover": "Allemagne",
    "bremen": "Allemagne", "leipzig": "Allemagne", "dresde": "Allemagne",
    "francfort": "Allemagne", "dortmund": "Allemagne",
    # Royaume-Uni
    "londres": "Royaume-Uni", "manchester": "Royaume-Uni", "birmingham": "Royaume-Uni",
    "edimbourg": "Royaume-Uni", "glasgow": "Royaume-Uni", "cardiff": "Royaume-Uni",
    "bristol": "Royaume-Uni", "southampton": "Royaume-Uni", "exeter": "Royaume-Uni",
    "newcastle": "Royaume-Uni", "leeds": "Royaume-Uni", "liverpool": "Royaume-Uni",
    "brighton": "Royaume-Uni", "oxford": "Royaume-Uni", "cambridge": "Royaume-Uni",
    # Pays-Bas
    "amsterdam": "Pays-Bas", "rotterdam": "Pays-Bas", "la haye": "Pays-Bas",
    "eindhoven": "Pays-Bas", "utrecht": "Pays-Bas",
    # Espagne
    "barcelone": "Espagne", "madrid": "Espagne", "seville": "Espagne",
    "valence": "Espagne", "bilbao": "Espagne", "ibiza": "Espagne",
    "palma": "Espagne", "gran canaria": "Espagne", "tenerife": "Espagne",
    "malaga": "Espagne", "alicante": "Espagne", "saragosse": "Espagne",
    # Portugal
    "lisbonne": "Portugal", "porto": "Portugal", "faro": "Portugal",
    "funchal": "Portugal", "ponta delgada": "Portugal",
    # Italie
    "rome": "Italie", "milan": "Italie", "venise": "Italie", "florence": "Italie",
    "naples": "Italie", "turin": "Italie", "torino": "Italie", "bologne": "Italie",
    "pise": "Italie", "pisa": "Italie", "bari": "Italie", "catane": "Italie",
    "catania": "Italie", "palerme": "Italie", "cagliari": "Italie",
    # Grèce
    "athenes": "Grèce", "thessalonique": "Grèce", "heraklion": "Grèce",
    "rhodes": "Grèce", "corfou": "Grèce", "santorin": "Grèce", "mykonos": "Grèce",
    # Autriche
    "vienne": "Autriche", "salzbourg": "Autriche", "innsbruck": "Autriche",
    # Pologne
    "varsovie": "Pologne", "cracovie": "Pologne", "gdansk": "Pologne", "poznan": "Pologne",
    "wroclaw": "Pologne",
    # République tchèque
    "prague": "Rép. tchèque",
    # Hongrie
    "budapest": "Hongrie",
    # Roumanie
    "bucarest": "Roumanie", "cluj": "Roumanie",
    # Scandinavie
    "stockholm": "Suède", "göteborg": "Suède", "malmo": "Suède",
    "oslo": "Norvège", "bergen": "Norvège", "trondheim": "Norvège",
    "copenhague": "Danemark", "aarhus": "Danemark",
    "helsinki": "Finlande", "tampere": "Finlande",
    "reykjavik": "Islande",
    # Pays Baltes & Europe de l'Est
    "tallinn": "Estonie", "riga": "Lettonie", "vilnius": "Lituanie",
    "varsovie": "Pologne", "minsk": "Biélorussie",
    "kiev": "Ukraine", "lviv": "Ukraine",
    "moscou": "Russie", "saint-petersbourg": "Russie",
    # Balkans
    "belgrade": "Serbie", "zagreb": "Croatie", "sarajevo": "Bosnie",
    "dubrovnik": "Croatie", "split": "Croatie",
    "ljubljana": "Slovénie", "sofia": "Bulgarie",
    "skopje": "Macédoine", "tirana": "Albanie", "pristina": "Kosovo",
    # Turquie
    "istanbul": "Turquie", "ankara": "Turquie", "izmir": "Turquie",
    "bodrum": "Turquie", "antalya": "Turquie", "cappadoce": "Turquie",
    # Malte & Chypre
    "malte": "Malte", "la valette": "Malte",
    "nicosie": "Chypre", "larnaca": "Chypre",
    # Moyen-Orient
    "dubai": "Émirats", "abou dabi": "Émirats", "sharjah": "Émirats",
    "doha": "Qatar", "riyad": "Arabie Saoudite", "koweït": "Koweït",
    "amman": "Jordanie", "beyrouth": "Liban", "tel-aviv": "Israël",
    # Afrique du Nord
    "le caire": "Égypte", "alexandrie": "Égypte", "hurghada": "Égypte",
    "casablanca": "Maroc", "marrakech": "Maroc", "fes": "Maroc",
    "rabat": "Maroc", "agadir": "Maroc", "tanger": "Maroc",
    "tunis": "Tunisie", "monastir": "Tunisie", "djerba": "Tunisie",
    "alger": "Algérie", "oran": "Algérie", "constantine": "Algérie", "setif": "Algérie",
    "tripoli": "Libye",
    # Afrique subsaharienne
    "dakar": "Sénégal", "abidjan": "Côte d'Ivoire", "accra": "Ghana",
    "lagos": "Nigéria", "nairobi": "Kenya", "dar es-salam": "Tanzanie",
    "johannesburg": "Afrique du Sud", "le cap": "Afrique du Sud",
    "luanda": "Angola", "douala": "Cameroun", "yaounde": "Cameroun",
    "addis-abeba": "Éthiopie", "djibouti": "Djibouti",
    "antananarivo": "Madagascar", "saint-denis": "La Réunion",
    # Asie
    "tokyo": "Japon", "osaka": "Japon", "kyoto": "Japon",
    "seoul": "Corée du Sud", "busan": "Corée du Sud",
    "pekin": "Chine", "shanghai": "Chine", "guangzhou": "Chine", "chengdu": "Chine",
    "hong kong": "Hong Kong", "macao": "Macao",
    "taipei": "Taïwan",
    "singapour": "Singapour",
    "bangkok": "Thaïlande", "phuket": "Thaïlande", "chiang mai": "Thaïlande",
    "kuala lumpur": "Malaisie", "kota kinabalu": "Malaisie",
    "jakarta": "Indonésie", "bali": "Indonésie",
    "manille": "Philippines", "cebu": "Philippines",
    "ho chi minh": "Vietnam", "hanoi": "Vietnam",
    "phnom penh": "Cambodge", "siem reap": "Cambodge",
    "rangoon": "Myanmar",
    "new delhi": "Inde", "mumbai": "Inde", "bangalore": "Inde", "calcutta": "Inde",
    "katmandou": "Népal",
    "islamabad": "Pakistan", "karachi": "Pakistan",
    "dacca": "Bangladesh",
    "colombo": "Sri Lanka",
    # Caucase & Asie centrale
    "tbilissi": "Géorgie", "erevan": "Arménie", "bakou": "Azerbaïdjan",
    "tachkent": "Ouzbékistan", "almaty": "Kazakhstan",
    # Amériques
    "new york": "États-Unis", "los angeles": "États-Unis", "chicago": "États-Unis",
    "miami": "États-Unis", "san francisco": "États-Unis", "boston": "États-Unis",
    "washington": "États-Unis", "dallas": "États-Unis", "houston": "États-Unis",
    "atlanta": "États-Unis", "seattle": "États-Unis", "las vegas": "États-Unis",
    "orlando": "États-Unis", "new orleans": "États-Unis", "denver": "États-Unis",
    "montreal": "Canada", "toronto": "Canada", "vancouver": "Canada",
    "quebec": "Canada", "calgary": "Canada",
    "mexico": "Mexique", "cancun": "Mexique", "guadalajara": "Mexique",
    "la havane": "Cuba", "santiago de cuba": "Cuba",
    "punta cana": "Rép. dominicaine", "saint-domingue": "Rép. dominicaine",
    "fort-de-france": "Martinique", "pointe-a-pitre": "Guadeloupe",
    "bogota": "Colombie", "medellin": "Colombie",
    "lima": "Pérou", "cuzco": "Pérou",
    "quito": "Équateur", "guayaquil": "Équateur",
    "buenos aires": "Argentine", "cordoba": "Argentine",
    "santiago": "Chili",
    "sao paulo": "Brésil", "rio de janeiro": "Brésil", "brasilia": "Brésil",
    "caracas": "Venezuela",
    # Océanie
    "sydney": "Australie", "melbourne": "Australie", "brisbane": "Australie",
    "perth": "Australie", "auckland": "Nouvelle-Zélande",
    "papeete": "Polynésie française", "noumea": "Nouvelle-Calédonie",
    # Villes supplémentaires France
    "evreux": "France", "chartres": "France", "toury": "France",
    "briancon": "France", "persan": "France", "creil": "France",
    "pontorson": "France", "nogent": "France", "vernon": "France",
    "montereau": "France", "clamecy": "France", "aulnoye": "France",
    "vittel": "France", "epinal": "France", "saint-brieuc": "France",
    "vannes": "France", "lorient": "France", "quimper": "France",
    "brest": "France", "saint-malo": "France", "granville": "France",
    "cherbourg": "France", "caen": "France", "le havre": "France",
    "rouen": "France", "evreux": "France", "chartres": "France",
    "tours": "France", "le mans": "France", "angers": "France",
    "la rochelle": "France", "poitiers": "France", "niort": "France",
    "limoges": "France", "brive": "France", "clermont": "France",
    "moulins": "France", "nevers": "France", "autun": "France",
    "dijon": "France", "auxerre": "France", "avallon": "France",
    "besancon": "France", "belfort": "France", "mulhouse": "France",
    "colmar": "France", "strasbourg": "France", "metz": "France",
    "nancy": "France", "epinal": "France", "vesoul": "France",
    "chaumont": "France", "troyes": "France", "reims": "France",
    "chalons": "France", "laon": "France", "saint-quentin": "France",
    "amiens": "France", "arras": "France", "lille": "France",
    "roubaix": "France", "dunkerque": "France", "calais": "France",
    "boulogne": "France", "abbeville": "France",
    # Irlande
    "dublin": "Irlande", "cork": "Irlande", "shannon": "Irlande",
    # Algérie supplémentaire
    "annaba": "Algérie", "batna": "Algérie", "tlemcen": "Algérie",
    "bejaia": "Algérie", "skikda": "Algérie",
    # Tunisie supplémentaire
    "sfax": "Tunisie", "sousse": "Tunisie", "tozeur": "Tunisie",
    # Italie supplémentaire
    "olbia": "Italie", "alghero": "Italie", "rimini": "Italie",
    "pescara": "Italie", "brindisi": "Italie", "reggio": "Italie",
    "trieste": "Italie", "verona": "Italie", "bergamo": "Italie",
    "genova": "Italie", "genes": "Italie",
    # République tchèque
    "ostrava": "Rép. tchèque", "brno": "Rép. tchèque", "plzen": "Rép. tchèque",
    # Slovaquie
    "bratislava": "Slovaquie", "kosice": "Slovaquie",
    # Serbie & Balkans
    "novi sad": "Serbie", "nis": "Serbie",
    "mostar": "Bosnie", "banja luka": "Bosnie",
    "podgorica": "Monténégro", "budva": "Monténégro",
    # Scandinavie supplémentaire
    "stavanger": "Norvège", "tromso": "Norvège",
    "goteborg": "Suède", "goteborg": "Suède",
    "turku": "Finlande", "oulu": "Finlande",
    # Autres
    "reykjavik": "Islande",
    "larnaca": "Chypre", "paphos": "Chypre",
    "valletta": "Malte",
    # Noms anglais fréquents dans la BDD
    "brussels": "Belgique", "antwerp": "Belgique",
    "genoa": "Italie", "genes": "Italie",
    "seville": "Espagne", "vigo": "Espagne", "bilbao": "Espagne",
    "philadelphia": "États-Unis", "phoenix": "États-Unis", "detroit": "États-Unis",
    "minneapolis": "États-Unis", "portland": "États-Unis", "charlotte": "États-Unis",
    "panama city": "Panama", "panama": "Panama",
    "cotonou": "Bénin", "monrovia": "Libéria", "freetown": "Sierra Leone",
    "conakry": "Guinée", "bamako": "Mali", "ouagadougou": "Burkina Faso",
    "niamey": "Niger", "lome": "Togo", "cotonou": "Bénin",
    "libreville": "Gabon", "brazzaville": "Congo", "kinshasa": "Rép. du Congo",
    "kigali": "Rwanda", "bujumbura": "Burundi",
    "kampala": "Ouganda", "dar es-salam": "Tanzanie",
    "harare": "Zimbabwe", "lusaka": "Zambie",
    "maputo": "Mozambique", "windhoek": "Namibie",
    "gaborone": "Botswana",
    "belfast": "Royaume-Uni", "derry": "Royaume-Uni",
    "biskra": "Algérie", "bejaia": "Algérie", "tebessa": "Algérie",
    "lahore": "Pakistan", "peshawar": "Pakistan", "faisalabad": "Pakistan",
    "keflavik": "Islande", "akureyri": "Islande",
    "sao vicente": "Cap-Vert", "sal": "Cap-Vert", "praia": "Cap-Vert",
    "bahrain": "Bahreïn", "manama": "Bahreïn",
    "dzaoudzi": "Mayotte", "mamoudzou": "Mayotte",
    "pointe-noire": "Congo", "brazzaville": "Congo",
    # France villes supplémentaires
    "saint-dizier": "France", "cahors": "France", "figeac": "France", "sarlat": "France",
    "perigueux": "France", "souillac": "France", "rocamadour": "France",
    "albi": "France", "cordes": "France", "mende": "France",
    "florac": "France", "millau": "France", "rodez": "France",
}


def _strip_accents(s: str) -> str:
    """Supprime les accents : 'Étoile' → 'Etoile'."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

# Mapping pays → fragments de noms de villes pour élargir la recherche
_PAYS_TO_PREFIX: dict[str, list[str]] = {
    "france":      ["Paris", "Lyon", "Marseille", "Bordeaux", "Toulouse", "Nice", "Nantes", "Strasbourg", "Rennes", "Montpellier"],
    "espagne":     ["Madrid", "Barcelone", "Séville", "Valence", "Bilbao", "Malaga", "Grenade"],
    "spain":       ["Madrid", "Barcelona", "Seville", "Valencia", "Bilbao", "Malaga"],
    "italie":      ["Rome", "Milan", "Venise", "Florence", "Naples", "Turin"],
    "italy":       ["Rome", "Milan", "Venice", "Florence", "Naples", "Turin"],
    "allemagne":   ["Berlin", "Munich", "Francfort", "Hambourg", "Cologne", "Düsseldorf"],
    "germany":     ["Berlin", "Munich", "Frankfurt", "Hamburg", "Cologne"],
    "royaume-uni": ["Londres", "Manchester", "Edinburgh", "Birmingham", "Glasgow"],
    "uk":          ["London", "Manchester", "Edinburgh"],
    "angleterre":  ["Londres", "Manchester", "Birmingham"],
    "portugal":    ["Lisbonne", "Porto", "Faro"],
    "grece":       ["Athènes", "Thessalonique", "Héraklion", "Santorin"],
    "greece":      ["Athens", "Thessaloniki"],
    "maroc":       ["Casablanca", "Marrakech", "Rabat", "Tanger", "Fès"],
    "morocco":     ["Casablanca", "Marrakech", "Rabat"],
    "belgique":    ["Bruxelles", "Liège", "Anvers"],
    "belgium":     ["Brussels", "Liege", "Antwerp"],
    "pays-bas":    ["Amsterdam", "Rotterdam", "La Haye"],
    "netherlands": ["Amsterdam", "Rotterdam"],
    "hollande":    ["Amsterdam", "Rotterdam"],
    "suisse":      ["Genève", "Zurich", "Bâle", "Berne"],
    "switzerland": ["Geneva", "Zurich", "Basel"],
    "usa":         ["New York", "Los Angeles", "Chicago", "Miami", "San Francisco"],
    "etats-unis":  ["New York", "Los Angeles", "Chicago", "Miami"],
    "canada":      ["Montréal", "Toronto", "Vancouver", "Québec"],
    "japon":       ["Tokyo", "Osaka", "Kyoto"],
    "japan":       ["Tokyo", "Osaka"],
    "chine":       ["Pékin", "Shanghai", "Hong Kong"],
    "china":       ["Beijing", "Shanghai"],
    "tunisie":     ["Tunis", "Djerba", "Monastir", "Sfax"],
    "algerie":     ["Alger", "Oran", "Constantine", "Annaba"],
    "algérie":     ["Alger", "Oran", "Constantine"],
    "senegal":     ["Dakar"],
    "sénégal":     ["Dakar"],
}

# Traductions EN→FR pour la requête utilisateur (mots clés courants)
_EN_QUERY_TO_FR: dict[str, str] = {
    "london": "Londres", "paris": "Paris", "barcelona": "Barcelone",
    "madrid": "Madrid", "rome": "Rome", "milan": "Milan",
    "berlin": "Berlin", "munich": "Munich", "frankfurt": "Francfort",
    "hamburg": "Hambourg", "vienna": "Vienne", "brussels": "Bruxelles",
    "amsterdam": "Amsterdam", "lisbon": "Lisbonne", "athens": "Athènes",
    "istanbul": "Istanbul", "moscow": "Moscou", "cairo": "Le Caire",
    "dubai": "Dubaï", "tokyo": "Tokyo", "beijing": "Pékin",
    "new york": "New York", "los angeles": "Los Angeles",
    "montreal": "Montréal", "toronto": "Toronto",
    "casablanca": "Casablanca", "marrakech": "Marrakech",
}


@router.get("/villes", response_model=list[str])
def suggest_villes(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(default="", min_length=1),
    type: str | None = Query(default=None),
    field: str = Query(default="depart"),
    limit: int = Query(default=8, ge=1, le=20),
):
    """Autocomplétion de ville : tolère les accents manquants, l'anglais, les noms de pays."""
    col = Route.depart if field == "depart" else Route.arrivee
    q_stripped = _strip_accents(q).lower()

    # Recherche pays → on remplace q par les villes du pays
    pays_villes = _PAYS_TO_PREFIX.get(q_stripped.rstrip("s"))  # "frances" → "france"
    if not pays_villes:
        pays_villes = _PAYS_TO_PREFIX.get(q_stripped)

    if pays_villes:
        # Retourne les villes du pays qui existent vraiment dans la BDD
        seen: set[str] = set()
        out: list[str] = []
        for prefix in pays_villes:
            qry = db.query(col).filter(col.ilike(f"{prefix}%")).distinct()
            if type:
                qry = qry.filter(Route.type == type)
            for (raw,) in qry.limit(3).all():
                clean = _clean_dest_name(raw)
                if clean not in seen:
                    seen.add(clean)
                    out.append(clean)
            if len(out) >= limit:
                break
        return out[:limit]

    # Traduction EN→FR de la requête
    q_fr = _EN_QUERY_TO_FR.get(q_stripped, None)

    def _run_query(pattern: str) -> list[str]:
        qry = db.query(col).filter(col.ilike(pattern)).distinct()
        if type:
            qry = qry.filter(Route.type == type)
        return qry.order_by(col).limit(limit * 4).all()

    # Requêtes : commence par q + commence par version FR + contient q (fallback)
    raw_rows = _run_query(f"{q}%")
    if q_fr and q_fr.lower() != q.lower():
        raw_rows += _run_query(f"{q_fr}%")
    # Si peu de résultats, on cherche aussi en milieu de mot
    if len(raw_rows) < limit:
        raw_rows += _run_query(f"% {q}%")   # mot après espace (ex: "Lyon" dans "Gare de Lyon")

    seen2: set[str] = set()
    out2: list[str] = []
    for (raw,) in raw_rows:
        clean = _clean_dest_name(raw)
        # Filtre côté Python avec normalisation des accents
        clean_norm = _strip_accents(clean).lower()
        q_norm = _strip_accents(q).lower()
        if q_norm in clean_norm and clean not in seen2:
            seen2.add(clean)
            out2.append(clean)
        if len(out2) >= limit:
            break
    return out2


@router.post("/materialize", response_model=TrajetOut)
async def materialize_trajet(
    db: Annotated[Session, Depends(get_db)],
    route_id: str = Query(...),
    date_str: str = Query(...),
):
    """Crée un vrai Trajet en BDD depuis une route dynamique (appelé à la réservation)."""
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route introuvable")

    day   = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    t_dyn = _make_trajet_out(route, day)

    existing = (
        db.query(Trajet)
        .filter(
            Trajet.type == route.type,
            Trajet.depart == route.depart,
            Trajet.arrivee == route.arrivee,
            Trajet.compagnie == route.compagnie,
            Trajet.date_depart == t_dyn.date_depart,
        )
        .first()
    )
    if existing:
        return existing

    trajet = Trajet(
        type=t_dyn.type, depart=t_dyn.depart, arrivee=t_dyn.arrivee,
        date_depart=t_dyn.date_depart, date_arrivee=t_dyn.date_arrivee,
        compagnie=t_dyn.compagnie, prix=t_dyn.prix,
        places_dispo=t_dyn.places_dispo, retard_minutes=t_dyn.retard_minutes,
        photo_url=t_dyn.photo_url, has_wifi=t_dyn.has_wifi,
        has_prise=t_dyn.has_prise, stops=t_dyn.stops, classe=t_dyn.classe,
    )
    db.add(trajet)
    db.commit()
    db.refresh(trajet)
    return trajet


@router.get("/{trajet_id}", response_model=TrajetOut)
def get_trajet(trajet_id: str, db: Annotated[Session, Depends(get_db)]):
    trajet = db.get(Trajet, trajet_id)
    if trajet is None:
        raise HTTPException(status_code=404, detail="Trajet introuvable")
    return trajet
