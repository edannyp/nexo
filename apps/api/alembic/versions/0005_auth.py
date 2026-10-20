"""Autenticación propia: permisos por usuario, registro de accesos y auditoría de usuarios sin secretos (ADR 0015, 0022).

Revision ID: 0005
Revises: 0004
"""

from pathlib import Path

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0005_auth.sql"


def upgrade() -> None:
    # Cursor del driver sin parámetros: ni SQLAlchemy (":") ni psycopg ("%") reinterpretan el SQL.
    op.get_bind().connection.dbapi_connection.cursor().execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError("Nexo no se migra hacia atrás: se corrige con una migración nueva.")
