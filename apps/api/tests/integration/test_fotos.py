"""Fotos propias: subida por el encargado (WebP con la convención de MinIO, numeración que continúa), orden, artículos sin foto y la
tarea NUEVA_FOTO cuando el artículo ya está validado (ADR 0013, propuesta UX §6.9). MinIO es un doble."""

import io

import psycopg
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app
from nexo_api.modules.emparejamiento import obtener_catalogo_maestro
from nexo_api.modules.imagenes import obtener_almacen, obtener_firmador

from .apoyo import articulo, cargar, crear_usuario, validar

URL = "/api/v1/articulos/RAD00188/fotos"


class AlmacenFalso:
    bucket = "rlt-dru"

    def __init__(self):
        self.objetos: dict[str, bytes] = {}

    def subir(self, objeto, datos, tipo="image/webp"):
        self.objetos[objeto] = datos


class FirmadorFalso:
    def firmar(self, objeto, bucket=None, segundos=3600):
        return f"https://minio.test/{bucket}/{objeto}?firma"


ALMACEN = AlmacenFalso()


def imagen(formato="JPEG", tamano=(400, 300), orientacion=None) -> bytes:
    b = io.BytesIO()
    img = Image.new("RGBA" if formato == "PNG" else "RGB", tamano, "steelblue")
    if orientacion:
        exif = img.getexif()
        exif[0x0112] = orientacion
        img.save(b, formato, exif=exif)
    else:
        img.save(b, formato)
    return b.getvalue()


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188"), articulo("RAD00156"), articulo("RAD00999"),
                   articulo("RAD00001", descripcion="INACTIVO", congelado_sap="Y")])
        ids = {u: crear_usuario(c, u, r) for u, r in (("fotos1", "FOTOS"), ("op1", "OPERADOR"), ("sup1", "SUPERVISOR"))}
        validar(c, "RAD00156", ids["op1"], ids["sup1"])
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    return motor, ids, bd


def como(entorno, usuario: str, almacen=ALMACEN) -> TestClient:
    motor, ids, _ = entorno
    with motor.connect() as c:
        u = cargar_usuario(c, ids[usuario])
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: u
    app.dependency_overrides[obtener_almacen] = lambda: almacen
    app.dependency_overrides[obtener_firmador] = FirmadorFalso
    app.dependency_overrides[obtener_catalogo_maestro] = lambda: None
    return TestClient(app)


def subir(cli, url, *archivos):
    return cli.post(url, files=[("archivos", (nombre, datos, "image/jpeg")) for nombre, datos in archivos])


def test_01_solo_el_encargado_o_el_administrador_sube(entorno):
    f = como(entorno, "op1").get(URL).json()
    assert f == {"item_code": "RAD00188", "puede_subir": False, "subida_disponible": True, "propias": [], "proveedor": [], "subidas": 0}
    assert subir(como(entorno, "op1"), URL, ("a.jpg", imagen())).status_code == 403
    assert como(entorno, "fotos1").get(URL).json()["puede_subir"]


def test_02_sube_webp_con_la_convencion_y_la_orientacion_de_la_camara(entorno):
    r = subir(como(entorno, "fotos1"), URL, ("celular.jpg", imagen(orientacion=6)), ("captura.png", imagen("PNG", (3000, 1000))))
    assert r.status_code == 201
    f = r.json()
    assert f["subidas"] == 2 and [p["orden"] for p in f["propias"]] == [1, 2]
    assert f["propias"][0]["url"] == "https://minio.test/rlt-dru/imagenes_inventario/25_RADIADORES/RAD00188/RAD00188_1.webp?firma"
    assert (f["propias"][0]["subida_por"], f["propias"][0]["validada"]) == ("fotos1", False)
    objetos = ALMACEN.objetos
    girada = Image.open(io.BytesIO(objetos["imagenes_inventario/25_RADIADORES/RAD00188/RAD00188_1.webp"]))
    grande = Image.open(io.BytesIO(objetos["imagenes_inventario/25_RADIADORES/RAD00188/RAD00188_2.webp"]))
    assert (girada.format, girada.size) == ("WEBP", (300, 400))                 # EXIF 6: la foto se ve derecha
    assert grande.size == (2400, 800)                                           # el lado mayor se acota


