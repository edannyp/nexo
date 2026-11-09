"""Descripción armada por Nexo (ADR 0027).

Revision ID: 0017
Revises: 0016
"""

from pathlib import Path

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0017_descripcion_nexo.sql"


def upgrade() -> None:
    # Cursor del driver sin parámetros: ni SQLAlchemy (":") ni psycopg ("%") reinterpretan el SQL.
    op.get_bind().connection.dbapi_connection.cursor().execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError("Nexo no se migra hacia atrás: se corrige con una migración nueva.")
