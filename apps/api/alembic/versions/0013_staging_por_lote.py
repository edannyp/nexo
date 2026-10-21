"""Staging con una fila por artículo y lote: el ETL solo agrega filas (sin upsert).

Revision ID: 0013
Revises: 0012
"""

from pathlib import Path

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0013_staging_por_lote.sql"


def upgrade() -> None:
    # Cursor del driver sin parámetros: ni SQLAlchemy (":") ni psycopg ("%") reinterpretan el SQL.
    op.get_bind().connection.dbapi_connection.cursor().execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError("Nexo no se migra hacia atrás: se corrige con una migración nueva.")
