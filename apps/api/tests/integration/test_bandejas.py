"""Bandejas y flujo (workflow-estados reglas 3 y 8): "Siguiente" con prioridad y doble control, reservas, transiciones,
listado con filtros, búsqueda y vistas guardadas."""

from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app

from .apoyo import articulo, cargar, completar, crear_usuario

Q = "cat=25&linea=IMPORTADO"


def mes(atras: int) -> date:
    hoy = date.today()
    total = hoy.year * 12 + hoy.month - 1 - atras
    return date(total // 12, total % 12 + 1, 1)


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [
            articulo("RAD00188", descripcion="RADIADOR TOYOTA 22R PLAST M 86/94 MT", numero_parte_proveedor="ZC-IS011",
                     panal_alto=400, panal_alto_unidad=1, panal_largo=518, panal_largo_unidad=1, panal_ancho=26, panal_ancho_unidad=1),
            articulo("RAD00174", descripcion="RADIADOR TOYOTA YARIS M 06/08 AT", codigo_anterior="13098"),
            articulo("RAD00156", descripcion="RADIADOR HONDA CRV M 02/05 AT",
                     panal_alto=520, panal_alto_unidad=1, panal_largo=395, panal_largo_unidad=1),       # alto/largo invertidos
            articulo("RAD00999", descripcion="RADIADOR SIN VENTA"),
        ])
        ids = {u: crear_usuario(c, u, *r) for u, r in [("op1", ["OPERADOR"]), ("op2", ["OPERADOR"]), ("sup1", ["SUPERVISOR"]),
                                                       ("sup2", ["SUPERVISOR"])]}
        # Ventas: RAD00174 vende más que RAD00188; RAD00156 poco; RAD00999 nada
        for atras in range(1, 13):
            c.execute("insert into app.venta_mensual values ('RAD00174', %s, 50), ('RAD00188', %s, 30), ('RAD00156', %s, 1)",
                      (mes(atras), mes(atras), mes(atras)))
        c.execute("insert into meta.carga_ventas (meses, articulos, filas) values (12, 3, 36)")
        # RAD00156 rechazado: debe salir primero en la bandeja del operador
        completar(c, "RAD00156", ids["op2"])
        c.execute("select app.fn_transicionar(id, 'POR_VALIDAR', 'USUARIO', %s) from app.articulo where item_code = 'RAD00156'",
                  (str(ids["op2"]),))
        c.execute("select app.fn_transicionar(id, 'RECHAZADO', 'USUARIO', %s, 'Faltan años') from app.articulo where item_code = 'RAD00156'",
                  (str(ids["sup1"]),))
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    return motor, ids


def como(entorno, usuario: str) -> TestClient:
    motor, ids = entorno
    with motor.connect() as c:
        u = cargar_usuario(c, ids[usuario])
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: u
    return TestClient(app)


def test_01_siguiente_prioriza_rechazados_y_luego_venta(entorno):
    op1, op2 = como(entorno, "op1"), como(entorno, "op2")
    a = op1.post(f"/api/v1/bandejas/operador/siguiente?{Q}").json()["articulo"]
    assert a["item_code"] == "RAD00156" and a["ultimo_motivo"] == "Faltan años" and a["reserva"]["mia"]
    assert op1.post(f"/api/v1/bandejas/operador/siguiente?{Q}").json()["articulo"]["item_code"] == "RAD00156"  # ya tiene uno
    assert op2.post(f"/api/v1/bandejas/operador/siguiente?{Q}").json()["articulo"]["item_code"] == "RAD00174"  # clase A primero
    assert como(entorno, "op1").post(f"/api/v1/bandejas/supervisor/siguiente?{Q}").status_code == 403


def test_02_reserva_ajena_bloquea_transiciones(entorno):
    op2 = como(entorno, "op2")
    a = op2.get("/api/v1/articulos/RAD00156").json()
    envio = next(x for x in a["acciones"] if x["destino"] == "POR_VALIDAR")
    assert not envio["habilitada"] and envio["razon"] == "Está reservado por otro usuario."
    r = op2.post("/api/v1/articulos/RAD00156/transiciones", json={"destino": "POR_VALIDAR", "version": a["version"]})
    assert r.status_code == 409 and r.json()["title"] == "Está reservado por otro usuario"
    assert op2.put("/api/v1/articulos/RAD00156/asignacion").status_code == 409            # el latido solo es del dueño
    tomar = op2.post("/api/v1/articulos/RAD00156/asignacion")
    assert tomar.status_code == 409 and tomar.json()["detail"] == "op1 lo está trabajando"
    assert op2.post("/api/v1/articulos/RAD00999/asignacion").status_code == 200       # libre: lo toma
    assert op2.get("/api/v1/articulos/RAD00999").json()["reserva"]["mia"]
    op2.delete("/api/v1/articulos/RAD00999/asignacion")


def test_03_enviar_conflicto_de_version_y_doble_control(entorno):
    op1, sup1, sup2 = como(entorno, "op1"), como(entorno, "sup1"), como(entorno, "sup2")
    a = op1.get("/api/v1/articulos/RAD00156").json()
    assert a["requisitos"] == []
    r = op1.post("/api/v1/articulos/RAD00156/transiciones", json={"destino": "POR_VALIDAR", "version": a["version"] - 1})
    assert r.status_code == 409 and r.json()["title"] == "Otro usuario cambió este artículo"
    r = op1.post("/api/v1/articulos/RAD00156/transiciones", json={"destino": "POR_VALIDAR", "version": a["version"]})
    assert r.status_code == 200 and r.json()["estado"] == "POR_VALIDAR" and r.json()["reserva"] is None   # se libera al transicionar

    # sup1 lo rechazó antes, pero el envío es de op1: puede tomarlo. Si sup2 hubiera enviado, no le tocaría a sup2.
    v = sup1.post(f"/api/v1/bandejas/supervisor/siguiente?{Q}").json()["articulo"]
    assert v["item_code"] == "RAD00156"
    sin_motivo = sup1.post("/api/v1/articulos/RAD00156/transiciones", json={"destino": "RECHAZADO", "version": v["version"]})
    assert sin_motivo.status_code == 422 and sin_motivo.json()["errors"][0]["campo"] == "motivo"
    ok = sup1.post("/api/v1/articulos/RAD00156/transiciones", json={"destino": "VALIDADO", "version": v["version"]})
    assert ok.json()["estado"] == "VALIDADO"
    assert sup2.post(f"/api/v1/bandejas/supervisor/siguiente?{Q}").json()["articulo"] is None             # bandeja vacía


