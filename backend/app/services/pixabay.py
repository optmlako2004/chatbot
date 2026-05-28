"""Images de villes via Pixabay API avec cache JSON local."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "image_cache.json"
_STATIC_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "city_photos.json"
_cache: dict[str, str] = {}

# Dataset statique : ~200+ grandes villes avec photos Unsplash curatiées
_STATIC_PHOTOS: dict[str, str] = {}


def _load_static() -> None:
    global _STATIC_PHOTOS
    if _STATIC_FILE.exists():
        try:
            _STATIC_PHOTOS = json.loads(_STATIC_FILE.read_text(encoding="utf-8"))
        except Exception:
            _STATIC_PHOTOS = {}


_load_static()

# Images de secours par mode si Pixabay ne répond pas
_FALLBACK: dict[str, str] = {
    "avion":  "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800",
    "train":  "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=800",
    "bateau": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800",
    "bus":    "https://images.unsplash.com/photo-1494515843206-f3117d3f51b7?w=800",
    "ville":  "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800",
}

# Pool de fallbacks variés pour éviter que toutes les villes inconnues aient la même image
_FALLBACK_POOL = [
    "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800",  # ville générique
    "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?w=800",  # skyline nuit
    "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=800",  # vieille ville
    "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800",    # rue animée
    "https://images.unsplash.com/photo-1507608869274-d3177c8bb4c7?w=800",  # place centrale
    "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800",  # quartier historique
    "https://images.unsplash.com/photo-1494522855154-9297ac14b55f?w=800",  # coucher soleil ville
    "https://images.unsplash.com/photo-1555993539-1732b0258235?w=800",    # marché ville
]

# URL à considérer comme "générique" — exclure du cache comme résultat valide
_GENERIC_URLS = {
    "https://cdn.pixabay.com/photo/2023/08/04/22/59/sunset-8170058_640.jpg",
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800",
}

# Mots dans le nom de fichier Pixabay qui indiquent une photo non-urbaine/hors-sujet
_FILENAME_BLACKLIST = {
    # Animaux
    "cow-", "cattle-", "horse-", "sheep-", "pig-",
    "dog-", "cat-", "rabbit-", "stork-", "swan-", "bird-",
    "pine-cones-", "mushroom-",
    # Personnes
    "man-2179", "woman-", "person-", "portrait-", "face-",
    "running-",
    # Bâtiments spécifiques mal attribués
    "reichstag-dome-",  # Reichstag Berlin, sort pour n'importe quelle ville
    "church-5894267",     # église de Lannion
    "architect-7692052",  # bâtiment générique
    "duomo-6808817",      # Duomo de Florence, sort pour des villes sans rapport
    "louvre-palace-",     # Louvre, sort pour des petites villes
    # Objets/véhicules
    "road-4911", "fan-7160", "shield-", "peugeot-",
    "train-616820",       # train générique
    "stairs-7705513",     # escaliers génériques
    "water-1460431",      # eau générique
    "door-", "house-176856",  # porte/maison génériques
    "jet-6847", "airplane-",  # avion générique
    "theater-5368958",        # théâtre générique (sort pour beaucoup de villes)
    "nissan-figaro-",         # voiture Nissan Figaro
    "tajikistan-",            # Tadjikistan pour des villes sans rapport
    "sandpipers-", "wading-", # oiseaux de rivage
    # Faune
    "amblyrhynchus-",     # iguane marin
    "iguana-", "lizard-", "reptile-",
    # Nature / générique
    "sunset-8068", "sunset-8170", "sunset-3875", "sky-388",
    "nature-", "flower-", "rose-", "tree-", "forest-", "lavender-3764",
    "countryside-", "field-", "meadow-", "grass-",
    "snow-2627", "snow-2628", "beach-5202733",
    # Nourriture
    "mandarins-", "tomatoes-", "fruit-", "food-", "vegetable-",
    # Conflit / guerre
    "war-", "tank-", "weapon-", "military-", "bomb-",
}


def _load_cache() -> None:
    global _cache
    if _CACHE_FILE.exists():
        try:
            _cache = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _cache = {}


def _save_cache() -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False, indent=2), encoding="utf-8")


_load_cache()


# Traductions FR→EN pour que Pixabay trouve mieux
_FR_TO_EN: dict[str, str] = {
    # Villes françaises
    "marseille": "marseille", "bordeaux": "bordeaux", "toulouse": "toulouse",
    "lyon": "lyon", "nice": "nice", "lille": "lille", "rennes": "rennes",
    "nantes": "nantes", "strasbourg": "strasbourg", "montpellier": "montpellier",
    "paris": "paris", "grenoble": "grenoble", "toulon": "toulon",
    # Europe — noms français → anglais pour Pixabay
    "barcelone": "barcelona", "lisbonne": "lisbon", "vienne": "vienna",
    "bruxelles": "brussels", "copenhague": "copenhagen", "genève": "geneva",
    "édimbourg": "edinburgh", "münich": "munich", "munich": "munich",
    "athènes": "athens", "varsovie": "warsaw", "bucarest": "bucharest",
    "moscou": "moscow", "francfort": "frankfurt", "hambourg": "hamburg",
    "cologne": "cologne", "düsseldorf": "dusseldorf", "bâle": "basel",
    "séville": "seville", "valence": "valencia", "venise": "venice",
    "naples": "naples", "florence": "florence", "bologne": "bologna",
    "thessalonique": "thessaloniki", "héraklion": "heraklion",
    "corfou": "corfu", "santorin": "santorini", "rhodes": "rhodes",
    "mykonos": "mykonos", "dubrovnik": "dubrovnik",
    "palma de majorque": "palma mallorca", "grande canarie": "gran canaria",
    # Monde
    "londres": "london", "dubaï": "dubai", "abou dabi": "abu dhabi",
    "le caire": "cairo", "alger": "algiers", "beyrouth": "beirut",
    "tel-aviv": "tel aviv", "riyad": "riyadh",
    "le cap": "cape town", "johannesburg": "johannesburg",
    "pékin": "beijing", "séoul": "seoul", "singapour": "singapore",
    "manille": "manila", "kuala lumpur": "kuala lumpur",
    "montréal": "montreal", "québec": "quebec city",
    "bogotá": "bogota", "são paulo": "sao paulo",
    "rio de janeiro": "rio de janeiro", "buenos aires": "buenos aires",
    "reykjavik": "reykjavik", "tallinn": "tallinn",
    "kiev": "kyiv", "tbilissi": "tbilisi", "erevan": "yerevan",
    "bakou": "baku", "tachkent": "tashkent",
    "marrakech": "marrakech", "casablanca": "casablanca",
    "katmandou": "kathmandu", "calcutta": "kolkata", "dacca": "dhaka",
    "saint-pétersbourg": "saint petersburg", "nuremberg": "nuremberg",
    "cracovie": "krakow", "göteborg": "gothenburg",
    "francfort": "frankfurt", "hambourg": "hamburg",
    "abou dabi": "abu dhabi", "beyrouth": "beirut",
    "riyad": "riyadh", "le caire": "cairo", "alexandrie": "alexandria",
    "alger": "algiers",
}

def _clean_city(query: str) -> str:
    """Extrait un nom de ville propre utilisable pour Pixabay.
    Exemples : "Barcelona BCN city travel" → "barcelona"
               "Toulouse Matabiau"        → "toulouse"
               "Paris Nord"               → "paris"
    """
    # 1. Supprime les mots génériques en queue ("city", "travel", "city travel")
    cleaned = re.sub(r'\s+(city|travel|airport|aéroport|station)\b.*', '', query.strip(), flags=re.IGNORECASE)
    # 2. Supprime les codes IATA (2-4 majuscules seules, n'importe où)
    cleaned = re.sub(r'\s+[A-Z]{2,4}(?=\s|$)', '', cleaned)
    # 3. Supprime les noms de gares/quartiers connus
    for suffix in [
        "Matabiau", "Saint-Charles", "Saint-Lazare", "Gare de Lyon",
        "Montparnasse", "Part-Dieu", "Perrache", "Austerlitz",
        "Bercy Seine", "Bercy", "La Défense", "Centrale", "Centraal",
        "Hbf", "Hauptbahnhof", "Schiphol", "Oriente",
        "Sants", "Termini", "Porta Susa", "Santa Lucia",
        "Keleti", "Hlavni", "Glavni", "Piraeus",
        "Atocha", "Joaquin Sorolla", "Santa Justa", "Maria Zambrano",
        "St Pancras", "Victoria", "Waterloo",
    ]:
        cleaned = re.sub(rf'\s+{re.escape(suffix)}.*', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    # 4. Traduit FR→EN pour de meilleures photos Pixabay
    lower = cleaned.lower()
    return _FR_TO_EN.get(lower, cleaned) or query.strip()


def _is_valid_city_photo(url: str) -> bool:
    """Retourne False si l'URL contient un mot-clé indiquant une photo hors-sujet."""
    if url in _GENERIC_URLS:
        return False
    url_lower = url.lower()
    return not any(kw in url_lower for kw in _FILENAME_BLACKLIST)


