"""Errores en formato problem+json (RFC 9457), sin base de datos."""

from fastapi.testclient import TestClient

from nexo_api.main import crear_app

cliente = TestClient(crear_app())


def test_ruta_inexistente_es_problem_json():
    r = cliente.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json() == {"type": "about:blank", "title": "Not Found", "status": 404}


def test_salud_viva_no_necesita_base():
    r = cliente.get("/api/v1/salud")
    assert r.status_code == 200 and r.json()["estado"] == "ok"


def test_openapi_publicado_con_operaciones_legibles_y_unicas():
    rutas = cliente.get("/api/openapi.json").json()["paths"]
    assert {"/api/v1/salud", "/api/v1/salud/lista", "/api/v1/categorias"} <= set(rutas)
    ids = [op["operationId"] for metodos in rutas.values() for op in metodos.values()]
    assert len(ids) == len(set(ids)) and "listar_categorias" in ids


def test_openapi_sin_nombres_de_modelo_duplicados():
    """Dos modelos con el mismo nombre en módulos distintos se publican como `nexo_api__modules__…`: el cliente queda ilegible."""
    esquemas = cliente.get("/api/openapi.json").json()["components"]["schemas"]
    assert not [n for n in esquemas if n.startswith("nexo_api")]
