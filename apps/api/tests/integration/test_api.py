"""API contra una base nexo desechable y migrada: salud y categorías del filtro global (con un usuario ya autenticado)."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import Usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app

from .apoyo import articulo, cargar


def cliente_para(url: str) -> TestClient:
    motor = create_engine(url)
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: Usuario(1, "prueba", "Prueba", None, frozenset(), frozenset(), False)
    return TestClient(app)


@pytest.fixture(scope="module")
def cliente(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188"), articulo("RLT00496", subcategoria_codigo="2502", subcategoria_nombre="FABRICADOS"),
                   articulo("INT00048", categoria_codigo="18", subcategoria_codigo="1801"),
                   articulo("RAD00001", descripcion="RADIADOR INACTIVO", congelado_sap="Y")])
    nombre = dict(p.split("=") for p in bd.split())["dbname"]
    host = dict(p.split("=") for p in bd.split())["host"]
    return cliente_para(f"postgresql+psycopg://postgres:postgres@{host}:5432/{nombre}")


def test_salud_lista_reporta_la_migracion(cliente):
    r = cliente.get("/api/v1/salud/lista")
    assert r.status_code == 200 and r.json() == {"estado": "ok", "migracion": "0012"}


def test_categorias_con_activos_por_linea(cliente):
    cats = {c["codigo"]: c for c in cliente.get("/api/v1/categorias").json()}
    assert len(cats) == 8
    assert cats["25"]["nombre"] == "RADIADORES" and cats["25"]["part_terminology_id"] == 2172
    assert cats["25"]["activos"] == {"IMPORTADO": 1, "FABRICADO": 1}      # el inactivo no cuenta
    assert cats["18"]["activos"] == {"IMPORTADO": 1, "FABRICADO": 0}


def test_salud_lista_sin_base_es_503():
    r = cliente_para("postgresql+psycopg://x:x@127.0.0.1:1/x?connect_timeout=1").get("/api/v1/salud/lista")
    assert r.status_code == 503 and r.headers["content-type"] == "application/problem+json"
    assert r.json()["title"] == "Base no disponible"
