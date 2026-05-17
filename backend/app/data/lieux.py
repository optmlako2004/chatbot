"""Catalogue statique de lieux par mode de transport.

Utilisé pour :
- Le seed massif (générer des trajets réalistes)
- L'autocomplete frontend (endpoint /lieux)
"""

from __future__ import annotations

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
    # Long-courrier
    {"nom": "New York JFK", "ville": "New York", "pays": "États-Unis", "code": "JFK"},
    {"nom": "Montréal Trudeau", "ville": "Montréal", "pays": "Canada", "code": "YUL"},
    {"nom": "Tokyo Haneda", "ville": "Tokyo", "pays": "Japon", "code": "HND"},
    {"nom": "Bangkok Suvarnabhumi", "ville": "Bangkok", "pays": "Thaïlande", "code": "BKK"},
    {"nom": "Le Cap", "ville": "Le Cap", "pays": "Afrique du Sud", "code": "CPT"},
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
    """Cherche les lieux contenant `query` (insensible casse), filtre par type si fourni."""
    q = (query or "").strip().lower()
    if type_transport and type_transport in LIEUX_PAR_TYPE:
        catalogues = [(type_transport, LIEUX_PAR_TYPE[type_transport])]
    else:
        catalogues = list(LIEUX_PAR_TYPE.items())

    results = []
    for type_, lieux in catalogues:
        for l in lieux:
            haystack = f"{l['nom']} {l['ville']} {l['pays']} {l.get('code','')}".lower()
            if not q or q in haystack:
                results.append({**l, "type": type_})
            if len(results) >= limit * 4:
                break
        if len(results) >= limit * 4:
            break
    return results[:limit]
