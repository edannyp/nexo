# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2", "python-dotenv>=1.0"]
# ///
"""Copia de referencia de AutoCare (autocare_global) a Consolidación, MercadoExterno o Nexo.

- Consolidación / MercadoExterno: esquema `ref`, contra el que validan sus triggers.
- Nexo: catálogo de atributos PIES (`meta.atributo_config`, ADR 0019) de los tipos de parte de `app.categoria`. Los atributos
  nuevos entran **deshabilitados**; la carga solo actualiza `nombre` y `requiere_uom`, nunca la configuración.
Hay que cargarla después de las migraciones y cada vez que se actualice AutoCare. Hace upsert (nunca vacía tablas).

Uso:
    uv run db/ref/cargar_ref.py consolidacion   --destino "host=... dbname=... user=... password=..."
    uv run db/ref/cargar_ref.py mercado_externo                       # destino = MERCADO_EXTERNO_* del .env
    uv run db/ref/cargar_ref.py nexo                                # destino = NEXO_* del .env
El origen siempre es AUTOCARE_* del .env (solo lectura).
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]

# (tabla destino, llave primaria, columnas, consulta en AutoCare)
VERSIONES = (
    "ref.version", ["base"], ["base", "version", "publicacion"],
    """select database_name, version, publication_date::date from vcdb_parts.db_version
       union all select database_name, version, publication_date::date from pcdb_parts.db_version
       union all select database_name, version, publication_date::date from padb_meta.db_version""",
)
COMUNES = [
    ("ref.make", ["make_id"], ["make_id", "make_name"], "select make_id, make_name from vcdb_base.make"),
    ("ref.model", ["model_id"], ["model_id", "model_name"], "select model_id, model_name from vcdb_base.model"),
    ("ref.sub_model", ["sub_model_id"], ["sub_model_id", "sub_model_name"], "select sub_model_id, sub_model_name from vcdb_base.sub_model"),
    ("ref.region", ["region_id"], ["region_id", "region_abbr", "region_name"], "select region_id, region_abbr, region_name from vcdb_parts.region"),
    ("ref.base_vehicle", ["base_vehicle_id"], ["base_vehicle_id", "year_id", "make_id", "model_id"],
     "select base_vehicle_id, year_id, make_id, model_id from vcdb_base.base_vehicle"),
]
# Atributos de los tipos de parte en alcance; {pts} = part_terminology_id de app.categoria en el destino
ATRIBUTOS_NEXO = [
    ("meta.atributo_config", ["part_terminology_id", "paid"], ["part_terminology_id", "paid", "nombre", "requiere_uom"],
     """select a.part_terminology_id, a.paid, min(pa.pa_name),
               bool_or(exists (select 1 from padb_config.meta_uom_code_assignment u where u.paptid = a.paptid))
        from padb_config.part_attribute_assignment a join padb_base.part_attribute pa on pa.paid = a.paid
        where a.part_terminology_id in ({pts})
        group by a.part_terminology_id, a.paid"""),
    ("meta.atributo_valor_permitido", ["part_terminology_id", "paid", "valid_value_id"],
     ["part_terminology_id", "paid", "valid_value_id", "valor"],
     """select distinct a.part_terminology_id, a.paid, v.valid_value_id, vv.valid_value
        from padb_config.valid_value_assignment v
        join padb_config.part_attribute_assignment a on a.paptid = v.paptid
        join padb_base.valid_value vv on vv.valid_value_id = v.valid_value_id
        where a.part_terminology_id in ({pts})"""),
]
TABLAS = {
    "consolidacion": [
        VERSIONES,
        *COMUNES,
        ("ref.part_terminology", ["part_terminology_id"], ["part_terminology_id", "nombre"],
         "select part_terminology_id, part_terminology_name from pcdb_base.part"),
        ("ref.atributo_permitido", ["part_terminology_id", "paid"], ["part_terminology_id", "paid", "nombre", "requiere_uom"],
         """select a.part_terminology_id, a.paid, min(pa.pa_name),
                   bool_or(exists (select 1 from padb_config.meta_uom_code_assignment u where u.paptid = a.paptid))
            from padb_config.part_attribute_assignment a join padb_base.part_attribute pa on pa.paid = a.paid
            group by a.part_terminology_id, a.paid"""),
        ("ref.valor_permitido", ["part_terminology_id", "paid", "valid_value_id"],
         ["part_terminology_id", "paid", "valid_value_id", "valor"],
         """select distinct a.part_terminology_id, a.paid, v.valid_value_id, vv.valid_value
            from padb_config.valid_value_assignment v
            join padb_config.part_attribute_assignment a on a.paptid = v.paptid
            join padb_base.valid_value vv on vv.valid_value_id = v.valid_value_id"""),
        ("ref.uom", ["uom_code"], ["uom_code", "nombre"], None),  # columnas de etiqueta se detectan
        ("ref.engine_config", ["engine_config_id"], ["engine_config_id"], "select engine_config_id from vcdb_config.engine_config"),
        ("ref.transmission", ["transmission_id"], ["transmission_id"], "select transmission_id from vcdb_config.transmission"),
        ("ref.equipment_base", ["equipment_base_id"], ["equipment_base_id"], "select equipment_base_id from vcdb_base.equipment_base"),
        ("ref.position", ["position_id"], ["position_id", "nombre"], None),
    ],
    "mercado_externo": [
        VERSIONES,
        *COMUNES,
        ("ref.vehicle_type", ["vehicle_type_id"], ["vehicle_type_id", "vehicle_type_name"],
         "select vehicle_type_id, vehicle_type_name from vcdb_base.vehicle_type"),
        ("ref.mfr", ["mfr_id"], ["mfr_id", "mfr_name"], "select mfr_id, mfr_name from vcdb_parts.mfr"),
        ("ref.equipment_model", ["equipment_model_id"], ["equipment_model_id", "equipment_model_name"],
         "select equipment_model_id, equipment_model_name from vcdb_base.equipment_model"),
        ("ref.equipment_base", ["equipment_base_id"], ["equipment_base_id", "mfr_id", "equipment_model_id"],
         "select equipment_base_id, mfr_id, equipment_model_id from vcdb_base.equipment_base"),
    ],
    "nexo": ATRIBUTOS_NEXO,
}


def dsn(prefijo: str) -> str:
    host = os.getenv(f"{prefijo}_HOST")
    if not host:
        sys.exit(f"Falta {prefijo}_HOST en .env")
    return (
        f"host={host} port={os.getenv(f'{prefijo}_PORT', '5432')} dbname={os.getenv(f'{prefijo}_DB')} "
        f"user={os.getenv(f'{prefijo}_USER')} password={os.getenv(f'{prefijo}_PASSWORD', '')} connect_timeout=10"
    )


def columna_etiqueta(origen: psycopg.Connection, esquema: str, tabla: str, candidatas: list[str]) -> str:
    cols = {r[0] for r in origen.execute(
        "select column_name from information_schema.columns where table_schema = %s and table_name = %s", (esquema, tabla))}
    for c in candidatas:
        if c in cols:
            return c
    return "null"


def consulta_detectada(origen: psycopg.Connection, tabla: str) -> str:
    if tabla == "ref.uom":
        et = columna_etiqueta(origen, "padb_base", "meta_uom_code", ["uom_label", "uom_description", "description", "uom_code_description"])
        return f"select uom_code, {et} from padb_base.meta_uom_code"
    if tabla == "ref.position":
        et = columna_etiqueta(origen, "pcdb_base", "position", ["position", "position_name", "name"])
        return f"select position_id, {et} from pcdb_base.position"
    raise ValueError(tabla)


def cargar(base: str, destino_dsn: str) -> None:
    with psycopg.connect(dsn("AUTOCARE")) as origen, psycopg.connect(destino_dsn) as destino:
        origen.read_only = True
        for tabla, pk, cols, consulta in TABLAS[base]:
            consulta = consulta or consulta_detectada(origen, tabla)
            if "{pts}" in consulta:
                pts = destino.execute("select string_agg(distinct part_terminology_id_defecto::text, ',') from app.categoria "
                                      "where part_terminology_id_defecto is not null").fetchone()[0]
                consulta = consulta.format(pts=pts)
            tmp = "tmp_" + tabla.split(".")[1]
            destino.execute(f"create temp table {tmp} (like {tabla} including defaults) on commit drop")
            lista = ", ".join(cols)
            with origen.cursor().copy(f"copy ({consulta}) to stdout") as src, \
                 destino.cursor().copy(f"copy {tmp} ({lista}) from stdin") as dst:
                for bloque in src:
                    dst.write(bloque)
            no_pk = [c for c in cols if c not in pk]
            accion = (f"do update set {', '.join(f'{c} = excluded.{c}' for c in no_pk)} "   # solo si cambió: sin ruido en la auditoría
                      f"where ({', '.join(f'{tabla}.{c}' for c in no_pk)}) is distinct from ({', '.join(f'excluded.{c}' for c in no_pk)})"
                      if no_pk else "do nothing")
            n = destino.execute(
                f"insert into {tabla} ({lista}) select {lista} from {tmp} on conflict ({', '.join(pk)}) {accion}").rowcount
            total = destino.execute(f"select count(*) from {tabla}").fetchone()[0]
            print(f"[ok] {tabla}: {n} insertadas/actualizadas, {total} en total")
        destino.commit()


def main() -> None:
    load_dotenv(RAIZ / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("base", choices=list(TABLAS))
    p.add_argument("--destino", help="DSN destino (por defecto, CONSOLIDACION_*, MERCADO_EXTERNO_* o NEXO_* del .env)")
    a = p.parse_args()
    cargar(a.base, a.destino or dsn({"consolidacion": "CONSOLIDACION", "mercado_externo": "MERCADO_EXTERNO", "nexo": "NEXO"}[a.base]))


if __name__ == "__main__":
    main()
