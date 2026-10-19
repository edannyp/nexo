"""Adaptador del catálogo maestro contra una Consolidación local con sus migraciones reales, la referencia mínima de db/pruebas y el
ejemplo de carga de db/consolidacion (Hyundai 335×608×16, Ford 770×588×36, Suzuki Grand Vitara con aplicaciones)."""

import os
import subprocess
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine

from nexo_api.adapters.consolidacion import Consolidacion, Medidas, medidas_de_texto, normalizar_numero

RAIZ = Path(__file__).resolve().parents[4]
HOST = os.getenv("PRUEBAS_PG_HOST", "postgres")
NOMBRE = "nexo_prueba_consolidacion"


@pytest.fixture(scope="module")
def maestro() -> Consolidacion:
    with psycopg.connect(f"host={HOST} dbname=postgres user=postgres password=postgres", autocommit=True) as c:
        c.execute(f"drop database if exists {NOMBRE} with (force)")
        c.execute(f"create database {NOMBRE}")
    dsn = f"host={HOST} dbname={NOMBRE} user=postgres password=postgres"
    subprocess.run(["uv", "run", "-q", str(RAIZ / "db" / "aplicar.py"), "consolidacion", "--dsn", dsn], check=True, capture_output=True)
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute((RAIZ / "db" / "pruebas" / "ref_minimo_consolidacion.sql").read_text())
        c.execute((RAIZ / "db" / "consolidacion" / "ejemplos" / "ejemplo_carga.sql").read_text())
    return Consolidacion(create_engine(f"postgresql+psycopg://postgres:postgres@{HOST}:5432/{NOMBRE}"))


def ids(maestro) -> dict[str, int]:
    return {r.descripcion.split()[1]: r.parte_id for r in maestro.buscar(2172, "radiador", 10)}


def test_textos():
    assert medidas_de_texto("400x518x26") == Medidas(Decimal(400), Decimal(518), Decimal(26))
    assert medidas_de_texto("37,5 × 60") == Medidas(Decimal("37.5"), Decimal(60), None)
    assert medidas_de_texto("16400-35090") is None
    assert normalizar_numero(" 568.770.38 ") == "56877038"


def test_candidatos_por_medidas_en_cualquier_orden(maestro):
    directo = maestro.candidatos(2172, Medidas(Decimal(330), Decimal(612)), 10, [], [])
    invertido = maestro.candidatos(2172, Medidas(Decimal(608), Decimal(335)), 10, [], [])
    assert [c.parte.descripcion for c in directo] == [c.parte.descripcion for c in invertido] == ["Radiador Hyundai panal 335x608x16"]
    assert directo[0].parte.medidas == Medidas(Decimal(335), Decimal(608), Decimal(16))
    assert maestro.candidatos(2172, Medidas(Decimal(330), Decimal(612)), 3, [], []) == []
    assert maestro.candidatos(6708, Medidas(Decimal(335), Decimal(608)), 10, [], []) == []      # otro tipo de parte


def test_candidatos_por_numero_y_por_vehiculo(maestro):
    por_numero = maestro.candidatos(2172, Medidas(), 10, ["25310 22050", "x"], [])
    assert len(por_numero) == 1 and por_numero[0].numeros_coinciden == ["OEM 25310-22050"]
    por_vehiculo = maestro.candidatos(2172, Medidas(), 10, [], [802006, 802007, 1])
    assert len(por_vehiculo) == 1 and por_vehiculo[0].vehiculos_comunes == 2 and "Suzuki" in por_vehiculo[0].parte.descripcion


def test_busqueda_manual(maestro):
    assert [p.descripcion for p in maestro.buscar(2172, "335x608x20", 5)] == ["Radiador Hyundai panal 335x608x16"]
    assert [p.descripcion for p in maestro.buscar(None, "2531022", 10)] == ["Radiador Hyundai panal 335x608x16"]
    assert [p.descripcion for p in maestro.buscar(2172, "ford panal", 10)] == ["Radiador Ford panal 770x588x36"]
    assert len(ids(maestro)) == 3


def test_detalle_y_resumenes(maestro):
    hyundai = ids(maestro)["Hyundai"]
    d = maestro.detalle(hyundai)
    assert [(n.tipo, n.numero) for n in d.numeros] == [("DPI", "1816"), ("OEM", "25310-22050"), ("OEM", "25310-22070")]
    assert {a.paid: a.valor_num for a in d.atributos} == {267: 335, 268: 16, 269: 608}
    assert [f.id_en_fuente for f in d.fuentes] == ["905096"] and d.aplicaciones == [] and d.imagenes == []
    suzuki = maestro.detalle(ids(maestro)["Suzuki"])
    assert len(suzuki.aplicaciones) == 11
    assert maestro.detalle(999999) is None and maestro.resumenes([]) == {}
    assert maestro.resumenes([hyundai])[hyundai].estado == "ACTIVA"
