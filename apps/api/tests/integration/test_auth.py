"""Autenticación (ADR 0015) y permisos (ADR 0022): escenario completo contra una base nexo desechable, sesiones en memoria."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth import contrasenas
from nexo_api.auth.dependencias import obtener_sesiones
from nexo_api.auth.sesiones import SesionesMemoria
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app

ADMIN_PASS = "Admin-Prueba-2026!"


@pytest.fixture(scope="module")
def entorno(bd):
    """App con la base de prueba, sesiones en memoria y un administrador inicial."""
    with psycopg.connect(bd, autocommit=True) as c:
        uid = c.execute("insert into app.usuario (usuario, nombre, password_hash, debe_cambiar_password) "
                        "values ('admin', 'Administradora', %s, false) returning id", (contrasenas.hashear(ADMIN_PASS),)).fetchone()[0]
        c.execute("insert into app.usuario_rol values (%s, 'ADMINISTRADOR')", (uid,))
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    app = crear_app()
    sesiones = SesionesMemoria(8 * 3600)
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[obtener_sesiones] = lambda: sesiones
    return app, bd


def entrar(app, usuario: str, password: str) -> tuple[TestClient, dict]:
    cliente = TestClient(app)
    r = cliente.post("/api/v1/sesion", json={"usuario": usuario, "password": password})
    if r.status_code == 200:
        cliente.headers["X-CSRF-Token"] = r.json()["csrf"]
    return cliente, r


def eventos(bd: str, usuario: str) -> list[str]:
    with psycopg.connect(bd) as c:
        return [f[0] for f in c.execute("select tipo::text from audit.evento_acceso where usuario = %s order by id", (usuario,))]


@pytest.fixture(scope="module")
def admin(entorno):
    cliente, r = entrar(entorno[0], "admin", ADMIN_PASS)
    assert r.status_code == 200, r.json()
    return cliente


def test_01_sin_sesion_no_hay_datos(entorno):
    r = TestClient(entorno[0]).get("/api/v1/categorias")
    assert r.status_code == 401 and r.headers["content-type"] == "application/problem+json"
    assert TestClient(entorno[0]).get("/api/v1/salud").status_code == 200        # salud es pública


def test_02_credenciales_incorrectas_no_revelan_si_el_usuario_existe(entorno):
    app, bd = entorno
    _, malo = entrar(app, "admin", "otra-cosa-cualquiera")
    _, inexistente = entrar(app, "nadie", "otra-cosa-cualquiera")
    assert malo.status_code == inexistente.status_code == 401
    assert malo.json()["title"] == inexistente.json()["title"] == "Usuario o contraseña incorrectos"
    assert eventos(bd, "nadie") == ["ENTRADA_FALLIDA"]


def test_03_alta_por_administrador_y_cambio_obligatorio(entorno, admin):
    app, bd = entorno
    r = admin.post("/api/v1/usuarios", json={"usuario": "ana.op", "nombre": "Ana Operadora", "roles": ["OPERADOR"]})
    assert r.status_code == 201
    temporal = r.json()["password_temporal"]
    assert r.json()["usuario"]["debe_cambiar_password"] is True and len(temporal) == 19
    assert admin.post("/api/v1/usuarios", json={"usuario": "ANA.OP", "nombre": "Otra", "roles": ["OPERADOR"]}).status_code == 409

    ana, r = entrar(app, "ana.op", temporal)
    assert r.status_code == 200 and r.json()["usuario"]["debe_cambiar_password"] is True
    assert ana.get("/api/v1/categorias").json()["title"] == "Debes cambiar tu contraseña antes de continuar"

    debil = ana.post("/api/v1/sesion/password", json={"actual": temporal, "nueva": "ana.op-12345678"})
    assert debil.status_code == 422 and debil.json()["errors"][0]["mensaje"] == "No debe contener tu nombre de usuario."
    sin_csrf = TestClient(app, cookies=ana.cookies).post("/api/v1/sesion/password", json={"actual": temporal, "nueva": "x"})
    assert sin_csrf.status_code == 403

    r = ana.post("/api/v1/sesion/password", json={"actual": temporal, "nueva": "Radiador-Azul-Hilux-86"})
    assert r.status_code == 200 and r.json()["usuario"]["debe_cambiar_password"] is False
    ana.headers["X-CSRF-Token"] = r.json()["csrf"]
    assert ana.get("/api/v1/categorias").status_code == 200
    assert eventos(bd, "ana.op") == ["ALTA", "ENTRADA", "CAMBIO_PASSWORD"]


def test_04_bloqueo_tras_cinco_intentos(entorno, admin):
    app, bd = entorno
    for _ in range(5):
        assert entrar(app, "ana.op", "equivocada-equivocada")[1].status_code == 401
    _, r = entrar(app, "ana.op", "Radiador-Azul-Hilux-86")                   # ni con la correcta
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0
    assert "BLOQUEO" in eventos(bd, "ana.op")

    uid = next(u["id"] for u in admin.get("/api/v1/usuarios").json() if u["usuario"] == "ana.op")
    assert admin.post(f"/api/v1/usuarios/{uid}/desbloquear").status_code == 204
    assert entrar(app, "ana.op", "Radiador-Azul-Hilux-86")[1].status_code == 200


def test_05_roles_y_permisos(entorno, admin):
    app, _ = entorno
    ana, _ = entrar(app, "ana.op", "Radiador-Azul-Hilux-86")
    assert ana.get("/api/v1/usuarios").status_code == 403                    # un operador no administra usuarios
    uid = ana.get("/api/v1/sesion").json()["usuario"]["id"]

    r = admin.patch(f"/api/v1/usuarios/{uid}", json={"roles": ["OPERADOR", "FOTOS"], "permisos": ["VER_ANALISIS_VENTAS"]})
    assert r.status_code == 200 and r.json()["roles"] == ["FOTOS", "OPERADOR"] and r.json()["permisos"] == ["VER_ANALISIS_VENTAS"]
    assert ana.get("/api/v1/sesion").json()["usuario"]["permisos"] == ["VER_ANALISIS_VENTAS"]  # se ve en la siguiente petición

    yo = admin.get("/api/v1/sesion").json()["usuario"]["id"]
    assert admin.patch(f"/api/v1/usuarios/{yo}", json={"roles": ["OPERADOR"]}).status_code == 409
    assert admin.patch(f"/api/v1/usuarios/{yo}", json={"activo": False}).status_code == 409


def test_06_desactivar_cierra_sus_sesiones_y_la_auditoria_no_guarda_secretos(entorno, admin):
    app, bd = entorno
    ana, _ = entrar(app, "ana.op", "Radiador-Azul-Hilux-86")
    uid = ana.get("/api/v1/sesion").json()["usuario"]["id"]
    assert admin.patch(f"/api/v1/usuarios/{uid}", json={"activo": False}).status_code == 200
    assert ana.get("/api/v1/sesion").status_code == 401
    assert entrar(app, "ana.op", "Radiador-Azul-Hilux-86")[1].status_code == 401

    r = admin.post(f"/api/v1/usuarios/{uid}/restablecer")
    assert r.status_code == 200 and len(r.json()["password_temporal"]) == 19
    with psycopg.connect(bd) as c:
        filas = c.execute("select antes, despues, actor from audit.auditoria_evento where entidad = 'app.usuario'").fetchall()
    assert filas and all("password_hash" not in (a or {}) and "password_hash" not in (d or {}) for a, d, _ in filas)
    admin_id = admin.get("/api/v1/sesion").json()["usuario"]["id"]
    assert any(actor == str(admin_id) for _, _, actor in filas)


def test_07_preferencias_del_filtro_global(admin):
    assert admin.get("/api/v1/preferencias").json() == {"cat": "25", "linea": "IMPORTADO"}
    assert admin.put("/api/v1/preferencias", json={"cat": "18", "linea": "FABRICADO"}).status_code == 200
    assert admin.get("/api/v1/preferencias").json() == {"cat": "18", "linea": "FABRICADO"}
    assert admin.put("/api/v1/preferencias", json={"cat": "99", "linea": "FABRICADO"}).status_code == 422


def test_08_cerrar_sesion(entorno, admin):
    assert admin.delete("/api/v1/sesion").status_code == 204
    assert admin.get("/api/v1/sesion").status_code == 401