def test_04_supervisor_no_recibe_lo_que_el_mismo_envio(entorno):
    sup2 = como(entorno, "sup2")
    motor, ids = entorno
    with motor.connect() as c:
        c.exec_driver_sql(f"""select app.fn_transicionar(id, 'PENDIENTE', 'USUARIO', '{ids['sup1']}', 'Reapertura de prueba')
                              from app.articulo where item_code = 'RAD00156'""")
        c.commit()
    with psycopg.connect(dict_bd(motor), autocommit=True) as c:
        completar(c, "RAD00999", ids["sup2"])
        c.execute("select app.fn_transicionar(id, 'POR_VALIDAR', 'USUARIO', %s) from app.articulo where item_code = 'RAD00999'",
                  (str(ids["sup2"]),))
    assert sup2.post(f"/api/v1/bandejas/supervisor/siguiente?{Q}").json()["articulo"] is None
    assert como(entorno, "sup1").post(f"/api/v1/bandejas/supervisor/siguiente?{Q}").json()["articulo"]["item_code"] == "RAD00999"
    detalle = sup2.get("/api/v1/articulos/RAD00999").json()
    validar = next(x for x in detalle["acciones"] if x["destino"] == "VALIDADO")
    assert not validar["habilitada"]                     # reservado por sup1 (y además sup2 lo envió)


def dict_bd(motor) -> str:
    u = motor.url
    return f"host={u.host} dbname={u.database} user={u.username} password={u.password}"


def test_05_listado_con_filtros_orden_y_paginacion(entorno):
    op1 = como(entorno, "op1")
    d = op1.get(f"/api/v1/articulos?{Q}&limit=2").json()
    assert d["total"] == 4 and [i["item_code"] for i in d["items"]] == ["RAD00174", "RAD00188"] and d["next_cursor"]
    d2 = op1.get(f"/api/v1/articulos?{Q}&limit=2&cursor={d['next_cursor']}").json()
    assert [i["item_code"] for i in d2["items"]] == ["RAD00156", "RAD00999"] and d2["next_cursor"] is None
    assert op1.get(f"/api/v1/articulos?{Q}&clase=SIN_VENTA").json()["total"] == 1
    assert op1.get(f"/api/v1/articulos?{Q}&estado=PENDIENTE&q=toyota").json()["total"] == 2
    assert op1.get(f"/api/v1/articulos?{Q}&q=13098").json()["items"][0]["item_code"] == "RAD00174"     # código anterior
    assert op1.get(f"/api/v1/articulos?{Q}&completitud=completa").json()["total"] == 2   # RAD00156 y RAD00999 (prueba 4)
    assert op1.get(f"/api/v1/articulos?{Q}&cursor=no-valido").status_code == 422


def test_06_busqueda(entorno):
    op1 = como(entorno, "op1")
    buscar = lambda q: op1.get(f"/api/v1/busqueda?{Q}&q={q}").json()  # noqa: E731
    assert [(x["item_code"], x["coincide"]) for x in buscar("RAD0018")["articulos"]] == [("RAD00188", "codigo")]
    assert buscar("22r toyota")["articulos"][0]["item_code"] == "RAD00188"            # palabras en cualquier orden
    assert buscar("ZC-IS011")["articulos"][0]["coincide"] == "numero_parte"
    assert buscar("13098")["articulos"][0]["coincide"] == "codigo_anterior"
    medidas = buscar("405x515")
    assert medidas["medidas"] == ["405", "515"] and medidas["articulos"][0]["item_code"] == "RAD00188"
    assert [x["item_code"] for x in buscar("400 520")["articulos"]] == ["RAD00188", "RAD00156"]   # sin orden, ±10 mm; el más cercano primero
    assert buscar("400x518x40")["articulos"] == []                                     # el ancho no coincide


def test_07_vistas_guardadas_por_usuario(entorno):
    op1, op2 = como(entorno, "op1"), como(entorno, "op2")
    v = op1.put("/api/v1/vistas", json={"nombre": "Sin foto", "parametros": {"con_foto": False}}).json()
    op1.put("/api/v1/vistas", json={"nombre": "Sin foto", "parametros": {"con_foto": False, "clase": ["A"]}})
    assert [x["parametros"] for x in op1.get("/api/v1/vistas").json()] == [{"con_foto": False, "clase": ["A"]}]
    assert op2.get("/api/v1/vistas").json() == []
    op2.delete(f"/api/v1/vistas/{v['id']}")                                           # no es suya: no la borra
    assert len(op1.get("/api/v1/vistas").json()) == 1


def test_08_historial(entorno):
    eventos = como(entorno, "op1").get("/api/v1/articulos/RAD00156/historial").json()
    assert [e["estado_destino"] for e in eventos if e["tipo"] == "TRANSICION"][:3] == ["PENDIENTE", "VALIDADO", "POR_VALIDAR"]
    assert eventos[0]["actor"] == "sup1" and eventos[0]["motivo"] == "Reapertura de prueba"
