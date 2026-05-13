"""
Initialisation de la base de données SQLAlchemy.

Une seule BDD SQLite à la racine (`app.db`) qui contient :
- users, chat_sessions, messages, feedbacks (via models.py)

À ne pas confondre avec `conversations.db` qui est le checkpointer LangGraph
(mémoire conversationnelle interne à l'agent).
"""

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base

DB_URL = os.getenv("DB_URL", "sqlite:///app.db")

engine = create_engine(
    DB_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Crée toutes les tables (idempotent)."""
    Base.metadata.create_all(engine)


def reset_db() -> None:
    """Drop + recreate. Utilisé par les tests et `seed.py`."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@contextmanager
def db_session() -> Iterator[Session]:
    """Context manager pour usage hors FastAPI (scripts, tests)."""
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : yield une session puis la ferme."""
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
