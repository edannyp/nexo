"""Clase de venta de ClickHouse (ADR 0023) y contrato del agente de revisión del catálogo.

Revision ID: 0011
Revises: 0010
"""

from pathlib import Path

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0011_clase_clickhouse_y_revision.sql"


def upgrade() -> None:
    # Cursor del driver sin parámetros: ni SQLAlchemy (":") ni psycopg ("%") reinterpretan el SQL.
    op.get_bind().connection.dbapi_connection.cursor().execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError("Nexo no se migra hacia atrás: se corrige con una migración nueva.")
