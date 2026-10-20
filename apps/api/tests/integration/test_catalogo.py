"""Catálogo maestro, vista inversa (propuesta UX §6.8): partes con cuántos artículos las usan, filtro "sin artículo" y, desde una parte,
los artículos de Nexo que podrían ser ella. El catálogo maestro es un doble."""

from decimal import Decimal as D

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.adapters.consolidacion import AplicacionParte, DetalleParte, Medidas, NumeroParte, ResumenParte
from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app
from nexo_api.modules.emparejamiento import obtener_catalogo_maestro

from .apoyo import articulo, cargar, crear_usuario

FILTRO = "cat=25&linea=IMPORTADO"


def parte(pid, alto, largo, ancho, numeros=(), bvs=()):
    r = ResumenParte(pid, 2172, "Radiator", f"Radiador {pid}", " ".join(numeros) or None, Medidas(D(alto), D(largo), D(ancho)), len(bvs),
                     1, None)
    return DetalleParte(r, [NumeroParte("OEM", None, n) for n in numeros], [], [AplicacionParte(b, None, None, None) for b in bvs], [], [])


PARTES = {7001: parte(7001, 400, 518, 26), 7002: parte(7002, 520, 398, 26, ["JJ-945"]), 7003: parte(7003, 300, 300, 20, bvs=[10, 11])}


class MaestroFalso:
    def __init__(self):
        self.excluidas = None

    def listar(self, pt, q, tolerancia, excluir, limite, desde):
        self.excluidas = sorted(excluir)
        lista = [d.parte for i, d in PARTES.items() if i not in set(excluir) and pt == 2172]
        return len(lista), lista[desde:desde + limite]

    def detalle(self, parte_id):
        return PARTES.get(parte_id)


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188", panal_alto=400, panal_alto_unidad=1, panal_largo=518, panal_largo_unidad=1, panal_ancho=26,
                            panal_ancho_unidad=1),
                   articulo("RAD00156", numero_parte_proveedor="JJ945"),
                   articulo("RAD00999", panal_alto=100, panal_alto_unidad=1, panal_largo=100, panal_largo_unidad=1)])
        uid = crear_usuario(c, "op1", "OPERADOR")
        a188, a999 = (c.execute("select id from app.articulo where item_code = %s", (x,)).fetchone()[0] for x in ("RAD00188", "RAD00999"))
        c.execute("insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por) values (%s, 7001, true, 'MANUAL', %s)",
                  (a188, uid))
        c.execute("insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, origen) values (%s, 11, 'MANUAL')", (a999,))
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    return motor, uid


def cliente(entorno, maestro) -> TestClient:
    motor, uid = entorno
    with motor.connect() as c:
        u = cargar_usuario(c, uid)
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: u
    app.dependency_overrides[obtener_catalogo_maestro] = lambda: maestro
    return TestClient(app)


def test_partes_con_cuantos_articulos_las_usan(entorno):
    m = MaestroFalso()
    r = cliente(entorno, m).get(f"/api/v1/catalogo?{FILTRO}").json()
    assert (r["disponible"], r["part_terminology_id"], r["total"]) == (True, 2172, 3)
    assert {p["parte"]["parte_id"]: p["articulos"] for p in r["partes"]} == {7001: 1, 7002: 0, 7003: 0}
    sin = cliente(entorno, m).get(f"/api/v1/catalogo?{FILTRO}&sin_articulo=true").json()
    assert m.excluidas == [7001] and [p["parte"]["parte_id"] for p in sin["partes"]] == [7002, 7003]


def test_sin_catalogo_maestro(entorno):
    r = cliente(entorno, None).get(f"/api/v1/catalogo?{FILTRO}").json()
    assert (r["disponible"], r["partes"]) == (False, [])
    assert cliente(entorno, None).get(f"/api/v1/catalogo/7001/articulos?{FILTRO}").status_code == 503


def test_articulos_que_podrian_ser_la_parte(entorno):
    m = MaestroFalso()
    v = cliente(entorno, m).get(f"/api/v1/catalogo/7001/articulos?{FILTRO}").json()
    assert [(a["item_code"], a["es_principal"]) for a in v["vinculados"]] == [("RAD00188", True)] and v["candidatos"] == []
    inv = cliente(entorno, m).get(f"/api/v1/catalogo/7002/articulos?{FILTRO}").json()
    assert [(a["item_code"], a["puntaje"]) for a in inv["candidatos"]] == [("RAD00188", 50), ("RAD00156", 35)]
    assert inv["candidatos"][0]["razones"][0] == "Alto y largo invertidos (520×398)"
    assert inv["candidatos"][1]["razones"] == ["Número JJ945 coincide"]
    por_vehiculo = cliente(entorno, m).get(f"/api/v1/catalogo/7003/articulos?{FILTRO}").json()
    assert [(a["item_code"], a["razones"]) for a in por_vehiculo["candidatos"]] == [("RAD00999", ["1 vehículo en común"])]
    assert cliente(entorno, m).get(f"/api/v1/catalogo/9999/articulos?{FILTRO}").status_code == 404
