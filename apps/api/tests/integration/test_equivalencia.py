"""Código equivalente de fabricados (ADR 0018): captura con sugerencia de SAP, importado sugerido, validación con foto, y confirmar
la equivalencia heredando parte y aplicaciones como sugerencias (ADR 0005); revisión de fabricados (propuesta UX §6.7)."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app
from nexo_api.modules.imagenes import obtener_firmador

from .apoyo import articulo, cargar, crear_usuario

FAB = "/api/v1/articulos/RLT00496/equivalencia"
FABRICADO = {"subcategoria_codigo": "2502", "subcategoria_nombre": "FABRICADOS"}


class FirmadorFalso:
    def firmar(self, objeto, bucket=None, segundos=3600):
        return f"https://minio.test/{objeto}"


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188", panal_alto=400, panal_alto_unidad=1, panal_largo=518, panal_largo_unidad=1),
                   articulo("RLT00496", codigo_anterior="RAD00188, OEM 16400", **FABRICADO),
                   articulo("RLT00500", **FABRICADO), articulo("RLT00501", **FABRICADO)])
        ids = {u: crear_usuario(c, u, r) for u, r in (("op1", "OPERADOR"), ("op2", "OPERADOR"), ("sup1", "SUPERVISOR"),
                                                      ("fotos1", "FOTOS"))}
        imp = c.execute("select id from app.articulo where item_code = 'RAD00188'").fetchone()[0]
        c.execute("insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por) values (%s, 7001, true, 'MANUAL', %s)",
                  (imp, ids["op1"]))
        c.execute("""insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, sub_model_id, engine_config_id, origen, confirmado_por,
                                                          confirmado_en)
                     values (%s, 10, 5, 7, 'MANUAL', %s, now()), (%s, 11, 5, 7, 'MANUAL', %s, now())""", (imp, ids["op1"], imp, ids["op1"]))
        c.execute("""insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto)
                     values (%s, 'PROPIA', 'rlt-dru', 'imagenes_inventario/25_RADIADORES/RAD00188/RAD00188_1.webp')""", (imp,))
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
    app.dependency_overrides[obtener_firmador] = FirmadorFalso
    return TestClient(app)


def test_01_sin_codigo_con_sugerencias_de_sap(entorno):
    e = como(entorno, "op1").get(FAB).json()
    assert (e["es_fabricado"], e["estado_codigo"], e["codigo_equivalente"], e["importado"]) == (True, "SIN_CODIGO", None, None)
    assert e["sugerencias"] == ["RAD00188", "OEM 16400"] and e["puede_capturar"] and not e["puede_validar"]
    imp = como(entorno, "op1").get("/api/v1/articulos/RAD00188/equivalencia").json()
    assert not imp["es_fabricado"] and not imp["puede_capturar"]


def test_02_capturar_el_itemcode_de_un_importado_lo_sugiere(entorno):
    e = como(entorno, "op1").put(FAB, json={"codigo": " rad00188 "}).json()
    assert (e["codigo_equivalente"], e["estado_codigo"], e["capturado_por"]) == ("RAD00188", "ESPERA_FOTO", "op1")
    i = e["importado"]
    assert (i["item_code"], i["equivalencia"], i["aplicaciones"], i["partes"]) == ("RAD00188", "SUGERIDA", 2, 1)
    assert i["medidas"]["alto"] == "400.00" and i["foto_url"].endswith("RAD00188_1.webp")
    assert e["sugerencias"] == ["OEM 16400"]
    assert como(entorno, "fotos1").put(FAB, json={"codigo": "X"}).status_code == 403
    assert como(entorno, "op1").put("/api/v1/articulos/RAD00188/equivalencia", json={"codigo": "X"}).status_code == 409


def test_03_validar_requiere_foto_propia_validada(entorno):
    motor, ids, bd = entorno
    assert como(entorno, "op1").post(f"{FAB}/validar").status_code == 403
    sin_foto = como(entorno, "sup1").post(f"{FAB}/validar")
    assert sin_foto.status_code == 422 and sin_foto.json()["title"] == "Falta una foto propia validada"
    with psycopg.connect(bd, autocommit=True) as c:
        c.execute("""insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto, validada, validada_por, validada_en)
                     select id, 'PROPIA', 'rlt-dru', 'imagenes_inventario/25_RADIADORES/RLT00496/RLT00496_1.webp', true, %s, now()
                     from app.articulo where item_code = 'RLT00496'""", (ids["sup1"],))
    e = como(entorno, "sup1").get(FAB).json()
    assert e["estado_codigo"] == "LISTO_PARA_VALIDAR" and e["puede_validar"] and not como(entorno, "op1").get(FAB).json()["puede_validar"]
    v = como(entorno, "sup1").post(f"{FAB}/validar").json()
    assert (v["estado_codigo"], v["validado_por"]) == ("VALIDADO", "sup1")


def test_04_cambiar_el_codigo_borra_la_validacion(entorno):
    op1 = como(entorno, "op1")
    e = op1.put(FAB, json={"codigo": "OEM 16400"}).json()
    assert (e["estado_codigo"], e["validado_por"]) == ("LISTO_PARA_VALIDAR", None)
    assert op1.put(FAB, json={"codigo": "RAD00188"}).json()["importado"]["item_code"] == "RAD00188"


def test_05_confirmar_y_heredar_requiere_editarlo(entorno):
    op1, op2 = como(entorno, "op1"), como(entorno, "op2")
    _, _, bd = entorno
    v = op1.get(FAB).json()["version"]
    sin_reserva = op1.post(f"{FAB}/confirmar", json={"version": v})
    assert sin_reserva.status_code == 409 and sin_reserva.json()["detail"] == "Toma el artículo para editarlo."
    assert op1.post("/api/v1/articulos/RLT00496/asignacion").status_code == 200
    assert op2.put(FAB, json={"codigo": "OTRO"}).status_code == 409                   # reservado por op1
    r = op1.post(f"{FAB}/confirmar", json={"version": v}).json()
    assert r["heredado"] == {"partes": 1, "aplicaciones_sugeridas": 2}
    e = r["equivalencia"]
    assert (e["importado"]["equivalencia"], e["importado"]["confirmada_por"], e["version"]) == ("CONFIRMADA", "op1", v + 1)
    with psycopg.connect(bd) as c:
        apl = c.execute("""select origen::text, confirmado_por from app.articulo_aplicacion x join app.articulo a on a.id = x.articulo_id
                           where a.item_code = 'RLT00496'""").fetchall()
    assert apl == [("HEREDADO_EQUIVALENTE", None)] * 2
    sin_importado = op1.post("/api/v1/articulos/RLT00500/asignacion")
    assert sin_importado.status_code == 200
    v500 = op1.get("/api/v1/articulos/RLT00500/equivalencia").json()["version"]
    r = op1.post("/api/v1/articulos/RLT00500/equivalencia/confirmar", json={"version": v500})
    assert r.status_code == 422 and r.json()["title"] == "No hay importado equivalente"


def test_06_revision_de_fabricados(entorno):
    r = como(entorno, "op1").get("/api/v1/fabricados?cat=25&linea=FABRICADO").json()
    assert r["por_estado"] == {"SIN_CODIGO": 2, "ESPERA_FOTO": 0, "LISTO_PARA_VALIDAR": 1, "VALIDADO": 0}
    assert [(f["item_code"], f["estado_codigo"], f["importado"]) for f in r["fabricados"]] == [
        ("RLT00496", "LISTO_PARA_VALIDAR", "RAD00188"), ("RLT00500", "SIN_CODIGO", None), ("RLT00501", "SIN_CODIGO", None)]
    sin = como(entorno, "op1").get("/api/v1/fabricados?cat=25&linea=FABRICADO&estado_codigo=SIN_CODIGO&q=501").json()
    assert (sin["total"], [f["item_code"] for f in sin["fabricados"]]) == (1, ["RLT00501"])
    assert como(entorno, "fotos1").get("/api/v1/fabricados?cat=25&linea=FABRICADO").status_code == 403
