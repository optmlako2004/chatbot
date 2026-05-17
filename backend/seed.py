"""Peuple la BDD avec des données factices pour la démo.

Génère un large catalogue de trajets en croisant tous les lieux disponibles,
de sorte que tous les filtres (mode, départ, arrivée) retournent des résultats.

Usage : python seed.py
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from app.data.lieux import LIEUX_PAR_TYPE
from app.database import SessionLocal, init_db
from app.models import Admin, Billet, ChatSession, Reclamation, Trajet, User
from app.routers.admin import _hash_password as _admin_hash
from app.services.auth import hash_password
from app.services.numeros import generate_numero_billet, generate_numero_reclamation

random.seed(42)


COMPAGNIES = {
    "avion": ["Air France", "EasyJet", "Transavia", "Lufthansa", "Ryanair", "Vueling", "ITA Airways"],
    "train": ["SNCF Voyageurs", "TGV inOui", "OUIGO", "Thalys", "Eurostar", "Trenitalia", "DB"],
    "bateau": ["Corsica Linea", "La Méridionale", "Brittany Ferries", "Moby Lines", "GNV"],
    "bus": ["FlixBus", "BlaBlaBus", "Eurolines", "RegioJet"],
}

PHOTOS = {
    "avion": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800",
    "train": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=800",
    "bateau": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800",
    "bus": "https://images.unsplash.com/photo-1494515843206-f3117d3f51b7?w=800",
}

CLASSES = {
    "avion": ["Économique", "Premium Economy", "Business"],
    "train": ["2nde · Loisir", "2nde · Pro", "1ère · Pro", "Standard"],
    "bateau": ["Pont", "Cabine 2", "Cabine 4", "Cabine premium"],
    "bus": ["Standard", "Premium", "Eco"],
}

PRIX_RANGE = {
    "avion": (49, 650),
    "train": (19, 220),
    "bateau": (35, 280),
    "bus": (9, 89),
}

DURATIONS_HOURS = {
    "avion": (1, 11),
    "train": (1, 6),
    "bateau": (2, 22),
    "bus": (2, 12),
}


NOMS = ["Dupont", "Martin", "Bernard", "Durand", "Petit", "Robert", "Richard", "Moreau",
        "Laurent", "Simon", "Michel", "Lefebvre", "Garcia", "Roux", "David", "Bertrand",
        "Morel", "Fournier", "Girard", "Bonnet"]
PRENOMS = ["Jean", "Marie", "Pierre", "Anne", "Lucas", "Camille", "Hugo", "Emma",
           "Léa", "Thomas", "Chloé", "Nathan", "Sarah", "Antoine", "Julie", "Maxime",
           "Sophie", "Arthur", "Manon", "Paul"]


def _random_date_naissance() -> date:
    year = random.randint(1960, 2005)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return date(year, month, day)


HUBS_PAR_TYPE = {
    "avion": ["Paris CDG", "Paris Orly", "Lyon Saint-Exupéry", "Marseille Provence", "Nice Côte d'Azur"],
    "train": ["Paris Gare de Lyon", "Paris Montparnasse", "Paris Nord", "Lyon Part-Dieu", "Marseille Saint-Charles", "Bordeaux Saint-Jean"],
    "bateau": ["Marseille", "Toulon", "Nice", "Sète"],
    "bus": ["Paris Bercy", "Paris La Défense", "Lyon Perrache", "Marseille Saint-Charles"],
}


def _make_trajet(type_, depart, arrivee, now):
    """Crée un trajet entre deux lieux avec des données réalistes random."""
    depart_dt = now + timedelta(days=random.randint(1, 90), hours=random.randint(5, 22))
    dur = timedelta(hours=random.uniform(*DURATIONS_HOURS[type_]))
    retard = random.choice([0] * 8 + [15, 30, 60, 120])
    pmin, pmax = PRIX_RANGE[type_]
    return Trajet(
        type=type_,
        depart=depart,
        arrivee=arrivee,
        date_depart=depart_dt,
        date_arrivee=depart_dt + dur,
        compagnie=random.choice(COMPAGNIES[type_]),
        prix=round(random.uniform(pmin, pmax), 2),
        places_dispo=random.randint(8, 120),
        retard_minutes=retard,
        photo_url=PHOTOS[type_],
        has_wifi=random.random() > 0.25,
        has_prise=random.random() > 0.30,
        stops=random.choices(["direct", "1 arrêt"], weights=[9, 1])[0],
        classe=random.choice(CLASSES[type_]),
    )


def _generate_trajets() -> list[Trajet]:
    """Génère un large catalogue garantissant que chaque hub majeur (Paris, Marseille, etc.)
    relie toutes les autres destinations de son mode, avec plusieurs créneaux par jour.

    Stratégie :
    1. Pour chaque hub : 2-3 trajets vers chaque destination du mode (couverture garantie)
    2. + ~40 trajets random pour la variété
    """
    trajets: list[Trajet] = []
    now = datetime.now(timezone.utc)

    for type_, lieux in LIEUX_PAR_TYPE.items():
        hubs = HUBS_PAR_TYPE.get(type_, [])
        autres = [l["nom"] for l in lieux]

        # Phase 1 : hub → toutes les destinations (2 créneaux chacun)
        for hub in hubs:
            for dest in autres:
                if dest == hub:
                    continue
                for _ in range(2):
                    trajets.append(_make_trajet(type_, hub, dest, now))
            # Et l'inverse : autres → hub (1 créneau)
            for src in autres:
                if src == hub:
                    continue
                trajets.append(_make_trajet(type_, src, hub, now))

        # Phase 2 : trajets random pour la variété
        for _ in range(40):
            d = random.choice(lieux)["nom"]
            a = random.choice(lieux)["nom"]
            if d == a:
                continue
            trajets.append(_make_trajet(type_, d, a, now))

    return trajets


def seed():
    init_db()
    db = SessionLocal()

    if db.query(User).count() > 0:
        print("BDD déjà peuplée, abandon.")
        db.close()
        return

    # Trajets — large catalogue avec couverture garantie depuis les hubs
    trajets = _generate_trajets()
    db.add_all(trajets)
    db.flush()

    # Users : 1 user de test + 20 fictifs
    users: list[User] = []
    test_user = User(
        nom="Moreau", prenom="Camille",
        date_naissance=date(1998, 3, 14),
        email="camille@test.fr",
        telephone="0624183347",
        password_hash=hash_password("test1234"),
    )
    users.append(test_user)
    for i in range(20):
        nom = random.choice(NOMS)
        prenom = random.choice(PRENOMS)
        u = User(
            nom=nom,
            prenom=prenom,
            date_naissance=_random_date_naissance(),
            email=f"{prenom.lower()}.{nom.lower()}{i}@example.fr",
            telephone=f"06{random.randint(10000000, 99999999)}",
        )
        users.append(u)
    db.add_all(users)
    db.flush()

    # Billets
    billets: list[Billet] = []
    for _ in range(40):
        user = random.choice(users)
        trajet = random.choice(trajets)
        if trajet.places_dispo <= 0:
            continue
        b = Billet(
            user_id=user.id,
            trajet_id=trajet.id,
            numero_billet=generate_numero_billet(),
            siege=f"{random.randint(1, 40)}{random.choice('ABCDEF')}",
            voiture=str(random.randint(1, 14)) if trajet.type == "train" else None,
            tarif=random.choice(["Loisir", "Pro", "Standard", "Premium"]),
            prix_paye=trajet.prix,
        )
        trajet.places_dispo -= 1
        billets.append(b)
    db.add_all(billets)
    db.flush()

    # Réclamations
    for _ in range(8):
        b = random.choice(billets)
        rec = Reclamation(
            user_id=b.user_id,
            billet_id=b.id,
            type=random.choice(["bagage", "incident", "remboursement", "autre"]),
            description="Réclamation de démonstration générée automatiquement.",
            numero_suivi=generate_numero_reclamation(),
        )
        db.add(rec)

    admin = Admin(email="admin@voyage.local", password_hash=_admin_hash("changeme"))
    db.add(admin)

    db.commit()

    by_type = {}
    for t in trajets:
        by_type[t.type] = by_type.get(t.type, 0) + 1
    print(f"Seed OK : {len(trajets)} trajets ({by_type}), {len(users)} users, {len(billets)} billets")

    print("\nCompte utilisateur de test :")
    print("  Email    : camille@test.fr")
    print("  Password : test1234")
    print("\nExemples de billets pour tester le chatbot :")
    for b in billets[:3]:
        u = next(x for x in users if x.id == b.user_id)
        print(f"  - {b.numero_billet} → {u.prenom} {u.nom} né(e) le {u.date_naissance:%d/%m/%Y}")
    print("\nAdmin: admin@voyage.local / changeme")

    db.close()


if __name__ == "__main__":
    seed()
