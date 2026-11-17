"""Solicitud de campos y campos oficiales (ADR 0030).

Revision ID: 0020
Revises: 0019
"""

from pathlib import Path

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0020_solicitud_de_campos.sql"


def upgrade() -> None:
    # Cursor del driver sin parámetros: ni SQLAlchemy (":") ni psycopg ("%") reinterpretan el SQL.
    op.get_bind().connection.dbapi_connection.cursor().execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError("Nexo no se migra hacia atrás: se corrige con una migración nueva.")