def test_03_un_archivo_malo_no_deja_subidas_a_medias(entorno):
    antes = len(ALMACEN.objetos)
    r = subir(como(entorno, "fotos1"), URL, ("ok.jpg", imagen()), ("notas.txt", b"hola"))
    assert r.status_code == 422 and r.json()["title"] == "No es una imagen" and "notas.txt" in r.json()["detail"]
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, "GIF")
    assert subir(como(entorno, "fotos1"), URL, ("a.gif", gif.getvalue())).json()["title"] == "Formato de imagen no admitido"
    assert len(ALMACEN.objetos) == antes


def test_04_la_numeracion_continua_despues_de_las_existentes(entorno):
    _, _, bd = entorno
    with psycopg.connect(bd, autocommit=True) as c:                            # una foto de la importación inicial con _7
        c.execute("""insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto, orden)
                     select id, 'PROPIA', 'rlt-dru', 'imagenes_inventario/25_RADIADORES/RAD00188/RAD00188_7.webp', 3
                     from app.articulo where item_code = 'RAD00188'""")
    f = subir(como(entorno, "fotos1"), URL, ("x.jpg", imagen())).json()
    assert f["propias"][-1]["url"].endswith("RAD00188_8.webp?firma") and f["propias"][-1]["orden"] == 4


def test_05_ordenar(entorno):
    fotos1 = como(entorno, "fotos1")
    ids = [p["id"] for p in fotos1.get(URL).json()["propias"]]
    f = fotos1.put(f"{URL}/orden", json={"ids": ids[::-1]}).json()
    assert [p["id"] for p in f["propias"]] == ids[::-1]
    assert fotos1.put(f"{URL}/orden", json={"ids": ids[:2]}).status_code == 422


def test_06_foto_de_un_validado_crea_la_verificacion(entorno):
    _, _, bd = entorno
    assert subir(como(entorno, "fotos1"), "/api/v1/articulos/RAD00156/fotos", ("v.jpg", imagen())).status_code == 201
    with psycopg.connect(bd) as c:
        tareas = c.execute("""select t.origen::text, t.detalle ->> 'objeto' from app.tarea_verificacion t
                              join app.articulo a on a.id = t.articulo_id where a.item_code = 'RAD00156'""").fetchall()
    assert tareas == [("NUEVA_FOTO", "imagenes_inventario/25_RADIADORES/RAD00156/RAD00156_1.webp")]


def test_07_reglas(entorno):
    inactivo = subir(como(entorno, "fotos1"), "/api/v1/articulos/RAD00001/fotos", ("a.jpg", imagen()))
    assert inactivo.status_code == 409
    sin_llave = subir(como(entorno, "fotos1", almacen=None), URL, ("a.jpg", imagen()))
    assert sin_llave.status_code == 503 and sin_llave.json()["title"] == "Subida de fotos no configurada"
    assert como(entorno, "fotos1", almacen=None).get(URL).json()["subida_disponible"] is False
    assert subir(como(entorno, "fotos1"), "/api/v1/articulos/NOEXISTE/fotos", ("a.jpg", imagen())).status_code == 404


def test_08_pendientes_de_foto(entorno):
    sin = como(entorno, "fotos1").get("/api/v1/fotos/pendientes?cat=25&linea=IMPORTADO").json()
    assert [a["item_code"] for a in sin] == ["RAD00999"]                         # el inactivo no cuenta
    assert como(entorno, "op1").get("/api/v1/fotos/pendientes").status_code == 403


def test_09_auditado(entorno):
    _, ids, bd = entorno
    with psycopg.connect(bd) as c:
        actores = {r[0] for r in c.execute("select actor from audit.auditoria_evento where entidad = 'app.articulo_imagen'")}
    assert str(ids["fotos1"]) in actores
