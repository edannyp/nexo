# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2", "python-dotenv>=1.0"]
# ///
"""Copia de referencia de AutoCare (autocare_global) a Consolidación, MercadoExterno o Nexo, versionada (ADR 0024).

- Consolidación / MercadoExterno: esquema `ref`, contra el que validan sus triggers.
- Nexo: catálogo de atributos PIES (`meta.atributo_config`, ADR 0019) de los tipos de parte de `app.categoria`. Los atributos
  nuevos entran **deshabilitados**; la carga solo actualiza `nombre` y `requiere_uom`, nunca la configuración.
- PCdb/PAdb se copian **solo para nuestros tipos de parte** (las 8 categorías; `--todo` copia todo). VCdb se copia completo.
- Cada carga se compara con la anterior: altas, cambios, bajas y reactivados por tabla. Lo que AutoCare quitó **no se borra**: se
  marca `obsoleto_en` (lo obsoleto no se asigna de nuevo; lo que ya lo usa se conserva). El resultado, con el **impacto** (lo
  obsoleto o cambiado que ya está en uso), queda en `ref.historial_carga` (Nexo: `meta.historial_referencia`).
- Defensa: si una tabla quedaría con más del 20 % de sus filas obsoletas, se detiene sin tocar nada (`--forzar` para seguir).
Hay que cargarla después de las migraciones y cada vez que se actualice AutoCare.

Uso:
    uv run db/ref/cargar_ref.py consolidacion   --destino "host=... dbname=... user=... password=..."
    uv run db/ref/cargar_ref.py mercado_externo                       # destino = MERCADO_EXTERNO_* del .env
    uv run db/ref/cargar_ref.py nexo                                # destino = NEXO_* del .env
    … --nexo "<dsn de nexo>"   # en consolidacion / mercado_externo: impacto también en las aplicaciones de Nexo
El origen es AUTOCARE_* del .env (solo lectura); `--origen` solo para pruebas.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
# Tipos de parte (PCdb) de las 8 categorías de Nexo (app.categoria.part_terminology_id_defecto; context/categorias.md)
TIPOS_ALCANCE = (2172, 6708, 12616, 2084, 48305, 10457, 10707)
MAX_BAJAS = 0.20

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
         "select part_terminology_id, part_terminology_name from pcdb_base.part where part_terminology_id in ({pts})"),
        ("ref.atributo_permitido", ["part_terminology_id", "paid"], ["part_terminology_id", "paid", "nombre", "requiere_uom"],
         """select a.part_terminology_id, a.paid, min(pa.pa_name),
                   bool_or(exists (select 1 from padb_config.meta_uom_code_assignment u where u.paptid = a.paptid))
            from padb_config.part_attribute_assignment a join padb_base.part_attribute pa on pa.paid = a.paid
            where a.part_terminology_id in ({pts})
            group by a.part_terminology_id, a.paid"""),
        ("ref.valor_permitido", ["part_terminology_id", "paid", "valid_value_id"],
         ["part_terminology_id", "paid", "valid_value_id", "valor"],
         """select distinct a.part_terminology_id, a.paid, v.valid_value_id, vv.valid_value
            from padb_config.valid_value_assignment v
            join padb_config.part_attribute_assignment a on a.paptid = v.paptid
            join padb_base.valid_value vv on vv.valid_value_id = v.valid_value_id
            where a.part_terminology_id in ({pts})"""),
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


HISTORIAL = {"consolidacion": "ref.historial_carga", "mercado_externo": "ref.historial_carga", "nexo": "meta.historial_referencia"}

# Impacto: lo obsoleto o cambiado que ya está en uso. Cada consulta recibe las llaves como lista JSON (%(llaves)s) y cuenta usos.
IMPACTO = {
    ("nexo", "meta.atributo_valor_permitido"): [
        ("artículos de Nexo con ese valor", """
            select count(*), coalesce(jsonb_agg(distinct a.item_code) filter (where a.item_code is not null), '[]')
            from jsonb_to_recordset(%(llaves)s) k(part_terminology_id int, paid int, valid_value_id int)
            join app.articulo a on a.part_terminology_id = k.part_terminology_id
            join app.articulo_atributo t on t.articulo_id = a.id and t.paid = k.paid and t.valid_value_id = k.valid_value_id"""),
    ],
    ("nexo", "meta.atributo_config"): [
        ("atributos habilitados en la ficha", """
            select count(*), coalesce(jsonb_agg(c.part_terminology_id || ':' || c.paid), '[]')
            from jsonb_to_recordset(%(llaves)s) k(part_terminology_id int, paid int)
            join meta.atributo_config c using (part_terminology_id, paid) where c.habilitado"""),
        ("artículos de Nexo con ese atributo", """
            select count(*), coalesce(jsonb_agg(distinct a.item_code) filter (where a.item_code is not null), '[]')
            from jsonb_to_recordset(%(llaves)s) k(part_terminology_id int, paid int)
            join app.articulo a on a.part_terminology_id = k.part_terminology_id
            join app.articulo_atributo t on t.articulo_id = a.id and t.paid = k.paid"""),
    ],
    ("consolidacion", "ref.valor_permitido"): [
        ("atributos de partes del catálogo con ese valor", """
            select count(*), coalesce(jsonb_agg(distinct pa.parte_id), '[]') from jsonb_to_recordset(%(llaves)s) k(part_terminology_id int, paid int, valid_value_id int)
            join catalogo.parte p on p.part_terminology_id = k.part_terminology_id
            join catalogo.parte_atributo pa on pa.parte_id = p.id and pa.paid = k.paid and pa.valid_value_id = k.valid_value_id"""),
    ],
    ("consolidacion", "ref.base_vehicle"): [
        ("aplicaciones del catálogo con ese vehículo", """
            select count(*), coalesce(jsonb_agg(distinct pa.parte_id), '[]') from jsonb_to_recordset(%(llaves)s) k(base_vehicle_id int)
            join catalogo.parte_aplicacion pa using (base_vehicle_id)"""),
    ],
    ("mercado_externo", "ref.base_vehicle"): [
        ("configuraciones de MercadoExterno con ese vehículo", """
            select count(*), coalesce(jsonb_agg(distinct c.base_vehicle_id), '[]') from jsonb_to_recordset(%(llaves)s) k(base_vehicle_id int)
            join vcdb.configuracion c using (base_vehicle_id)"""),
    ],
}
# Con --nexo: vehículos obsoletos o cambiados que ya están en aplicaciones de artículos de Nexo
IMPACTO_NEXO_VEHICULOS = """
    select count(*), coalesce(jsonb_agg(distinct a.item_code) filter (where a.item_code is not null), '[]')
    from jsonb_to_recordset(%(llaves)s) k(base_vehicle_id int)
    join app.articulo_aplicacion x using (base_vehicle_id) join app.articulo a on a.id = x.articulo_id where a.activo"""


def comparar(destino: psycopg.Connection, tabla: str, tmp: str, pk: list[str], cols: list[str], ambito: str) -> dict:
    """Altas, cambios, bajas y reactivados de `tmp` (lo que hoy publica AutoCare) frente a `tabla` (la copia anterior)."""
    no_pk = [c for c in cols if c not in pk]
    llave = " and ".join(f"d.{k} = t.{k}" for k in pk)
    pk_json = ", ".join(f"'{k}', t.{k}" for k in pk)
    pk_json_d = ", ".join(f"'{k}', d.{k}" for k in pk)
    distinto = (f"({', '.join(f'd.{c}' for c in no_pk)}) is distinct from ({', '.join(f't.{c}' for c in no_pk)})" if no_pk else "false")
    antes_despues = ", ".join(f"'{c}', jsonb_build_array(d.{c}, t.{c})" for c in no_pk) if no_pk else "'_', null"

    def lista(sql: str) -> list:
        return [r[0] for r in destino.execute(sql)]
    altas = lista(f"select jsonb_build_object({pk_json}) from {tmp} t where not exists (select 1 from {tabla} d where {llave})")
    cambios = lista(f"""select jsonb_build_object({pk_json}) || jsonb_build_object('antes_despues', jsonb_build_object({antes_despues}))
                        from {tmp} t join {tabla} d on {llave} where {distinto}""")
    reactivados = lista(f"select jsonb_build_object({pk_json}) from {tmp} t join {tabla} d on {llave} where d.obsoleto_en is not null")
    bajas = lista(f"""select jsonb_build_object({pk_json_d}) from {tabla} d where d.obsoleto_en is null and ({ambito})
                      and not exists (select 1 from {tmp} t where {llave})""")
    vigentes = destino.execute(f"select count(*) from {tabla} d where d.obsoleto_en is null and ({ambito})").fetchone()[0]
    return {"altas": altas, "cambios": cambios, "bajas": bajas, "reactivados": reactivados, "vigentes": vigentes}


def impacto(conn: psycopg.Connection | None, consultas: list[tuple[str, str]], llaves: list[dict]) -> dict:
    if conn is None or not llaves:
        return {}
    salida = {}
    for descripcion, sql in consultas:
        n, ejemplos = conn.execute(sql, {"llaves": json.dumps(llaves)}).fetchone()
        if n:
            salida[descripcion] = {"usos": n, "ejemplos": ejemplos[:20]}
    return salida


def cargar(base: str, destino_dsn: str, origen_dsn: str, todo: bool = False, forzar: bool = False, nexo_dsn: str | None = None) -> None:
    with psycopg.connect(origen_dsn) as origen, psycopg.connect(destino_dsn) as destino:
        origen.read_only = True
        nexo = psycopg.connect(nexo_dsn) if nexo_dsn else None
        if nexo:
            nexo.read_only = True
        versiones = {r[0]: {"version": r[1], "publicacion": str(r[2])} for r in origen.execute(VERSIONES[3])}
        if base == "nexo":
            pts = destino.execute("select string_agg(distinct part_terminology_id_defecto::text, ',') from app.categoria "
                                  "where part_terminology_id_defecto is not null").fetchone()[0]
        else:
            pts = ",".join(str(p) for p in TIPOS_ALCANCE)
        resumen = []
        for tabla, pk, cols, consulta in TABLAS[base]:
            consulta = consulta or consulta_detectada(origen, tabla)
            filtrada = "{pts}" in consulta
            if filtrada:
                consulta = consulta.format(pts=pts) if not todo else consulta.replace("in ({pts})", "is not null")
            ambito = f"d.part_terminology_id in ({pts})" if filtrada and not todo else "true"
            tmp = "tmp_" + tabla.split(".")[1]
            destino.execute(f"create temp table {tmp} (like {tabla} including defaults) on commit drop")
            lista = ", ".join(cols)
            with origen.cursor().copy(f"copy ({consulta}) to stdout") as src, \
                 destino.cursor().copy(f"copy {tmp} ({lista}) from stdin") as dst:
                for bloque in src:
                    dst.write(bloque)
            if tabla == "ref.version":                                     # sin historial: es el número de versión
                destino.execute(f"insert into {tabla} ({lista}) select {lista} from {tmp} on conflict (base) do update set "
                                "version = excluded.version, publicacion = excluded.publicacion")
                continue

            c = comparar(destino, tabla, tmp, pk, cols, ambito)
            if c["vigentes"] and len(c["bajas"]) > max(10, c["vigentes"] * MAX_BAJAS) and not forzar:
                destino.rollback()
                sys.exit(f"[alto] {tabla}: AutoCare ya no traería {len(c['bajas'])} de {c['vigentes']} filas (más del "
                         f"{MAX_BAJAS:.0%}). No se tocó nada. Revisa el origen; si es correcto, repite con --forzar.")
            if c["bajas"]:                                                 # lo que AutoCare ya no publica: obsoleto, nunca borrado
                llave = " and ".join(f"d.{k} = t.{k}" for k in pk)
                destino.execute(f"update {tabla} d set obsoleto_en = now() where d.obsoleto_en is null and ({ambito}) "
                                f"and not exists (select 1 from {tmp} t where {llave})")
            no_pk = [col for col in cols if col not in pk]
            reactivar = f"{tabla}.obsoleto_en is not null"
            accion = (f"do update set {', '.join(f'{col} = excluded.{col}' for col in no_pk)}, obsoleto_en = null "
                      f"where ({', '.join(f'{tabla}.{col}' for col in no_pk)}) is distinct from ({', '.join(f'excluded.{col}' for col in no_pk)}) "
                      f"or {reactivar}" if no_pk else f"do update set obsoleto_en = null where {reactivar}")
            destino.execute(f"insert into {tabla} ({lista}) select {lista} from {tmp} on conflict ({', '.join(pk)}) {accion}")

            # Impacto: lo obsoleto o cambiado que ya está en uso (en esta base y, con --nexo, en las aplicaciones de Nexo)
            afectadas = [{k: x[k] for k in pk} for x in c["bajas"] + c["cambios"]]
            imp = impacto(destino, IMPACTO.get((base, tabla), []), afectadas)
            if nexo and tabla == "ref.base_vehicle":
                imp |= impacto(nexo, [("artículos de Nexo con ese vehículo", IMPACTO_NEXO_VEHICULOS)], afectadas)
            detalle = {k: c[k][:20] for k in ("altas", "cambios", "bajas", "reactivados") if c[k]}
            destino.execute(f"""insert into {HISTORIAL[base]} (versiones, tabla, altas, cambios, bajas, reactivados, detalle, impacto)
                                values (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (json.dumps(versiones), tabla, len(c["altas"]), len(c["cambios"]), len(c["bajas"]), len(c["reactivados"]),
                             json.dumps(detalle, default=str), json.dumps(imp, default=str)))
            total = destino.execute(f"select count(*) filter (where obsoleto_en is null), count(*) from {tabla}").fetchone()
            print(f"[ok] {tabla}: +{len(c['altas'])} altas, ~{len(c['cambios'])} cambios, -{len(c['bajas'])} obsoletas, "
                  f"{len(c['reactivados'])} reactivadas · {total[0]} vigentes de {total[1]}")
            for descripcion, v in imp.items():
                print(f"     ⚠ impacto: {v['usos']} {descripcion} (p. ej. {', '.join(str(e) for e in v['ejemplos'][:5])})")
            resumen.append(tabla)
        if base == "consolidacion" and not todo:
            depurar_fuera_de_alcance(destino, pts)
        destino.commit()
        if nexo:
            nexo.close()


