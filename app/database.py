import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lotabot.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Colonnes ajoutées après la création initiale des tables. Base.metadata.create_all
# ne modifie jamais une table déjà existante, donc on les ajoute ici à la main,
# de façon idempotente (ignore silencieusement si la colonne existe déjà).
_PENDING_COLUMNS = [
    ("trades", "external_id", "VARCHAR"),
]


def run_migrations():
    for table, column, col_type in _PENDING_COLUMNS:
        with engine.connect() as conn:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
            except Exception:
                conn.rollback()

    # Nettoyage des anciennes fausses données de démo : tout trade sans
    # external_id vient forcément de l'ancien compte de démo pré-rempli
    # (les vrais trades, eux, arrivent toujours avec un external_id via /mt5/sync).
    with engine.connect() as conn:
        try:
            conn.execute(text("DELETE FROM trades WHERE external_id IS NULL"))
            conn.commit()
        except Exception:
            conn.rollback()
