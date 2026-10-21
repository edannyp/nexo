"""Copia de AutoCare versionada hacia Nexo (db/ref/cargar_ref.py, ADR 0024) con un AutoCare MÍNIMO local: lo que AutoCare quita
queda obsoleto y el historial dice qué artículos de Nexo lo usan; con --nexo, la carga de Consolidación mide el impacto en las
aplicaciones de Nexo."""

import contextlib
import importlib.util
import io
import os
import subprocess
from pathlib import Path

import psycopg
import pytest

from .apoyo import articulo, cargar

RAIZ = Path(__file__).resolve().parents[4]
HOST = os.getenv("PRUEBAS_PG_HOST", "postgres")
spec = importlib.util.spec_from_file_location("cargar_ref", RAIZ / "db" / "ref" / "cargar_ref.py")
cargar_ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cargar_ref)


def base_nueva(nombre: str) -> str:
    with psycopg.connect(f"host={HOST} dbname=postgres user=postgres password=postgres", autocommit=True) as c:
        c.execute(f"drop database if exists {nombre} with (force)")
        c.execute(f"create database {nombre}")
    return f"host={HOST} dbname={nombre} user=postgres password=postgres"


def correr(*args, **kw) -> str:
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        cargar_ref.cargar(*args, **kw)
    return salida.getvalue()


@pytest.fixture(scope="module")
def origen():
    dsn = base_nueva("nexo_prueba_autocare")
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute((RAIZ / "db" / "pruebas" / "autocare_minimo.sql").read_text())
    return dsn


def test_carga_a_nexo_marca_obsoleto_y_dice_que_articulos_lo_usan(bd, origen):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00701", tipo_flujo="Down Flow")])
        a = c.execute("select id from app.articulo where item_code = 'RAD00701'").fetchone()[0]
        c.execute("select app.fn_precargar_atributos_sap(%s)", (a,))                         # queda con 7448 = 444 (Down Flow)
    correr("nexo", bd, origen, forzar=True)          # la primera vez alinea el catálogo de la migración con este AutoCare mínimo
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute("delete from padb_config.valid_value_assignment where valid_value_id = 444")
    salida = correr("nexo", bd, origen)
    with psycopg.connect(bd) as c:
        obsoleto = c.execute("""select obsoleto_en is not null from meta.atributo_valor_permitido
                                where paid = 7448 and valid_value_id = 444""").fetchone()[0]
        bajas, impacto = c.execute("""select bajas, impacto from meta.historial_referencia where tabla = 'meta.atributo_valor_permitido'
                                      order by id desc limit 1""").fetchone()
    assert obsoleto and bajas == 1
    assert impacto["artículos de Nexo con ese valor"]["ejemplos"] == ["RAD00701"]
    assert "⚠ impacto: 1 artículos de Nexo con ese valor" in salida


def test_carga_de_consolidacion_mide_el_impacto_en_las_aplicaciones_de_nexo(bd, origen):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00702")])
        c.execute("""insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, origen)
                     select id, 802007, 'MANUAL' from app.articulo where item_code = 'RAD00702'""")
    cons = base_nueva("nexo_prueba_consolidacion_ref")
    subprocess.run(["uv", "run", "-q", str(RAIZ / "db" / "aplicar.py"), "consolidacion", "--dsn", cons], check=True, capture_output=True)
    correr("consolidacion", cons, origen)
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute("delete from vcdb_base.base_vehicle where base_vehicle_id = 802007")
    correr("consolidacion", cons, origen, nexo_dsn=bd)
    with psycopg.connect(cons) as c:
        impacto = c.execute("""select impacto from ref.historial_carga where tabla = 'ref.base_vehicle' order by id desc limit 1""").fetchone()[0]
    assert impacto["artículos de Nexo con ese vehículo"]["ejemplos"] == ["RAD00702"]
