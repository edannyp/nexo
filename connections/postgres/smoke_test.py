"""Comprueba la conexión a cada base Postgres configurada en .env."""

import psycopg

from common.config import POSTGRES, postgres_dsn


def main() -> None:
    for nombre in POSTGRES:
        dsn = postgres_dsn(nombre)
        if dsn is None:
            print(f"[--] {nombre}: sin configurar")
            continue
        try:
            with psycopg.connect(dsn) as conn:
                version = conn.execute("select version()").fetchone()[0]
                tablas = conn.execute(
                    "select count(*) from information_schema.tables "
                    "where table_schema not in ('pg_catalog', 'information_schema')"
                ).fetchone()[0]
            print(f"[ok] {nombre}: {tablas} tablas · {version.split(',')[0]}")
        except Exception as exc:  # noqa: BLE001 - queremos ver cualquier fallo
            print(f"[x ] {nombre}: {exc}")


if __name__ == "__main__":
    main()
