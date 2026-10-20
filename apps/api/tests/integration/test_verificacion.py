"""Cola de verificación: foto nueva (conforme valida la foto), con hallazgo regresa a Pendiente, verificación manual, muestreo del
administrador y CAMBIO_CATALOGO informados por el agente de revisión del catálogo (ADR 0012, propuesta UX §6.6)."""

import json

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app
from nexo_api.modules.imagenes import obtener_firmador

from .apoyo import articulo, cargar, crear_usuario, validar

URL = "/api/v1/verificaciones"
FILTRO = "?cat=25&linea=IMPORTADO"


class FirmadorFalso:
    def firmar(self, objeto, bucket=None, segundos=3600):
        return f"https://minio.test/{objeto}"


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo(f"RAD0010{i}", panal_alto=400, panal_alto_unidad=1, panal_largo=518, panal_largo_unidad=1)
                   for i in range(1, 6)])
        ids = {u: crear_usuario(c, u, r) for u, r in (("op1", "OPERADOR"), ("sup1", "SUPERVISOR"), ("admin", "ADMINISTRADOR"))}
        for i in range(1, 6):
            validar(c, f"RAD0010{i}", ids["op1"], ids["sup1"], parte_id=5000 + i)
        c.execute("""insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto)
                     select id, 'PROPIA', 'rlt-dru', 'imagenes_inventario/25_RADIADORES/RAD00101/RAD00101_1.webp'
                     from app.articulo where item_code = 'RAD00101'""")
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


def tareas(cli, origen=None) -> list[dict]:
    return cli.get(URL + FILTRO + (f"&origen={origen}" if origen else "")).json()["tareas"]


def test_01_foto_nueva_en_la_cola(entorno):
    assert como(entorno, "op1").get(URL + FILTRO).status_code == 403
    cola = como(entorno, "sup1").get(URL + FILTRO).json()
    assert cola["por_origen"] == {"NUEVA_FOTO": 1, "MUESTREO": 0, "CAMBIO_CATALOGO": 0, "MANUAL": 0}
    t = cola["tareas"][0]
    assert (t["item_code"], t["origen"], t["estado_articulo"]) == ("RAD00101", "NUEVA_FOTO", "VALIDADO")
    assert t["foto_url"] == "https://minio.test/imagenes_inventario/25_RADIADORES/RAD00101/RAD00101_1.webp"
    assert t["medidas"] == {"alto": "400.00", "largo": "518.00", "ancho": None} and t["fotos_validadas"] == 0
    assert como(entorno, "sup1").get(URL + "?cat=18&linea=IMPORTADO").json()["tareas"] == []      # respeta el filtro global


def test_02_conforme_valida_la_foto(entorno):
    sup1 = como(entorno, "sup1")
    _, _, bd = entorno
    tid = tareas(sup1)[0]["id"]
    assert sup1.post(f"{URL}/{tid}/resolucion", json={"resultado": "CONFORME"}).status_code == 204
    assert tareas(sup1) == []
    with psycopg.connect(bd) as c:
        assert c.execute("select validada from app.articulo_imagen").fetchone()[0] is True
        assert c.execute("select estado::text from app.articulo where item_code = 'RAD00101'").fetchone()[0] == "VALIDADO"
    otra = sup1.post(f"{URL}/{tid}/resolucion", json={"resultado": "CONFORME"})
    assert otra.status_code == 409 and otra.json()["title"] == "Esa verificación ya se resolvió"
    assert sup1.post(f"{URL}/999999/resolucion", json={"resultado": "CONFORME"}).status_code == 404


def test_03_manual_y_con_hallazgo_regresa_a_pendiente(entorno):
    sup1 = como(entorno, "sup1")
    _, _, bd = entorno
    assert sup1.post(URL, json={"item_code": "rad00102", "nota": "Revisar años"}).status_code == 201
    assert sup1.post(URL, json={"item_code": "RAD00102", "nota": "Otra vez"}).status_code == 409
    assert sup1.post(URL, json={"item_code": "NOEXISTE", "nota": "x" * 5}).status_code == 404
    t = tareas(sup1, "MANUAL")[0]
    assert t["detalle"] == {"nota": "Revisar años", "creada_por": "sup1"}
    sin_nota = sup1.post(f"{URL}/{t['id']}/resolucion", json={"resultado": "CON_HALLAZGO", "nota": "  "})
    assert sin_nota.status_code == 422
    assert sup1.post(f"{URL}/{t['id']}/resolucion", json={"resultado": "CON_HALLAZGO", "nota": "Los años son 1990-1995"}).status_code == 204
    with psycopg.connect(bd) as c:
        estado, motivo = c.execute("""select a.estado::text, e.motivo from app.articulo a
                                      join audit.bitacora_articulo e on e.articulo_id = a.id
                                      where a.item_code = 'RAD00102' and e.tipo = 'TRANSICION' order by e.id desc limit 1""").fetchone()
    assert (estado, motivo) == ("PENDIENTE", "VERIFICACION")


def test_04_manual_solo_de_validados(entorno):
    r = como(entorno, "sup1").post(URL, json={"item_code": "RAD00102", "nota": "Otra revisión"})   # quedó en Pendiente
    assert r.status_code == 409 and r.json()["title"] == "Solo se verifican artículos validados"


def test_04b_muestreo_solo_administrador(entorno):
    assert como(entorno, "sup1").post(f"{URL}/muestreo{FILTRO}", json={"cantidad": 2}).status_code == 403
    r = como(entorno, "admin").post(f"{URL}/muestreo{FILTRO}", json={"cantidad": 2})
    assert r.json() == {"creadas": 2}
    assert len(tareas(como(entorno, "admin"), "MUESTREO")) == 2


def test_05_cambio_en_el_catalogo_llega_a_la_cola(entorno):
    """El agente de revisión (otro proceso) informa por app.fn_registrar_cambios_catalogo; aquí se ve en la cola."""
    _, _, bd = entorno
    cambios = [{"parte_id": 5003, "estado": "FUSIONADA", "fusionada_en_id": 9001},
               {"parte_id": 5004, "estado": "DATOS_CAMBIARON", "huella": "h1", "nota": "El alto pasó de 400 a 410 mm en el catálogo."}]
    with psycopg.connect(bd, autocommit=True) as c:
        assert c.execute("select app.fn_registrar_cambios_catalogo(%s)", (json.dumps(cambios),)).fetchone()[0]["tareas"] == 2
    cambios = {t["item_code"]: t["detalle"] for t in tareas(como(entorno, "sup1"), "CAMBIO_CATALOGO")}
    assert cambios["RAD00103"] == {"parte_id": 5003, "estado": "FUSIONADA", "fusionada_en_id": 9001, "clave": "FUSIONADA:9001"}
    assert cambios["RAD00104"]["nota"] == "El alto pasó de 400 a 410 mm en el catálogo."
