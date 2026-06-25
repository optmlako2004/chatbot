from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401  (enregistre les tables sur Base)

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """Migrations légères pour les bases déjà créées (create_all n'ajoute pas
    les nouvelles colonnes aux tables existantes). Idempotent."""
    inspector = inspect(engine)
    if "billets" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("billets")}
    if "nb_places" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE billets ADD COLUMN nb_places INTEGER NOT NULL DEFAULT 1"))
