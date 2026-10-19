"""Ficha de atributos: sugerencias de SAP persistidas, guardado con botón (todo junto y confirmado), reglas de edición,
validación PIES y traducciones (propuesta UX §6.4, decisiones 1 y 5)."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app

from .apoyo import articulo, cargar, crear_usuario

URL = "/api/v1/articulos/RAD00188/ficha"


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188", panal_alto=40, panal_alto_unidad=2, panal_largo=518, panal_largo_unidad=1, filas_panal=3,
                            tipo_panal="C", material_panal="Aluminum", tipo_flujo="Down Flow", dimension_tanque="545*54.5")])
        ids = {u: crear_usuario(c, u, "OPERADOR") for u in ("op1", "op2")}
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    return motor, ids, bd


def como(entorno, usuario: str) -> TestClient:
    motor, ids, _ = entorno
    with motor.connect() as c:
        u = cargar_usuario(c, ids[usuario])
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: u
    return TestClient(app)


def por_etiqueta(ficha: dict) -> dict:
    return {a["etiqueta"]: a for a in ficha["atributos"]}


def test_01_sugerencias_de_sap_y_opciones_traducidas(entorno):
    _, _, bd = entorno
    f = como(entorno, "op1").get(URL).json()
    assert not f["editable"] and f["razon_no_editable"] == "Toma el artículo para editarlo."
    a = por_etiqueta(f)
    assert a["Alto"]["valor_sap"] == "400" and a["Alto"]["valor"]["valor_num"] == "400.00" and a["Alto"]["origen"] == "SAP"
    assert a["Alto"]["tipo"] == "numero" and a["Alto"]["requiere_uom"] and not a["Alto"]["confirmado"]
    flujo = a["Tipo flujo"]
    assert flujo["tipo"] == "lista" and flujo["valor"]["valid_value_id"] == 444
    assert {o["valor"]: o["valor_es"] for o in flujo["opciones"]} == {"Cross Flow": "Horizontal (flujo cruzado)",
                                                                     "Down Flow": "Vertical (flujo descendente)"}
    assert a["Tipo de panal"]["tipo"] == "texto" and a["Tipo de panal"]["sugerencias"] == ["C"]
    assert (a["Largo tanque"]["valor"]["valor_num"], a["Ancho tanque"]["valor"]["valor_num"]) == ("545", "54.5")
    with psycopg.connect(bd) as c:                       # las sugerencias quedan guardadas (no solo en la respuesta)
        assert c.execute("select count(*) from app.articulo_atributo where origen = 'SAP' and confirmado_por is null").fetchone()[0] == 8  # el ancho no viene de SAP


def test_02_solo_edita_quien_lo_tiene_reservado(entorno):
    op1, op2 = como(entorno, "op1"), como(entorno, "op2")
    assert op1.post("/api/v1/articulos/RAD00188/asignacion").status_code == 200
    assert op1.get(URL).json()["editable"]
    f2 = op2.get(URL).json()
    assert not f2["editable"] and f2["razon_no_editable"] == "op1 lo está trabajando."
    r = op2.put(URL, json={"version": f2["version"], "cambios": []})
    assert r.status_code == 409 and r.json()["detail"] == "op1 lo está trabajando."


def test_03_aceptar_sugerido_conserva_el_origen_y_guardar_confirma(entorno):
    op1 = como(entorno, "op1")
    f = op1.get(URL).json()
    alto = por_etiqueta(f)["Alto"]
    cambios = [
        {"paid": alto["paid"], **{k: v for k, v in alto["valor"].items() if v is not None}},     # aceptar lo sugerido
        {"paid": por_etiqueta(f)["Material tanque"]["paid"], "valid_value_id": 890},            # capturar (Plastic)
        {"paid": por_etiqueta(f)["Filas"]["paid"], "valor_num": 2},                             # corregir lo de SAP
    ]
    g = op1.put(URL, json={"version": f["version"], "cambios": cambios}).json()
    a = por_etiqueta(g)
    assert g["version"] == f["version"] + 1
    assert (a["Alto"]["origen"], a["Alto"]["confirmado"], a["Alto"]["confirmado_por"]) == ("SAP", True, "op1")
    assert (a["Material tanque"]["origen"], a["Material tanque"]["confirmado"]) == ("MANUAL", True)
    assert (a["Filas"]["origen"], a["Filas"]["valor"]["valor_num"]) == ("MANUAL", "2")
    assert not a["Largo"]["confirmado"]                                        # lo que no se tocó sigue sugerido
    requisitos = [r["etiqueta"] for r in op1.get("/api/v1/articulos/RAD00188").json()["requisitos"]]
    assert "Alto" not in requisitos and "Material tanque" not in requisitos and "Largo" in requisitos


def test_04_quitar_un_valor(entorno):
    op1 = como(entorno, "op1")
    f = op1.get(URL).json()
    g = op1.put(URL, json={"version": f["version"], "quitar": [por_etiqueta(f)["Material tanque"]["paid"]]}).json()
    assert por_etiqueta(g)["Material tanque"]["valor"] is None


def test_05_validaciones(entorno):
    op1 = como(entorno, "op1")
    f = op1.get(URL).json()
    a, v = por_etiqueta(f), f["version"]
    vieja = op1.put(URL, json={"version": v - 1, "cambios": []})
    assert vieja.status_code == 409 and vieja.json()["title"] == "Otro usuario cambió este artículo"
    fuera = op1.put(URL, json={"version": v, "cambios": [{"paid": a["Material panal"]["paid"], "valid_value_id": 999}]})
    assert fuera.status_code == 422 and fuera.json()["title"] == "Ese valor no está en la lista de PIES"
    sin_uom = op1.put(URL, json={"version": v, "cambios": [{"paid": a["Alto"]["paid"], "valor_num": 400}]})
    assert sin_uom.status_code == 422 and sin_uom.json()["title"] == "Falta la unidad de la medida"
    dos = op1.put(URL, json={"version": v, "cambios": [{"paid": a["Alto"]["paid"], "valor_num": 1, "valor_texto": "x"}]})
    assert dos.status_code == 422
    no_habilitado = op1.put(URL, json={"version": v, "cambios": [{"paid": 3683, "valor_texto": "Yes"}]})
    assert no_habilitado.status_code == 422 and no_habilitado.json()["title"] == "Ese atributo no se usa en este tipo de parte"
    assert op1.get(URL).json()["version"] == v                                # nada se guardó a medias


def test_06_cambios_auditados_con_el_usuario(entorno):
    motor, ids, bd = entorno
    with psycopg.connect(bd) as c:
        actores = {r[0] for r in c.execute("select actor from audit.auditoria_evento where entidad = 'app.articulo_atributo'")}
    assert str(ids["op1"]) in actores and "PROCESO:PRECARGA_SAP" in actores
