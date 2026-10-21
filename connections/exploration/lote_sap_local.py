"""Carga de REFERENCIA (no es el ETL): lee SAP con SELECT y llena el staging de una nexo LOCAL, luego fn_procesar_staging.
Sigue el contrato del ETL de entrada (architecture/datos/contratos.md): foto completa de las 8 categorías, más los artículos que ya
se habían enviado aunque hoy estén en otra categoría. Sirve para verificar el ETL real (exploration/verificar_etl_sap.py).

Uso (desde connections/, con la base ya migrada en el Postgres local):
    PYTHONPATH=. uv run python -m exploration.lote_sap_local                                  # base nexo_real
    PYTHONPATH=. uv run python -m exploration.lote_sap_local --destino "host=postgres dbname=nexo_ref user=postgres password=postgres"
"""
import argparse
import datetime
import decimal
import json

import psycopg
from hdbcli import dbapi

from common.config import hana, hana_schema

MAPEO = {  # campo SAP → columna staging (mapeo-fuentes.md)
 "ItemCode": "item_code", "ItemName": "descripcion", "U_Categoria": "categoria_codigo", "U_SubCat": "subcategoria_codigo",
 "U_SubSubCat": "material_codigo", "U_SSCatName": "material_descripcion", "SuppCatNum": "numero_parte_proveedor",
 "U_CodAnterior": "codigo_anterior", "U_Marca": "marca_vehiculo_codigo", "U_Linea": "modelo_vehiculo_codigo",
 "U_LineName": "modelo_vehiculo", "U_anio1": "anio_desde", "U_anio2": "anio_hasta", "U_Motor": "motor", "U_Cyl": "cilindrada",
 "U_transmision": "transmision", "SHeight1": "panal_alto", "SHght1Unit": "panal_alto_unidad", "SLength1": "panal_largo",
 "SLen1Unit": "panal_largo_unidad", "SWidth1": "panal_ancho", "SWdth1Unit": "panal_ancho_unidad", "U_Tamanio": "tamano_panal",
 "U_Filas": "filas_panal", "U_TipoPanal": "tipo_panal", "U_CoreMaterial": "material_panal", "U_TankMaterial": "material_tanque",
 "U_TankDimension": "dimension_tanque", "U_FlowType": "tipo_flujo", "U_InletDiameter": "entrada_diametro",
 "U_InletLocation": "entrada_ubicacion", "U_OutletDiameter": "salida_diametro", "U_OutletLocation": "salida_ubicacion",
 "U_CapIncluded": "incluye_tapon", "U_ThermostatIncluded": "incluye_termostato",
 "U_TransmissionOilCoolerIncluded": "incluye_enfriador_transmision", "U_Material_PRI": "material_principal",
 "U_Material_SEC": "material_secundario", "U_Material_Other": "material_otro", "U_Material_Comp": "composicion_material",
 "U_ID_Aces": "autocare_id_sap", "frozenFor": "congelado_sap",
}
CATS = ("25", "07", "18", "11", "29", "09", "44", "46")

def j(v):
    return float(v) if isinstance(v, decimal.Decimal) else v.isoformat() if isinstance(v, (datetime.date, datetime.datetime)) else v

p = argparse.ArgumentParser()
p.add_argument("--destino", default="host=postgres user=postgres password=postgres dbname=nexo_real",
               help="DSN de una base nexo LOCAL ya migrada (nunca un servidor)")
destino_dsn = p.parse_args().destino
if not any(f"host={h}" in destino_dsn for h in ("postgres", "localhost", "127.0.0.1")):
    raise SystemExit("La carga de referencia solo se hace en una base local.")

s = hana_schema()
h = dbapi.connect(**hana()); cur = h.cursor()
cur.execute(f'select "Code","Name" from "{s}"."@IGT_MARCAS"'); marcas = cur.fetchall()
cur.execute(f'select "Code","LineId","U_Linea","U_Tamanio" from "{s}"."@IGT_LINEA"'); modelos = cur.fetchall()
cols = ", ".join(f'i."{k}"' for k in MAPEO)
cur.execute(f'select {cols}, c2."Name" from "{s}"."OITM" i left join "{s}"."@IGT_CAT2" c2 on c2."Code" = i."U_SubCat" '
            f'where i."U_Categoria" in ({",".join("?" * len(CATS))})', CATS)
filas = cur.fetchall()
# Foto completa: también los que ya se habían enviado y hoy están en otra categoría (así Nexo sabe que salieron del alcance)
with psycopg.connect(destino_dsn) as c:
    enviados = {r[0] for r in c.execute("select item_code from staging.articulo_sap")}
faltan = sorted(enviados - {f[0] for f in filas})
for i in range(0, len(faltan), 500):
    lote_codigos = faltan[i:i + 500]
    cur.execute(f'select {cols}, c2."Name" from "{s}"."OITM" i left join "{s}"."@IGT_CAT2" c2 on c2."Code" = i."U_SubCat" '
                f'where i."ItemCode" in ({",".join("?" * len(lote_codigos))})', lote_codigos)
    filas += cur.fetchall()
h.close()
print(f"SAP: {len(marcas)} marcas, {len(modelos)} modelos, {len(filas)} artículos (8 categorías + {len(faltan)} enviados antes)")

destino = list(MAPEO.values()) + ["subcategoria_nombre", "datos_sap", "extraido_en", "lote_id"]
with psycopg.connect(destino_dsn, autocommit=True) as c:
    lote = c.execute("insert into staging.lote (completo) values (true) returning lote_id").fetchone()[0]
    with c.transaction():
        c.cursor().executemany("insert into staging.sap_marca values (%s, %s, %s) on conflict (marca_codigo) do update "
                               "set nombre = excluded.nombre, lote_id = excluded.lote_id", [(*m, lote) for m in marcas])
        c.cursor().executemany("insert into staging.sap_modelo values (%s, %s, %s, %s, %s) on conflict (marca_codigo, modelo_codigo) "
                               "do update set nombre = excluded.nombre, tamano = excluded.tamano, lote_id = excluded.lote_id",
                               [(*m, lote) for m in modelos])
        ahora = datetime.datetime.now(datetime.UTC)
        set_ = ", ".join(f"{k} = excluded.{k}" for k in destino if k != "item_code")
        c.cursor().executemany(f"insert into staging.articulo_sap ({', '.join(destino)}) values ({', '.join(['%s'] * len(destino))}) "
                               f"on conflict (item_code) do update set {set_}",
                               [(*[None if v == "" else v for v in f[:-1]], f[-1], json.dumps({k: j(v) for k, v in zip(MAPEO, f)}), ahora, lote)
                                for f in filas])
    print("fn_procesar_staging:", c.execute("select app.fn_procesar_staging(%s)", (lote,)).fetchone()[0])