async def _pixabay_query(client: httpx.AsyncClient, q: str) -> str | None:
    """Lance une requête Pixabay, retourne l'URL CDN ou None si aucun résultat non-générique."""
    try:
        r = await client.get(
            "https://pixabay.com/api/",
            params={
                "key": settings.pixabay_api_key,
                "q": q,
                "image_type": "photo",
                "orientation": "horizontal",
                "category": "travel,places,buildings",
                "min_width": 640,
                "safesearch": "true",
                "per_page": 15,
                "order": "popular",
            },
        )
        r.raise_for_status()
        for hit in r.json().get("hits", []):
            preview = hit.get("previewURL", "")
            if preview and "cdn.pixabay.com" in preview:
                url = re.sub(r'_\d+\.', '_640.', preview)
                if _is_valid_city_photo(url):
                    return url
    except Exception as e:
        logger.warning("Pixabay erreur pour '%s': %s", q, e)
    return None


async def _wikipedia_image(client: httpx.AsyncClient, city_name: str) -> str | None:
    """Récupère la photo principale Wikipedia pour une ville (FR puis EN)."""
    title = city_name.title()
    for lang in ("fr", "en"):
        try:
            r = await client.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "pageimages",
                    "format": "json",
                    "pithumbsize": 640,
                    "redirects": 1,
                },
                timeout=4.0,
            )
            if r.status_code == 429:
                logger.debug("Wikipedia %s rate-limited pour '%s'", lang, title)
                continue
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                thumb = page.get("thumbnail", {}).get("source", "")
                if thumb and "upload.wikimedia.org" in thumb:
                    # Rejeter les SVG (drapeaux, logos, blasons)
                    if ".svg" in thumb.lower():
                        continue
                    thumb = re.sub(r'/\d+px-', '/640px-', thumb)
                    return thumb
        except Exception as e:
            logger.debug("Wikipedia %s erreur pour '%s': %s", lang, title, e)
    return None


