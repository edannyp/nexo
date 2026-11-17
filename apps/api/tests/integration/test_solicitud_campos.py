"""Solicitud de campos (ADR 0030): quien trabaja artículos propone un campo que falta; queda PROPUESTO en la ficha de todo el tipo de
parte (se captura, pero no es oficial ni puede ser obligatorio) hasta que quien tiene CONFIGURAR_FICHA lo aprueba o lo rechaza con
motivo (sale de la ficha y lo capturado se conserva)."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app

from .apoyo import articulo, cargar, crear_usuario

CFG = "/api/v1/configuracion/ficha/2172"
ART = "/api/v1/articulos"
ALETA = {"nombre": "Tipo de aleta", "tipo": "LISTA", "opciones": ["Recta", "Ondulada"], "grupo": "CONSTRUCCION",
         "motivo": "Los clientes preguntan por la aleta ondulada"}


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188"), articulo("RAD00189")])
        ids = {u: crear_usuario(c, u, r) for u, r in (("op1", "OPERADOR"), ("sup1", "SUPERVISOR"), ("fotos", "FOTOS"),
                                                       ("cfg", "FOTOS"))}
        c.execute("insert into app.usuario_permiso values (%s, 'CONFIGURAR_FICHA')", (ids["cfg"],))
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


def en_ficha(cli, item: str) -> dict:
    return {a["etiqueta"]: a for a in cli.get(f"{ART}/{item}/ficha").json()["atributos"]}


def config(entorno) -> dict:
    return {a["etiqueta"] or a["nombre"]: a for a in como(entorno, "cfg").get(CFG).json()["atributos"]}


def test_01_quien_trabaja_articulos_solicita_un_campo(entorno):
    fotos = como(entorno, "fotos")
    assert not fotos.get(f"{ART}/RAD00188/ficha").json()["puede_solicitar"]
    assert fotos.post(f"{ART}/RAD00188/ficha/campos", json=ALETA).status_code == 403
    op1 = como(entorno, "op1")
    assert op1.get(f"{ART}/RAD00188/ficha").json()["puede_solicitar"]
    assert op1.post(f"{ART}/RAD00188/ficha/campos", json={**ALETA, "motivo": ""}).status_code == 422      # el motivo es obligatorio
    r = op1.post(f"{ART}/RAD00188/ficha/campos", json={**ALETA, "obligatorio": True})
    assert r.status_code == 201
    aleta = {a["etiqueta"]: a for a in r.json()["atributos"]}["Tipo de aleta"]
    assert (aleta["estado"], aleta["solicitado_por"], aleta["propio"], aleta["obligatorio"]) == ("PROPUESTO", "op1", True, False)
    assert op1.post(f"{ART}/RAD00188/ficha/campos", json=ALETA).status_code == 409                       # ya existe


def test_02_todos_lo_ven_y_lo_capturan_sin_que_sea_requisito(entorno):
    sup1 = como(entorno, "sup1")
    aleta = en_ficha(sup1, "RAD00189")["Tipo de aleta"]                               # otro artículo del mismo tipo de parte
    assert aleta["estado"] == "PROPUESTO"
    assert sup1.post(f"{ART}/RAD00189/asignacion").status_code == 200
    v = sup1.get(f"{ART}/RAD00189/ficha").json()["version"]
    ondulada = aleta["opciones"][1]["valid_value_id"]
    r = sup1.put(f"{ART}/RAD00189/ficha", json={"version": v, "cambios": [{"paid": aleta["paid"], "valid_value_id": ondulada}]})
    assert r.status_code == 200
    assert not any(x["codigo"] == "ATRIBUTO:Tipo de aleta" for x in sup1.get(f"{ART}/RAD00189").json()["requisitos"])


def test_03_la_configuracion_ve_la_solicitud(entorno):
    panorama = como(entorno, "op1").get("/api/v1/panorama?cat=25&linea=IMPORTADO").json()
    assert panorama["atencion"]["campos_propuestos"] == 1                                # el Panorama la cuenta
    a = config(entorno)["Tipo de aleta"]
    assert (a["estado"], a["solicitado_por"], a["motivo_solicitud"], a["en_uso"]) == (
        "PROPUESTO", "op1", "Los clientes preguntan por la aleta ondulada", 1)
    assert a["solicitado_en"] is not None and a["revisado_por"] is None
    r = como(entorno, "cfg").patch(f"{CFG}/{a['paid']}", json={"obligatorio": True})
    assert r.status_code == 422 and r.json()["title"] == "Un campo propuesto no puede ser obligatorio"
    assert como(entorno, "op1").post(f"{CFG}/{a['paid']}/aprobar").status_code == 403                    # sin el permiso


def test_04_rechazar_lo_saca_de_la_ficha_y_conserva_lo_capturado(entorno):
    _, _, bd = entorno
    cfg, a = como(entorno, "cfg"), config(entorno)["Tipo de aleta"]
    assert cfg.post(f"{CFG}/{a['paid']}/rechazar", json={"motivo": "x"}).status_code == 422               # motivo muy corto
    r = cfg.post(f"{CFG}/{a['paid']}/rechazar", json={"motivo": "Ya existe como Core Type"}).json()
    assert (r["estado"], r["habilitado"], r["revisado_por"], r["motivo_rechazo"]) == ("RECHAZADO", False, "cfg", "Ya existe como Core Type")
    assert "Tipo de aleta" not in en_ficha(como(entorno, "op1"), "RAD00189")
    with psycopg.connect(bd) as c:
        assert c.execute("select count(*) from app.articulo_atributo where paid = %s", (a["paid"],)).fetchone()[0] == 1
    otra = como(entorno, "op1").post(f"{ART}/RAD00188/ficha/campos", json=ALETA)
    assert otra.status_code == 409 and otra.json()["detail"] == "Motivo: Ya existe como Core Type"
    assert cfg.patch(f"{CFG}/{a['paid']}", json={"habilitado": True}).status_code == 422
    assert cfg.post(f"{CFG}/{a['paid']}/rechazar", json={"motivo": "Otra vez"}).status_code == 409


def test_05_aprobar_lo_vuelve_oficial_con_lo_capturado(entorno):
    cfg, a = como(entorno, "cfg"), config(entorno)["Tipo de aleta"]
    r = cfg.post(f"{CFG}/{a['paid']}/aprobar").json()                                        # reconsiderar un rechazado
    assert (r["estado"], r["habilitado"], r["motivo_rechazo"], r["revisado_por"]) == ("OFICIAL", True, None, "cfg")
    aleta = en_ficha(como(entorno, "op1"), "RAD00189")["Tipo de aleta"]
    assert aleta["estado"] == "OFICIAL" and aleta["valor"]["valid_value_id"] == a["opciones"][1]["valid_value_id"]
    assert cfg.patch(f"{CFG}/{a['paid']}", json={"obligatorio": True}).json()["obligatorio"]              # ya puede serlo
    assert cfg.post(f"{CFG}/{a['paid']}/aprobar").status_code == 409
    assert cfg.post(f"{CFG}/{a['paid']}/rechazar", json={"motivo": "Ya no"}).status_code == 409


def test_06_lo_que_crea_la_configuracion_es_oficial_y_autocare_tambien(entorno):
    cfg = como(entorno, "cfg")
    r = cfg.post(f"{CFG}/propios", json={"nombre": "Nota técnica", "tipo": "TEXTO"}).json()
    assert r["estado"] == "OFICIAL" and r["solicitado_por"] is None
    assert config(entorno)["Alto"]["estado"] == "OFICIAL"
    assert cfg.post(f"{CFG}/267/rechazar", json={"motivo": "No aplica"}).status_code == 409
