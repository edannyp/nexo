"""Perfila una tabla Postgres: filas, nulos y distintos por columna, y una muestra.

Uso:
    uv run python -m exploration.perfilar --conexion autocare --tabla public.vehicle
Escribe el resultado en data/perfiles/<conexion>__<tabla>.md
"""

import argparse

import psycopg
from psycopg import sql

from common.config import POSTGRES, RAIZ, postgres_dsn


def perfilar(conexion: str, tabla: str, muestra: int) -> str:
    esquema, nombre = tabla.split(".", 1) if "." in tabla else ("public", tabla)
    ident = sql.Identifier(esquema, nombre)
    with psycopg.connect(postgres_dsn(conexion)) as conn:
        total = conn.execute(sql.SQL("select count(*) from {}").format(ident)).fetchone()[0]
        columnas = conn.execute(
            "select column_name, data_type from information_schema.columns "
            "where table_schema = %s and table_name = %s order by ordinal_position",
            (esquema, nombre),
        ).fetchall()
        lineas = [
            f"# Perfil {conexion}.{esquema}.{nombre}",
            "",
            f"Filas: {total}",
            "",
            "| Columna | Tipo | % nulos | Distintos |",
            "|---|---|---|---|",
        ]
        for col, tipo in columnas:
            c = sql.Identifier(col)
            nulos, distintos = conn.execute(
                sql.SQL("select count(*) filter (where {c} is null), count(distinct {c}) from {t}").format(
                    c=c, t=ident
                )
            ).fetchone()
            pct = 100 * nulos / total if total else 0
            lineas.append(f"| {col} | {tipo} | {pct:.1f} | {distintos} |")
        filas = conn.execute(sql.SQL("select * from {} limit %s").format(ident), (muestra,)).fetchall()
    lineas += ["", f"## Muestra ({len(filas)} filas)", "", "```"]
    lineas += [" | ".join(str(v) for v in fila) for fila in filas]
    lineas.append("```")
    return "\n".join(lineas) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--conexion", choices=list(POSTGRES), required=True)
    p.add_argument("--tabla", required=True)
    p.add_argument("--muestra", type=int, default=10)
    a = p.parse_args()
    salida = RAIZ / "data" / "perfiles" / f"{a.conexion}__{a.tabla}.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(perfilar(a.conexion, a.tabla, a.muestra), encoding="utf-8")
    print(f"Perfil escrito en {salida}")


if __name__ == "__main__":
    main()
