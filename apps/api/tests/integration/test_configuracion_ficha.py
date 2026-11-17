"""Configuración de la ficha desde la consola (ADR 0029): solo con el permiso CONFIGURAR_FICHA; habilitar, obligatorio, etiqueta y
precarga desde SAP; campos propios (número, lista, texto, sí/no) que la ficha del artículo usa y valida; homologación y
traducciones."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app

from .apoyo import articulo, cargar, crear_usuario

CFG = "/api/v1/configuracion/ficha/2172"
FICHA = "/api/v1/articulos/RAD00188/ficha"


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188", panal_alto=400, panal_alto_unidad=1, material_panal="Aluminum", incluye_tapon="S"),
                   articulo("RAD00189", material_panal="COBRE", incluye_tapon="N"),
                   articulo("RAD00190", material_panal="Laton")])
        ids = {u: crear_usuario(c, u, r) for u, r in (("op1", "OPERADOR"), ("cfg", "FOTOS"))}
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


def atributos(cli) -> dict:
    return {a["etiqueta"] or a["nombre"]: a for a in cli.get(CFG).json()["atributos"]}


def test_01_sin_el_permiso_no_se_configura(entorno):
    op1 = como(entorno, "op1")
    for r in (op1.get(CFG), op1.get("/api/v1/configuracion/ficha/columnas-sap"), op1.patch(f"{CFG}/267", json={"etiqueta": "x"}),
              op1.post(f"{CFG}/propios", json={"nombre": "Algo", "tipo": "TEXTO"}),
              op1.put("/api/v1/configuracion/traducciones/203", json={"valor_es": "x"})):
        assert r.status_code == 403


def test_02_lee_la_configuracion_con_opciones_y_homologacion(entorno):
    d = como(entorno, "cfg").get(CFG).json()
    assert d["categorias"] == ["RADIADORES"]
    a = {x["etiqueta"]: x for x in d["atributos"]}
    assert (a["Alto"]["tipo"], a["Alto"]["requiere_uom"], a["Alto"]["habilitado"], a["Alto"]["obligatorio"]) == ("NUMERO", True, True, True)
    assert (a["Alto"]["columna_sap"], a["Alto"]["conversion"], a["Alto"]["propio"]) == ("panal_alto_mm", "NUMERO", False)
    material = {o["valor"]: o for o in a["Material panal"]["opciones"]}
    assert material["Aluminum"]["valor_es"] == "Aluminio" and material["Aluminum"]["homologados"] == ["ALUMINIO", "ALUMINUM"]
    assert a["Tipo de panal"]["tipo"] == "TEXTO" and a["Filas"]["tipo"] == "NUMERO"
    columnas = {x["columna"]: x for x in como(entorno, "cfg").get("/api/v1/configuracion/ficha/columnas-sap").json()}
    assert columnas["material_panal"]["campo_sap"] == "U_CoreMaterial" and "incluye_tapon" in columnas


def test_03_configurar_un_atributo_de_autocare(entorno):
    cfg = como(entorno, "cfg")
    r = cfg.patch(f"{CFG}/5061", json={"etiqueta": "  Filas del panal ", "obligatorio": False, "orden": 20, "grupo": "MEDIDAS"}).json()
    assert (r["etiqueta"], r["obligatorio"], r["orden"], r["grupo"]) == ("Filas del panal", False, 20, "MEDIDAS")
    r = cfg.patch(f"{CFG}/5061", json={"habilitado": False}).json()
    assert not r["habilitado"] and not r["obligatorio"]
    assert "Filas del panal" not in {a["etiqueta"] for a in como(entorno, "op1").get(FICHA).json()["atributos"]}
    assert cfg.patch(f"{CFG}/5061", json={"obligatorio": True}).status_code == 422          # solo si está habilitado
    r = cfg.patch(f"{CFG}/5061", json={"habilitado": True, "etiqueta": ""}).json()
    assert r["habilitado"] and r["etiqueta"] is None                                          # vacío vuelve al nombre de PAdb
    assert cfg.patch(f"{CFG}/5061", json={"columna_sap": "no_existe", "conversion": "NUMERO"}).status_code == 422
    malo = cfg.patch(f"{CFG}/5061", json={"columna_sap": "material_panal", "conversion": "LISTA"})
    assert malo.status_code == 422 and malo.json()["title"] == "Esa conversión no sirve para este atributo"
    r = cfg.patch(f"{CFG}/270", json={"columna_sap": None}).json()                            # sin columna, sin precarga
    assert (r["columna_sap"], r["conversion"], r["parte"]) == (None, None, None)
    assert cfg.patch(f"{CFG}/270", json={"columna_sap": "dimension_tanque", "conversion": "PARTE_DE_MEDIDA"}).status_code == 422
    r = cfg.patch(f"{CFG}/270", json={"columna_sap": "dimension_tanque", "conversion": "PARTE_DE_MEDIDA", "parte": 1}).json()
    assert (r["conversion"], r["parte"]) == ("PARTE_DE_MEDIDA", 1)
    assert cfg.patch(f"{CFG}/99999", json={"orden": 1}).status_code == 404


def test_04_campos_propios(entorno):
    cfg = como(entorno, "cfg")
    assert cfg.post(f"{CFG}/propios", json={"nombre": "Tipo de aleta", "tipo": "LISTA"}).status_code == 422     # sin opciones
    assert cfg.post(f"{CFG}/propios", json={"nombre": "Alto", "tipo": "TEXTO"}).status_code == 409              # ya existe
    assert cfg.post(f"{CFG}/propios", json={"nombre": "Nota", "tipo": "TEXTO", "medida": True}).status_code == 422
    aleta = cfg.post(f"{CFG}/propios", json={"nombre": "Tipo de aleta", "tipo": "LISTA", "opciones": ["Recta", "Ondulada"],
                                             "grupo": "CONSTRUCCION"})
    assert aleta.status_code == 201
    a = aleta.json()
    assert a["propio"] and a["paid"] >= 1_000_000 and a["habilitado"] and [o["valor"] for o in a["opciones"]] == ["Recta", "Ondulada"]
    assert all(o["propia"] and o["valid_value_id"] >= 1_000_000 for o in a["opciones"])
    espesor = cfg.post(f"{CFG}/propios", json={"nombre": "Espesor de aleta", "tipo": "NUMERO", "medida": True, "obligatorio": True})
    assert espesor.json()["requiere_uom"] and espesor.json()["obligatorio"]
    sensor = cfg.post(f"{CFG}/propios", json={"nombre": "Incluye tapón", "tipo": "SI_NO", "grupo": "INCLUYE"}).json()
    r = cfg.patch(f"{CFG}/{sensor['paid']}", json={"columna_sap": "incluye_tapon", "conversion": "SI_NO"})
    assert r.status_code == 200
    assert cfg.patch(f"{CFG}/{sensor['paid']}", json={"conversion": "NUMERO"}).status_code == 422
    assert cfg.post(f"{CFG}/propios", json={"nombre": "Nota técnica", "tipo": "TEXTO"}).status_code == 201


def test_05_la_ficha_usa_y_valida_los_campos_propios(entorno):
    op1, cfg = como(entorno, "op1"), como(entorno, "cfg")
    a = atributos(cfg)
    assert op1.post("/api/v1/articulos/RAD00188/asignacion").status_code == 200
    f = op1.get(FICHA).json()
    ficha = {x["etiqueta"]: x for x in f["atributos"]}
    tapon = ficha["Incluye tapón"]
    assert (tapon["tipo"], tapon["propio"], tapon["nombre_pies"]) == ("si_no", True, "Campo propio de Nexo")
    assert tapon["valor"]["valor_texto"] == "SI" and tapon["origen"] == "SAP"                    # precargado de incluye_tapon = S
    assert ficha["Tipo de aleta"]["tipo"] == "lista" and ficha["Espesor de aleta"]["tipo"] == "numero"
    assert ficha["Nota técnica"]["tipo"] == "texto"
    requisitos = {r["codigo"] for r in op1.get("/api/v1/articulos/RAD00188").json()["requisitos"]}
    assert "ATRIBUTO:Espesor de aleta" in requisitos                                            # obligatorio propio
    v = f["version"]
    malo = op1.put(FICHA, json={"version": v, "cambios": [{"paid": tapon["paid"], "valor_texto": "TAL VEZ"}]})
    assert malo.status_code == 422 and malo.json()["title"] == "Ese valor no es válido para el atributo"
    otra = op1.put(FICHA, json={"version": v, "cambios": [{"paid": a["Tipo de aleta"]["paid"], "valid_value_id": 203}]})
    assert otra.status_code == 422
    texto_en_numero = op1.put(FICHA, json={"version": v, "cambios": [{"paid": a["Espesor de aleta"]["paid"], "valor_texto": "1 mm"}]})
    assert texto_en_numero.status_code == 422
    ondulada = a["Tipo de aleta"]["opciones"][1]["valid_value_id"]
    r = op1.put(FICHA, json={"version": v, "cambios": [
        {"paid": tapon["paid"], "valor_texto": "NO"},
        {"paid": a["Tipo de aleta"]["paid"], "valid_value_id": ondulada},
        {"paid": a["Espesor de aleta"]["paid"], "valor_num": "0.12", "uom_code": "MM"},
        {"paid": a["Nota técnica"]["paid"], "valor_texto": "Aleta louver"}]})
    assert r.status_code == 200
    ficha = {x["etiqueta"]: x for x in r.json()["atributos"]}
    assert ficha["Incluye tapón"]["valor"]["valor_texto"] == "NO" and ficha["Incluye tapón"]["confirmado"]
    assert ficha["Tipo de aleta"]["valor"]["valid_value_id"] == ondulada
    assert "ATRIBUTO:Espesor de aleta" not in {x["codigo"] for x in op1.get("/api/v1/articulos/RAD00188").json()["requisitos"]}


def test_06_opciones_de_un_campo_propio(entorno):
    cfg = como(entorno, "cfg")
    aleta = atributos(cfg)["Tipo de aleta"]
    url = f"{CFG}/{aleta['paid']}/opciones"
    recta, ondulada = (o["valid_value_id"] for o in aleta["opciones"])
    r = cfg.post(url, json={"valor": "Louver"}).json()
    assert [o["valor"] for o in r["opciones"]] == ["Recta", "Ondulada", "Louver"]
    assert cfg.post(url, json={"valor": "louver"}).status_code == 409
    r = cfg.patch(f"{url}/{ondulada}", json={"valor": "Ondulada (wavy)"}).json()
    assert r["opciones"][1]["valor"] == "Ondulada (wavy)" and r["opciones"][1]["en_uso"] == 1     # RAD00188 la conserva
    assert cfg.delete(f"{url}/{ondulada}").status_code == 409                                       # en uso
    r = cfg.delete(f"{url}/{recta}").json()
    assert [o["valor"] for o in r["opciones"]] == ["Ondulada (wavy)", "Louver"]
    assert cfg.post(f"{CFG}/302/opciones", json={"valor": "Titanio"}).status_code == 422             # AutoCare no se cambia


def test_07_homologacion_y_valores_de_sap(entorno):
    cfg = como(entorno, "cfg")
    valores = {v["valor"]: v for v in cfg.get(f"{CFG}/302/valores-sap").json()}
    assert valores["ALUMINUM"]["valid_value_id"] == 203 and valores["LATON"]["valid_value_id"] is None
    r = cfg.put(f"{CFG}/302/homologacion", json=[{"valor_sap": "aluminum", "valid_value_id": 203},
                                                 {"valor_sap": "Cobre", "valid_value_id": 381}])
    assert {o["valor"]: o["homologados"] for o in r.json()["opciones"]} == {"Aluminum": ["ALUMINUM"], "Copper": ["COBRE"]}
    assert cfg.put(f"{CFG}/302/homologacion", json=[{"valor_sap": "X", "valid_value_id": 890}]).status_code == 422   # no es del 302
    assert cfg.put(f"{CFG}/302/homologacion", json=[{"valor_sap": "x", "valid_value_id": 203},
                                                    {"valor_sap": "X", "valid_value_id": 381}]).status_code == 422
    assert cfg.put(f"{CFG}/267/homologacion", json=[]).status_code == 422                                           # no es lista


def test_08_traducciones(entorno):
    cfg = como(entorno, "cfg")
    assert cfg.put("/api/v1/configuracion/traducciones/203", json={"valor_es": " Aluminio  puro "}).status_code == 204
    material = {o["valor"]: o for o in atributos(cfg)["Material panal"]["opciones"]}
    assert material["Aluminum"]["valor_es"] == "Aluminio puro"
    assert cfg.put("/api/v1/configuracion/traducciones/203", json={"valor_es": ""}).status_code == 204
    assert {o["valor"]: o for o in atributos(cfg)["Material panal"]["opciones"]}["Aluminum"]["valor_es"] is None
    assert cfg.put("/api/v1/configuracion/traducciones/77777", json={"valor_es": "x"}).status_code == 404
    propia = atributos(cfg)["Tipo de aleta"]["opciones"][0]["valid_value_id"]
    assert cfg.put(f"/api/v1/configuracion/traducciones/{propia}", json={"valor_es": "x"}).status_code == 422


def test_09_borrar_un_campo_propio(entorno):
    cfg = como(entorno, "cfg")
    a = atributos(cfg)
    assert cfg.delete(f"{CFG}/{a['Tipo de aleta']['paid']}").status_code == 409                  # en uso: se deshabilita
    assert cfg.delete(f"{CFG}/267").status_code == 422                                            # de AutoCare
    sin_uso = cfg.post(f"{CFG}/propios", json={"nombre": "Temporal", "tipo": "LISTA", "opciones": ["A"]}).json()
    assert cfg.delete(f"{CFG}/{sin_uso['paid']}").status_code == 204
    assert "Temporal" not in atributos(cfg)


def test_10_auditado(entorno):
    _, ids, bd = entorno
    with psycopg.connect(bd) as c:
        entidades = {r[0] for r in c.execute("select distinct entidad from audit.auditoria_evento where actor = %s", (str(ids["cfg"]),))}
    assert {"meta.atributo_config", "meta.atributo_valor_permitido", "meta.valor_sap_pies", "meta.traduccion_valor"} <= entidades
