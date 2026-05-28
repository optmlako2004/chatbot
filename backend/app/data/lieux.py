"""Catalogue statique de lieux par mode de transport.

Utilisé pour :
- Le seed massif (générer des trajets réalistes)
- L'autocomplete frontend (endpoint /lieux)
"""

from __future__ import annotations

import unicodedata


def _norm(s: str) -> str:
    """Minuscules + supprime les accents pour la comparaison."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


# Traductions courantes EN→FR pour la recherche
_EN_TO_FR_QUERY: dict[str, list[str]] = {
    # Anglais → noms FR (et noms EN pour la recherche BDD)
    "london":        ["Londres", "London"],
    "rome":          ["Rome"],
    "milan":         ["Milan"],
    "florence":      ["Florence"],
    "venice":        ["Venise", "Venice"],
    "naples":        ["Naples"],
    "vienna":        ["Vienne", "Vienna"],
    "munich":        ["Munich"],
    "berlin":        ["Berlin"],
    "frankfurt":     ["Francfort", "Frankfurt"],
    "hamburg":       ["Hambourg", "Hamburg"],
    "cologne":       ["Cologne"],
    "amsterdam":     ["Amsterdam"],
    "brussels":      ["Bruxelles", "Brussels"],
    "lisbon":        ["Lisbonne", "Lisbon"],
    "athens":        ["Athènes", "Athens"],
    "istanbul":      ["Istanbul"],
    "moscow":        ["Moscou", "Moscow"],
    "cairo":         ["Le Caire", "Cairo"],
    "dubai":         ["Dubaï", "Dubai"],
    "tokyo":         ["Tokyo"],
    "osaka":         ["Osaka"],
    "beijing":       ["Pékin", "Beijing"],
    "montreal":      ["Montréal", "Montreal"],
    "toronto":       ["Toronto"],
    "new york":      ["New York"],
    "casablanca":    ["Casablanca"],
    "marrakech":     ["Marrakech"],
    "barcelona":     ["Barcelone", "Barcelona"],
    "madrid":        ["Madrid"],
    "seville":       ["Séville", "Seville"],
    "copenhagen":    ["Copenhague", "Copenhagen"],
    "stockholm":     ["Stockholm"],
    "oslo":          ["Oslo"],
    "zurich":        ["Zurich"],
    "geneva":        ["Genève", "Geneva"],
    "prague":        ["Prague"],
    "warsaw":        ["Varsovie", "Warsaw"],
    "budapest":      ["Budapest"],
    "bucharest":     ["Bucarest", "Bucharest"],
    "zagreb":        ["Zagreb"],
    "sofia":         ["Sofia"],
    "porto":         ["Porto"],
    "faro":          ["Faro"],
    # Pays → villes principales
    "france":        ["Paris", "Lyon", "Marseille", "Bordeaux", "Nice", "Toulouse", "Nantes"],
    "spain":         ["Madrid", "Barcelone", "Séville", "Valence"],
    "espagne":       ["Madrid", "Barcelone", "Séville", "Valence"],
    "italy":         ["Rome", "Milan", "Naples", "Florence", "Venise", "Turin"],
    "italie":        ["Rome", "Milan", "Naples", "Florence", "Venise"],
    "germany":       ["Berlin", "Munich", "Francfort", "Hambourg", "Cologne"],
    "allemagne":     ["Berlin", "Munich", "Francfort", "Hambourg"],
    "uk":            ["Londres"],
    "england":       ["Londres"],
    "angleterre":    ["Londres"],
    "royaume-uni":   ["Londres"],
    "portugal":      ["Lisbonne", "Porto", "Faro"],
    "greece":        ["Athènes", "Santorin", "Mykonos"],
    "grece":         ["Athènes", "Santorin", "Mykonos", "Héraklion"],
    "morocco":       ["Marrakech", "Casablanca", "Rabat", "Tanger"],
    "maroc":         ["Marrakech", "Casablanca", "Rabat", "Tanger"],
    "tunisia":       ["Tunis", "Djerba"],
    "tunisie":       ["Tunis", "Djerba"],
    "algeria":       ["Alger", "Oran"],
    "algerie":       ["Alger", "Oran"],
    "netherlands":   ["Amsterdam"],
    "pays-bas":      ["Amsterdam", "Rotterdam"],
    "belgium":       ["Bruxelles", "Liège"],
    "belgique":      ["Bruxelles", "Liège"],
    "switzerland":   ["Genève", "Zurich", "Bâle"],
    "suisse":        ["Genève", "Zurich"],
    "austria":       ["Vienne"],
    "autriche":      ["Vienne"],
    "usa":           ["New York", "Los Angeles", "Miami", "Chicago", "San Francisco"],
    "etats-unis":    ["New York", "Los Angeles", "Miami"],
    "canada":        ["Montréal", "Toronto", "Vancouver"],
    "japan":         ["Tokyo", "Osaka", "Kyoto"],
    "japon":         ["Tokyo", "Osaka"],
    "china":         ["Pékin", "Shanghai"],
    "chine":         ["Pékin", "Shanghai"],
    "senegal":       ["Dakar"],
    "sénégal":       ["Dakar"],
    "dubai":         ["Dubaï"],
    "emirats":       ["Dubaï"],
    "turkey":        ["Istanbul", "Ankara"],
    "turquie":       ["Istanbul", "Ankara"],
    # Afrique
    "egypte":        ["Le Caire", "Cairo", "Hurghada", "Sharm"],
    "egypt":         ["Le Caire", "Cairo", "Hurghada"],
    "kenya":         ["Nairobi", "Mombasa"],
    "afrique du sud":["Le Cap", "Johannesburg"],
    "south africa":  ["Le Cap", "Johannesburg"],
    "nigeria":       ["Lagos", "Abuja"],
    "ghana":         ["Accra"],
    "cote d ivoire": ["Abidjan"],
    "ivory coast":   ["Abidjan"],
    "madagascar":    ["Antananarivo"],
    "reunion":       ["Saint-Denis de la Réunion"],
    "martinique":    ["Fort-de-France"],
    "guadeloupe":    ["Pointe-à-Pitre"],
    "ethiopie":      ["Addis-Abeba"],
    "ethiopia":      ["Addis-Abeba"],
    # Asie
    "inde":          ["Mumbai", "Delhi", "Bangalore", "Chennai"],
    "india":         ["Mumbai", "Delhi", "Bangalore"],
    "thaïlande":     ["Bangkok", "Phuket", "Chiang Mai"],
    "thailand":      ["Bangkok", "Phuket"],
    "vietnam":       ["Hô Chi Minh-Ville", "Hanoi"],
    "indonesie":     ["Bali", "Jakarta"],
    "indonesia":     ["Bali", "Jakarta"],
    "singapour":     ["Singapour"],
    "singapore":     ["Singapour"],
    "hong kong":     ["Hong Kong"],
    "coree":         ["Séoul"],
    "korea":         ["Séoul"],
    "russie":        ["Moscou", "Saint-Pétersbourg"],
    "russia":        ["Moscou"],
    # Amériques
    "mexique":       ["Mexico", "Cancún"],
    "mexico":        ["Mexico"],
    "bresil":        ["São Paulo", "Rio de Janeiro", "Brasilia"],
    "brazil":        ["São Paulo", "Rio de Janeiro"],
    "argentine":     ["Buenos Aires"],
    "argentina":     ["Buenos Aires"],
    "colombie":      ["Bogota"],
    "colombia":      ["Bogota"],
    "perou":         ["Lima"],
    "peru":          ["Lima"],
    "chili":         ["Santiago"],
    "chile":         ["Santiago"],
    "cuba":          ["La Havane"],
    "republique dominicaine": ["Punta Cana", "Saint-Domingue"],
    # Océanie
    "australie":     ["Sydney", "Melbourne", "Brisbane"],
    "australia":     ["Sydney", "Melbourne"],
    "nouvelle-zelande": ["Auckland", "Wellington"],
}

LIEUX_AVION = [
    # France
    {"nom": "Paris CDG", "ville": "Paris", "pays": "France", "code": "CDG"},
    {"nom": "Paris Orly", "ville": "Paris", "pays": "France", "code": "ORY"},
    {"nom": "Lyon Saint-Exupéry", "ville": "Lyon", "pays": "France", "code": "LYS"},
    {"nom": "Marseille Provence", "ville": "Marseille", "pays": "France", "code": "MRS"},
    {"nom": "Nice Côte d'Azur", "ville": "Nice", "pays": "France", "code": "NCE"},
    {"nom": "Toulouse Blagnac", "ville": "Toulouse", "pays": "France", "code": "TLS"},
    {"nom": "Bordeaux Mérignac", "ville": "Bordeaux", "pays": "France", "code": "BOD"},
    {"nom": "Nantes Atlantique", "ville": "Nantes", "pays": "France", "code": "NTE"},
    {"nom": "Strasbourg", "ville": "Strasbourg", "pays": "France", "code": "SXB"},
    {"nom": "Montpellier", "ville": "Montpellier", "pays": "France", "code": "MPL"},
    # Europe
    {"nom": "Londres Heathrow", "ville": "Londres", "pays": "Royaume-Uni", "code": "LHR"},
    {"nom": "Londres Gatwick", "ville": "Londres", "pays": "Royaume-Uni", "code": "LGW"},
    {"nom": "Madrid Barajas", "ville": "Madrid", "pays": "Espagne", "code": "MAD"},
    {"nom": "Barcelone El Prat", "ville": "Barcelone", "pays": "Espagne", "code": "BCN"},
    {"nom": "Valence (Espagne) Manises", "ville": "Valence", "pays": "Espagne", "code": "VLC"},
    {"nom": "Séville San Pablo", "ville": "Séville", "pays": "Espagne", "code": "SVQ"},
    {"nom": "Palma de Majorque", "ville": "Palma", "pays": "Espagne", "code": "PMI"},
    {"nom": "Malaga", "ville": "Malaga", "pays": "Espagne", "code": "AGP"},
    {"nom": "Rome Fiumicino", "ville": "Rome", "pays": "Italie", "code": "FCO"},
    {"nom": "Milan Malpensa", "ville": "Milan", "pays": "Italie", "code": "MXP"},
    {"nom": "Berlin Brandenburg", "ville": "Berlin", "pays": "Allemagne", "code": "BER"},
    {"nom": "Munich", "ville": "Munich", "pays": "Allemagne", "code": "MUC"},
    {"nom": "Francfort", "ville": "Francfort", "pays": "Allemagne", "code": "FRA"},
    {"nom": "Amsterdam Schiphol", "ville": "Amsterdam", "pays": "Pays-Bas", "code": "AMS"},
    {"nom": "Bruxelles Zaventem", "ville": "Bruxelles", "pays": "Belgique", "code": "BRU"},
    {"nom": "Zurich", "ville": "Zurich", "pays": "Suisse", "code": "ZRH"},
    {"nom": "Lisbonne Portela", "ville": "Lisbonne", "pays": "Portugal", "code": "LIS"},
    {"nom": "Porto", "ville": "Porto", "pays": "Portugal", "code": "OPO"},
    {"nom": "Athènes", "ville": "Athènes", "pays": "Grèce", "code": "ATH"},
    {"nom": "Santorin", "ville": "Santorin", "pays": "Grèce", "code": "JTR"},
    {"nom": "Mykonos", "ville": "Mykonos", "pays": "Grèce", "code": "JMK"},
    {"nom": "Heraklion (Crète)", "ville": "Héraklion", "pays": "Grèce", "code": "HER"},
    {"nom": "Naples", "ville": "Naples", "pays": "Italie", "code": "NAP"},
    {"nom": "Venise Marco Polo", "ville": "Venise", "pays": "Italie", "code": "VCE"},
    {"nom": "Faro", "ville": "Faro", "pays": "Portugal", "code": "FAO"},
    {"nom": "Vienne", "ville": "Vienne", "pays": "Autriche", "code": "VIE"},
    {"nom": "Copenhague", "ville": "Copenhague", "pays": "Danemark", "code": "CPH"},
    {"nom": "Stockholm Arlanda", "ville": "Stockholm", "pays": "Suède", "code": "ARN"},
    {"nom": "Oslo Gardermoen", "ville": "Oslo", "pays": "Norvège", "code": "OSL"},
    # Maghreb / Moyen-Orient
    {"nom": "Marrakech Menara", "ville": "Marrakech", "pays": "Maroc", "code": "RAK"},
    {"nom": "Casablanca Mohammed V", "ville": "Casablanca", "pays": "Maroc", "code": "CMN"},
    {"nom": "Alger Houari Boumédiène", "ville": "Alger", "pays": "Algérie", "code": "ALG"},
    {"nom": "Tunis Carthage", "ville": "Tunis", "pays": "Tunisie", "code": "TUN"},
    {"nom": "Dubaï International", "ville": "Dubaï", "pays": "Émirats", "code": "DXB"},
    {"nom": "Istanbul", "ville": "Istanbul", "pays": "Turquie", "code": "IST"},
    # Afrique & Moyen-Orient
    {"nom": "Le Caire", "ville": "Le Caire", "pays": "Égypte", "code": "CAI"},
    {"nom": "Hurghada", "ville": "Hurghada", "pays": "Égypte", "code": "HRG"},
    {"nom": "Sharm el-Sheikh", "ville": "Sharm el-Sheikh", "pays": "Égypte", "code": "SSH"},
    {"nom": "Dakar", "ville": "Dakar", "pays": "Sénégal", "code": "DKR"},
    {"nom": "Abidjan", "ville": "Abidjan", "pays": "Côte d'Ivoire", "code": "ABJ"},
    {"nom": "Nairobi", "ville": "Nairobi", "pays": "Kenya", "code": "NBO"},
    {"nom": "Lagos", "ville": "Lagos", "pays": "Nigeria", "code": "LOS"},
    {"nom": "Johannesburg", "ville": "Johannesburg", "pays": "Afrique du Sud", "code": "JNB"},
    {"nom": "Addis-Abeba", "ville": "Addis-Abeba", "pays": "Éthiopie", "code": "ADD"},
    {"nom": "Accra", "ville": "Accra", "pays": "Ghana", "code": "ACC"},
    # Long-courrier
    {"nom": "New York JFK", "ville": "New York", "pays": "États-Unis", "code": "JFK"},
    {"nom": "Los Angeles", "ville": "Los Angeles", "pays": "États-Unis", "code": "LAX"},
    {"nom": "Miami", "ville": "Miami", "pays": "États-Unis", "code": "MIA"},
    {"nom": "Montréal Trudeau", "ville": "Montréal", "pays": "Canada", "code": "YUL"},
    {"nom": "Toronto Pearson", "ville": "Toronto", "pays": "Canada", "code": "YYZ"},
    {"nom": "Vancouver", "ville": "Vancouver", "pays": "Canada", "code": "YVR"},
    {"nom": "Mexico", "ville": "Mexico", "pays": "Mexique", "code": "MEX"},
    {"nom": "Cancún", "ville": "Cancún", "pays": "Mexique", "code": "CUN"},
    {"nom": "Bogota", "ville": "Bogota", "pays": "Colombie", "code": "BOG"},
    {"nom": "São Paulo", "ville": "São Paulo", "pays": "Brésil", "code": "GRU"},
    {"nom": "Buenos Aires", "ville": "Buenos Aires", "pays": "Argentine", "code": "EZE"},
    {"nom": "Lima", "ville": "Lima", "pays": "Pérou", "code": "LIM"},
    {"nom": "Tokyo Haneda", "ville": "Tokyo", "pays": "Japon", "code": "HND"},
    {"nom": "Osaka", "ville": "Osaka", "pays": "Japon", "code": "KIX"},
    {"nom": "Seoul Incheon", "ville": "Séoul", "pays": "Corée du Sud", "code": "ICN"},
    {"nom": "Bangkok Suvarnabhumi", "ville": "Bangkok", "pays": "Thaïlande", "code": "BKK"},
    {"nom": "Singapour Changi", "ville": "Singapour", "pays": "Singapour", "code": "SIN"},
    {"nom": "Hong Kong", "ville": "Hong Kong", "pays": "Hong Kong", "code": "HKG"},
    {"nom": "Kuala Lumpur", "ville": "Kuala Lumpur", "pays": "Malaisie", "code": "KUL"},
    {"nom": "Mumbai", "ville": "Mumbai", "pays": "Inde", "code": "BOM"},
    {"nom": "Delhi", "ville": "Delhi", "pays": "Inde", "code": "DEL"},
    {"nom": "Sydney", "ville": "Sydney", "pays": "Australie", "code": "SYD"},
    {"nom": "Le Cap", "ville": "Le Cap", "pays": "Afrique du Sud", "code": "CPT"},
    {"nom": "Moscou Sheremetyevo", "ville": "Moscou", "pays": "Russie", "code": "SVO"},
    {"nom": "La Havane", "ville": "La Havane", "pays": "Cuba", "code": "HAV"},
    {"nom": "Punta Cana", "ville": "Punta Cana", "pays": "Rép. Dominicaine", "code": "PUJ"},
]

LIEUX_TRAIN = [
    # France
    {"nom": "Paris Gare de Lyon", "ville": "Paris", "pays": "France", "code": "PLY"},
    {"nom": "Paris Montparnasse", "ville": "Paris", "pays": "France", "code": "PMO"},
    {"nom": "Paris Nord", "ville": "Paris", "pays": "France", "code": "PNO"},
    {"nom": "Paris Est", "ville": "Paris", "pays": "France", "code": "PES"},
    {"nom": "Paris Saint-Lazare", "ville": "Paris", "pays": "France", "code": "PSL"},
    {"nom": "Lyon Part-Dieu", "ville": "Lyon", "pays": "France", "code": "LPD"},
    {"nom": "Marseille Saint-Charles", "ville": "Marseille", "pays": "France", "code": "MSC"},
    {"nom": "Bordeaux Saint-Jean", "ville": "Bordeaux", "pays": "France", "code": "BSJ"},
    {"nom": "Lille Flandres", "ville": "Lille", "pays": "France", "code": "LIF"},
    {"nom": "Lille Europe", "ville": "Lille", "pays": "France", "code": "LIE"},
    {"nom": "Toulouse Matabiau", "ville": "Toulouse", "pays": "France", "code": "TMA"},
    {"nom": "Nantes", "ville": "Nantes", "pays": "France", "code": "NAN"},
    {"nom": "Strasbourg", "ville": "Strasbourg", "pays": "France", "code": "STR"},
    {"nom": "Rennes", "ville": "Rennes", "pays": "France", "code": "REN"},
    {"nom": "Nice Ville", "ville": "Nice", "pays": "France", "code": "NIC"},
    {"nom": "Montpellier Saint-Roch", "ville": "Montpellier", "pays": "France", "code": "MTP"},
    {"nom": "Valence TGV", "ville": "Valence", "pays": "France", "code": "VLN"},
    {"nom": "Avignon TGV", "ville": "Avignon", "pays": "France", "code": "AVG"},
    {"nom": "Dijon Ville", "ville": "Dijon", "pays": "France", "code": "DIJ"},
    {"nom": "Reims", "ville": "Reims", "pays": "France", "code": "REI"},
    {"nom": "Avignon TGV", "ville": "Avignon", "pays": "France", "code": "AVG"},
    {"nom": "Dijon Ville", "ville": "Dijon", "pays": "France", "code": "DIJ"},
    {"nom": "Reims", "ville": "Reims", "pays": "France", "code": "REI"},
    {"nom": "Grenoble", "ville": "Grenoble", "pays": "France", "code": "GRE"},
    # Europe
    {"nom": "Bruxelles Midi", "ville": "Bruxelles", "pays": "Belgique", "code": "BMI"},
    {"nom": "Amsterdam Centraal", "ville": "Amsterdam", "pays": "Pays-Bas", "code": "AMS"},
    {"nom": "Cologne Hbf", "ville": "Cologne", "pays": "Allemagne", "code": "CGN"},
    {"nom": "Francfort Hbf", "ville": "Francfort", "pays": "Allemagne", "code": "FRH"},
    {"nom": "Milan Centrale", "ville": "Milan", "pays": "Italie", "code": "MIC"},
    {"nom": "Turin Porta Nuova", "ville": "Turin", "pays": "Italie", "code": "TRN"},
    {"nom": "Genève Cornavin", "ville": "Genève", "pays": "Suisse", "code": "GVA"},
    {"nom": "Barcelone Sants", "ville": "Barcelone", "pays": "Espagne", "code": "BNA"},
    {"nom": "Londres St Pancras", "ville": "Londres", "pays": "Royaume-Uni", "code": "STP"},
]

LIEUX_BATEAU = [
    {"nom": "Marseille", "ville": "Marseille", "pays": "France", "code": "MRS"},
    {"nom": "Toulon", "ville": "Toulon", "pays": "France", "code": "TLN"},
    {"nom": "Nice", "ville": "Nice", "pays": "France", "code": "NCE"},
    {"nom": "Sète", "ville": "Sète", "pays": "France", "code": "SET"},
    {"nom": "Bastia", "ville": "Bastia", "pays": "France", "code": "BST"},
    {"nom": "Ajaccio", "ville": "Ajaccio", "pays": "France", "code": "AJA"},
    {"nom": "Calvi", "ville": "Calvi", "pays": "France", "code": "CLY"},
    {"nom": "Île-Rousse", "ville": "Île-Rousse", "pays": "France", "code": "IRO"},
    {"nom": "Saint-Malo", "ville": "Saint-Malo", "pays": "France", "code": "SMA"},
    {"nom": "Caen Ouistreham", "ville": "Caen", "pays": "France", "code": "CAE"},
    {"nom": "Cherbourg", "ville": "Cherbourg", "pays": "France", "code": "CBG"},
    {"nom": "Roscoff", "ville": "Roscoff", "pays": "France", "code": "ROS"},
    {"nom": "Brest", "ville": "Brest", "pays": "France", "code": "BRT"},
    {"nom": "Calais", "ville": "Calais", "pays": "France", "code": "CAL"},
    {"nom": "Tanger", "ville": "Tanger", "pays": "Maroc", "code": "TGR"},
    {"nom": "Alger", "ville": "Alger", "pays": "Algérie", "code": "ALG"},
    {"nom": "Tunis La Goulette", "ville": "Tunis", "pays": "Tunisie", "code": "TUN"},
    {"nom": "Civitavecchia (Rome)", "ville": "Rome", "pays": "Italie", "code": "CVV"},
    {"nom": "Gênes", "ville": "Gênes", "pays": "Italie", "code": "GOA"},
    {"nom": "Palerme", "ville": "Palerme", "pays": "Italie", "code": "PAL"},
    {"nom": "Naples", "ville": "Naples", "pays": "Italie", "code": "NAP"},
    {"nom": "Portsmouth", "ville": "Portsmouth", "pays": "Royaume-Uni", "code": "PSM"},
    {"nom": "Douvres", "ville": "Douvres", "pays": "Royaume-Uni", "code": "DVR"},
]

LIEUX_BUS = [
    {"nom": "Paris Bercy", "ville": "Paris", "pays": "France", "code": "PBY"},
    {"nom": "Paris La Défense", "ville": "Paris", "pays": "France", "code": "PLD"},
    {"nom": "Paris Porte Maillot", "ville": "Paris", "pays": "France", "code": "PPM"},
    {"nom": "Lyon Perrache", "ville": "Lyon", "pays": "France", "code": "LPE"},
    {"nom": "Lyon Part-Dieu", "ville": "Lyon", "pays": "France", "code": "LPD"},
    {"nom": "Marseille Saint-Charles", "ville": "Marseille", "pays": "France", "code": "MSC"},
    {"nom": "Bordeaux Centre", "ville": "Bordeaux", "pays": "France", "code": "BOC"},
    {"nom": "Toulouse Centre", "ville": "Toulouse", "pays": "France", "code": "TLC"},
    {"nom": "Nice Centre", "ville": "Nice", "pays": "France", "code": "NIC"},
    {"nom": "Lille Centre", "ville": "Lille", "pays": "France", "code": "LIC"},
    {"nom": "Strasbourg Centre", "ville": "Strasbourg", "pays": "France", "code": "STC"},
    {"nom": "Nantes", "ville": "Nantes", "pays": "France", "code": "NAN"},
    {"nom": "Rennes", "ville": "Rennes", "pays": "France", "code": "REN"},
    {"nom": "Montpellier", "ville": "Montpellier", "pays": "France", "code": "MTP"},
    {"nom": "Grenoble", "ville": "Grenoble", "pays": "France", "code": "GRE"},
    {"nom": "Bruxelles Nord", "ville": "Bruxelles", "pays": "Belgique", "code": "BNO"},
    {"nom": "Amsterdam Sloterdijk", "ville": "Amsterdam", "pays": "Pays-Bas", "code": "AMS"},
    {"nom": "Berlin ZOB", "ville": "Berlin", "pays": "Allemagne", "code": "BER"},
    {"nom": "Munich ZOB", "ville": "Munich", "pays": "Allemagne", "code": "MUC"},
    {"nom": "Milan Lampugnano", "ville": "Milan", "pays": "Italie", "code": "MIL"},
    {"nom": "Barcelone Nord", "ville": "Barcelone", "pays": "Espagne", "code": "BCN"},
    {"nom": "Madrid Méndez Álvaro", "ville": "Madrid", "pays": "Espagne", "code": "MAD"},
    {"nom": "Stuttgart", "ville": "Stuttgart", "pays": "Allemagne", "code": "STU"},
    {"nom": "Genève", "ville": "Genève", "pays": "Suisse", "code": "GVA"},
]


LIEUX_PAR_TYPE = {
    "avion": LIEUX_AVION,
    "train": LIEUX_TRAIN,
    "bateau": LIEUX_BATEAU,
    "bus": LIEUX_BUS,
}


def search_lieux(query: str = "", type_transport: str | None = None, limit: int = 12):
    """Cherche les lieux :
    - insensible aux accents (marseille = Marseille = Märseille)
    - supporte l'anglais (london → Londres, spain → Espagne)
    - supporte les noms de pays (france, italy, maroc…)
    """
    q_raw = (query or "").strip()
    q = _norm(q_raw)

    if type_transport and type_transport in LIEUX_PAR_TYPE:
        catalogues = [(type_transport, LIEUX_PAR_TYPE[type_transport])]
    else:
        catalogues = list(LIEUX_PAR_TYPE.items())

    # Si la requête correspond à un pays/traduction, on construit des termes élargis
    extra_terms: list[str] = []
    if q in _EN_TO_FR_QUERY:
        extra_terms = [_norm(t) for t in _EN_TO_FR_QUERY[q]]

    def _matches(l: dict) -> bool:
        haystack = _norm(f"{l['nom']} {l['ville']} {l['pays']} {l.get('code','')}")
        if not q:
            return True
        if q in haystack:
            return True
        # Correspondance via traduction pays/EN
        return any(term in haystack for term in extra_terms)

    results = []
    seen: set[str] = set()
    for type_, lieux in catalogues:
        for l in lieux:
            if _matches(l):
                key = f"{l['nom']}|{type_}"
                if key not in seen:
                    seen.add(key)
                    results.append({**l, "type": type_})
            if len(results) >= limit * 4:
                break
        if len(results) >= limit * 4:
            break
    return results[:limit]
