"""Migration des données SQLite (voyage.db) -> Postgres (Neon, etc.).

La table `routes` (~182 000 lignes) n'est PAS régénérable par seed.py : elle
n'existe que dans voyage.db. Ce script copie donc *les données existantes*
table par table, dans l'ordre des dépendances de clés étrangères.

Usage :
    # 1) la cible (Neon) est lue depuis DATABASE_URL
    export DATABASE_URL="postgresql+psycopg://user:pass@host/db?sslmode=require"
    # 2) la source SQLite (défaut : ./voyage.db)
    .venv/bin/python migrate_to_postgres.py
    # source personnalisée :
    .venv/bin/python migrate_to_postgres.py sqlite:///./voyage.db

Idempotent-ish : on vide chaque table cible avant d'insérer (TRUNCATE/DELETE),
donc relançable sans doublons.
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

# Importe les modèles pour que Base.metadata connaisse toutes les tables.
from app.database import Base
from app.models import (
    Admin,
    Billet,
    ChatMessage,
    ChatSession,
    Reclamation,
    Route,
    Trajet,
    User,
)

# Ordre d'insertion : parents avant enfants (FK).
# Ordre de purge : l'inverse.
ORDER = [Route, User, Trajet, Billet, Reclamation, ChatSession, ChatMessage, Admin]

BATCH = 5000


def _columns(model) -> list[str]:
    return [c.key for c in model.__mapper__.column_attrs]


def main() -> None:
    source_url = sys.argv[1] if len(sys.argv) > 1 else "sqlite:///./voyage.db"
    target_url = os.getenv("DATABASE_URL", "")
    if not target_url:
        sys.exit("DATABASE_URL (cible Postgres) est vide. Exporte-le d'abord.")
    if target_url.startswith("sqlite"):
        sys.exit("DATABASE_URL pointe sur SQLite : ce script migre VERS Postgres.")

    print(f"Source : {source_url}")
    print(f"Cible  : {target_url.split('@')[-1]}")  # masque les creds

    src_engine = create_engine(source_url, future=True)
    tgt_engine = create_engine(target_url, future=True)

    # Crée le schéma sur la cible.
    Base.metadata.create_all(tgt_engine)
    print("Schéma créé sur la cible.")

    # Purge (enfants -> parents) pour pouvoir relancer.
    with Session(tgt_engine) as tgt:
        for model in reversed(ORDER):
            tgt.execute(delete(model))
        tgt.commit()
    print("Tables cibles vidées.")

    with Session(src_engine) as src, Session(tgt_engine) as tgt:
        for model in ORDER:
            cols = _columns(model)
            rows = src.execute(select(model)).scalars().all()
            total = len(rows)
            if total == 0:
                print(f"  {model.__tablename__:16} : 0 ligne")
                continue
            mappings = [{c: getattr(r, c) for c in cols} for r in rows]
            for i in range(0, total, BATCH):
                tgt.bulk_insert_mappings(model, mappings[i : i + BATCH])
                tgt.commit()
                print(f"  {model.__tablename__:16} : {min(i + BATCH, total)}/{total}", end="\r")
            print(f"  {model.__tablename__:16} : {total}/{total} ✓        ")

    print("\nMigration terminée.")


if __name__ == "__main__":
    main()
