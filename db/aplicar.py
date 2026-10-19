# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2", "python-dotenv>=1.0"]
# ///
"""Aplica en orden las migraciones SQL de una base (db/<base>/migraciones/V###__*.sql).

Cada archivo corre en su propia transacción y queda registrado en public.esquema_version con su checksum.
Si un archivo ya aplicado cambió, se detiene: las migraciones aplicadas no se editan, se agrega una nueva.

Uso:
    uv run db/aplicar.py consolidacion                 # usa CONSOLIDACION_* del .env
    uv run db/aplicar.py mercado_externo --dsn "host=postgres dbname=prueba user=postgres password=postgres"
    uv run db/aplicar.py consolidacion --servidor      # obligatorio si el host no es local
"""

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
BASES = {"consolidacion": "CONSOLIDACION", "mercado_externo": "MERCADO_EXTERNO"}
HOSTS_LOCALES = {"localhost", "127.0.0.1", "postgres"}


def dsn_desde_env(prefijo: str) -> str:
    load_dotenv(RAIZ / ".env")
    host = os.getenv(f"{prefijo}_HOST")
    if not host:
        sys.exit(f"Falta {prefijo}_HOST en .env")
    return (
        f"host={host} port={os.getenv(f'{prefijo}_PORT', '5432')} dbname={os.getenv(f'{prefijo}_DB')} "
        f"user={os.getenv(f'{prefijo}_USER')} password={os.getenv(f'{prefijo}_PASSWORD', '')} connect_timeout=10"
    )


def migraciones(base: str) -> list[tuple[str, Path]]:
    archivos = sorted((RAIZ / "db" / base / "migraciones").glob("V*__*.sql"))
    salida = []
    for f in archivos:
        m = re.match(r"V(\d{3})__", f.name)
        if not m:
            sys.exit(f"Nombre inválido: {f.name} (esperado V###__descripcion.sql)")
        salida.append((m.group(1), f))
    return salida


def aplicar(base: str, dsn: str) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            """create table if not exists public.esquema_version (
                 version text primary key, archivo text not null, checksum text not null,
                 aplicado_en timestamptz not null default now())"""
        )
        aplicadas = dict(conn.execute("select version, checksum from public.esquema_version").fetchall())
        for version, archivo in migraciones(base):
            sql = archivo.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            if version in aplicadas:
                if aplicadas[version] != checksum:
                    sys.exit(f"[x] {archivo.name} ya aplicada pero cambió. No edites migraciones aplicadas: crea una nueva.")
                print(f"[=] {archivo.name}")
                continue
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "insert into public.esquema_version (version, archivo, checksum) values (%s, %s, %s)",
                    (version, archivo.name, checksum),
                )
            print(f"[+] {archivo.name}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("base", choices=list(BASES))
    p.add_argument("--dsn", help="DSN explícito (por defecto, variables del .env)")
    p.add_argument("--servidor", action="store_true", help="confirma que se aplicará sobre un servidor no local")
    a = p.parse_args()
    dsn = a.dsn or dsn_desde_env(BASES[a.base])
    host = re.search(r"host=(\S+)", dsn)
    if host and host.group(1) not in HOSTS_LOCALES and not a.servidor:
        sys.exit(f"El host {host.group(1)} no es local. Repite con --servidor si de verdad quieres aplicar ahí.")
    aplicar(a.base, dsn)


if __name__ == "__main__":
    main()
