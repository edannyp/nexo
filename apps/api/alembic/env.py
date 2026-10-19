"""Migraciones de Nexo. El DDL vive en alembic/sql/*.sql; cada versión lo ejecuta tal cual."""

import os
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine

# En desarrollo, el .env de la raíz del repositorio; en la imagen Docker las variables ya vienen del entorno.
load_dotenv(next((d / ".env" for d in Path(__file__).resolve().parents if (d / ".env").is_file()), None))


def url() -> str:
    x = context.get_x_argument(as_dictionary=True)
    if "url" in x:
        return x["url"]
    return (
        f"postgresql+psycopg://{os.environ['NEXO_USER']}:{os.getenv('NEXO_PASSWORD', '')}"
        f"@{os.environ['NEXO_HOST']}:{os.getenv('NEXO_PORT', '5432')}/{os.environ['NEXO_DB']}"
    )


def run_migrations_online() -> None:
    engine = create_engine(url())
    with engine.connect() as conn:
        context.configure(connection=conn, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