async def get_image(query: str, fallback_mode: str = "ville") -> str:
    """Retourne une URL d'image pour la ville donnée.
    Priorité : dataset statique → Wikipedia → Pixabay → Picsum
    """
    city = _clean_city(query)
    key = city.lower().strip()

    # 1. Dataset statique (364 grandes villes Unsplash, qualité garantie)
    if key in _STATIC_PHOTOS:
        return _STATIC_PHOTOS[key]

    if key in _cache:
        return _cache[key]

    url = None
    async with httpx.AsyncClient(timeout=6.0, headers={"User-Agent": "VoyageAssistant/1.0"}) as client:
        # 2. Wikipedia (couvre toutes les villes du monde avec vraies photos)
        url = await _wikipedia_image(client, city)

        # 3. Pixabay si Wikipedia n'a rien (villes très petites sans page Wiki)
        if not url and settings.pixabay_api_key:
            country_en = _CITY_COUNTRY_EN.get(key, "")
            if country_en:
                url = await _pixabay_query(client, f"{city} {country_en}")
            if not url:
                url = await _pixabay_query(client, city)
            if not url:
                url = await _pixabay_query(client, f"{city} architecture landmark")

    if url:
        _cache[key] = url
        _save_cache()
    return url


# Mapping ville (clé = nom Pixabay nettoyé) → pays EN (pour enrichir les requêtes Pixabay)
_CITY_COUNTRY: dict[str, str] = {
    "aurillac": "France", "le mans": "France", "mulhouse": "France",
    "pau": "France", "nevers": "France", "vesoul": "France", "chaumont": "France",
    "troyes": "France", "agen": "France", "brive": "France", "auch": "France",
    "montauban": "France", "blois": "France", "castres": "France",
    "creil": "France", "cambrai": "France", "laon": "France",
}
_CITY_COUNTRY_EN: dict[str, str] = {
    "aurillac": "france auvergne", "le mans": "france sarthe", "mulhouse": "france haut-rhin",
    "pau": "france pyrenees", "nevers": "france", "vesoul": "france",
    "chaumont": "france", "troyes": "france champagne", "agen": "france",
    "brive": "france correze", "auch": "france gascogne", "montauban": "france tarn",
    "blois": "france loire", "castres": "france", "creil": "france",
    "cambrai": "france nord", "laon": "france",
    "moscow": "russia", "château-thierry": "france aisne",
    "romilly-sur-seine": "france aube", "saint-just-en-chaussée": "france oise",
}