def depurar_fuera_de_alcance(destino: psycopg.Connection, pts: str) -> None:
    """Copias anteriores sin filtro: borra lo de otros tipos de parte que ninguna parte del catálogo usa (nunca lo que está en uso)."""
    libres = f"part_terminology_id not in ({pts}) and part_terminology_id not in (select part_terminology_id from catalogo.parte)"
    n = sum(destino.execute(f"delete from {t} where {libres}").rowcount
            for t in ("ref.valor_permitido", "ref.atributo_permitido", "ref.part_terminology"))
    if n:
        print(f"[ok] depuradas {n} filas de PCdb/PAdb de tipos de parte fuera de alcance (no usadas)")


def main() -> None:
    load_dotenv(RAIZ / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("base", choices=list(TABLAS))
    p.add_argument("--destino", help="DSN destino (por defecto, CONSOLIDACION_*, MERCADO_EXTERNO_* o NEXO_* del .env)")
    p.add_argument("--origen", help="DSN de AutoCare (por defecto, AUTOCARE_* del .env; para pruebas)")
    p.add_argument("--todo", action="store_true", help="copiar PCdb/PAdb de todos los tipos de parte, no solo los nuestros")
    p.add_argument("--forzar", action="store_true", help=f"aplicar aunque una tabla quede con más del {MAX_BAJAS:.0%} obsoleto")
    p.add_argument("--nexo", help="DSN de Nexo (solo lectura) para medir el impacto en sus aplicaciones")
    a = p.parse_args()
    destino = a.destino or dsn({"consolidacion": "CONSOLIDACION", "mercado_externo": "MERCADO_EXTERNO", "nexo": "NEXO"}[a.base])
    cargar(a.base, destino, a.origen or dsn("AUTOCARE"), todo=a.todo, forzar=a.forzar, nexo_dsn=a.nexo)

if __name__ == "__main__":
    main()
