"""Aplicaciones del artículo: sugerencia de SAP traducida al catálogo, agregar desde el selector (confirmadas), confirmar sugeridas
completas, quitar, y la misma regla de edición que la ficha (propuesta UX §6.4, decisión 4). El catálogo de vehículos es un doble."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.adapters.vehiculos import BaseVehicle, Marca, Modelo
from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app
from nexo_api.modules.vehiculos import obtener_vehiculos

from .apoyo import articulo, cargar, crear_usuario

URL = "/api/v1/articulos/RAD00500/aplicaciones"


class CatalogoFalso:
    """D-Max 2010–2012 con un submodelo y un motor; los ids son los de un AutoCare inventado."""
    def marcas(self, desde, hasta):
        return [Marca(21, "Isuzu"), Marca(76, "Toyota")]

    def modelos(self, marca_id, desde, hasta):
        return [Modelo(900, "Rodeo"), Modelo(901, "D-Max"), Modelo(902, "Trooper")] if marca_id == 21 else []

    def base_vehicles(self, ids):
        return {i: BaseVehicle(2000 + i % 100, "Isuzu", "D-Max") for i in ids}

    def submodelos(self, ids):
        return {i: "LS" for i in ids}

    def motores(self, ids):
        return {i: "3.0L L4 4JJ1 · Diésel" for i in ids}


CATALOGO = CatalogoFalso()


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00500", marca_vehiculo_codigo="00049", modelo_vehiculo_codigo=6, modelo_vehiculo="DMAX",
                            anio_desde=2010, anio_hasta=2012)])
        ids = {u: crear_usuario(c, u, "OPERADOR") for u in ("op1", "op2")}
        a = c.execute("select id from app.articulo where item_code = 'RAD00500'").fetchone()[0]
        # Heredadas de un equivalente: una completa y una sin motor
        c.execute("""insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, sub_model_id, engine_config_id, origen)
                     values (%s, 13, 5, 7, 'HEREDADO_EQUIVALENTE'), (%s, 14, 5, null, 'HEREDADO_EQUIVALENTE')""", (a, a))
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    return motor, ids, bd


def como(entorno, usuario: str, catalogo=CATALOGO) -> TestClient:
    motor, ids, _ = entorno
    with motor.connect() as c:
        u = cargar_usuario(c, ids[usuario])
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: u
    app.dependency_overrides[obtener_vehiculos] = lambda: catalogo
    return TestClient(app)


def items(r: dict) -> dict:
    return {(i["base_vehicle_id"], i["engine_config_id"]): i for g in r["grupos"] for i in g["items"]}


def test_01_sugerencia_de_sap_y_heredadas(entorno):
    r = como(entorno, "op1").get(URL).json()
    assert not r["editable"] and r["catalogo_disponible"]
    s = r["sugerencia_sap"]
    assert (s["marca"], s["modelo"], s["desde"], s["hasta"]) == ("ISUZU", "DMAX", 2010, 2012)
    assert s["marca_catalogo"] == {"id": 21, "nombre": "Isuzu"} and s["modelos_candidatos"][0]["nombre"] == "D-Max"
    assert [(g["titulo"], g["detalle"], g["anios"], g["sugeridos"]) for g in r["grupos"]] == [
        ("Isuzu D-Max", "LS · 3.0L L4 4JJ1 · Diésel", "2013", 1), ("Isuzu D-Max", "LS · Sin motor", "2014", 1)]
    assert not items(r)[(14, None)]["completa"]


def test_02_sin_catalogo_lista_igual(entorno):
    r = como(entorno, "op1", catalogo=None).get(URL).json()
    assert not r["catalogo_disponible"] and r["sugerencia_sap"]["marca_catalogo"] is None
    assert {g["titulo"] for g in r["grupos"]} == {"Vehículo 13", "Vehículo 14"}
    assert como(entorno, "op1", catalogo=None).get("/api/v1/vehiculos/marcas?desde=2010&hasta=2012").status_code == 503


def test_03_solo_edita_quien_lo_tiene_reservado(entorno):
    op1, op2 = como(entorno, "op1"), como(entorno, "op2")
    assert op1.post("/api/v1/articulos/RAD00500/asignacion").status_code == 200
    v = op1.get(URL).json()["version"]
    r = op2.post(URL, json={"version": v, "items": [{"base_vehicle_id": 10, "sub_model_id": 5, "engine_config_id": 7}]})
    assert r.status_code == 409 and r.json()["detail"] == "op1 lo está trabajando."


def test_04_agregar_queda_confirmada_y_confirma_la_heredada_igual(entorno):
    op1 = como(entorno, "op1")
    v = op1.get(URL).json()["version"]
    nuevas = [{"base_vehicle_id": b, "sub_model_id": 5, "engine_config_id": 7} for b in (10, 11, 12, 13)]
    r = op1.post(URL, json={"version": v, "items": nuevas}).json()
    assert r["version"] == v + 1
    g = r["grupos"][0]
    assert (g["detalle"], g["anios"], g["confirmados"], g["sugeridos"]) == ("LS · 3.0L L4 4JJ1 · Diésel", "2010–2013", 4, 0)
    assert items(r)[(13, 7)]["origen"] == "HEREDADO_EQUIVALENTE"            # ya estaba: se confirma, no se duplica
    assert {i["origen"] for k, i in items(r).items() if k[0] in (10, 11, 12)} == {"MANUAL"}


def test_05_no_confirma_incompletas_ni_con_version_vieja(entorno):
    op1 = como(entorno, "op1")
    r = op1.get(URL).json()
    incompleta = items(r)[(14, None)]["id"]
    vieja = op1.post(f"{URL}/confirmar", json={"version": r["version"] - 1, "ids": [incompleta]})
    assert vieja.status_code == 409 and vieja.json()["title"] == "Otro usuario cambió este artículo"
    mal = op1.post(f"{URL}/confirmar", json={"version": r["version"], "ids": [incompleta]})
    assert mal.status_code == 422 and mal.json()["title"] == "Completa submodelo y motor antes de confirmar"
    assert op1.get(URL).json()["version"] == r["version"]


def test_06_quitar(entorno):
    op1 = como(entorno, "op1")
    r = op1.get(URL).json()
    quitar = [items(r)[(14, None)]["id"], items(r)[(12, 7)]["id"]]
    q = op1.post(f"{URL}/quitar", json={"version": r["version"], "ids": quitar}).json()
    assert q["grupos"][0]["anios"] == "2010–2011, 2013" and len(q["grupos"]) == 1


def test_07_cambios_auditados_con_el_usuario(entorno):
    _, ids, bd = entorno
    with psycopg.connect(bd) as c:
        actores = {r[0] for r in c.execute("select actor from audit.auditoria_evento where entidad = 'app.articulo_aplicacion'")}
    assert str(ids["op1"]) in actores
