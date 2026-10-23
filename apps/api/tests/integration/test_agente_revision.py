"""Agente de revisión del catálogo (migración 0011), con el usuario de deploy/sql/usuario-agente-revision-catalogo.sql: qué revisar,
lo validado de cada artículo, cambios de estado y de datos con nota, y que el mismo cambio no vuelva aunque ya se haya resuelto."""

import json
import secrets
from pathlib import Path

import psycopg
import pytest

from .apoyo import articulo, cargar, crear_usuario, validar

SCRIPT = Path(__file__).resolve().parents[4] / "deploy" / "sql" / "usuario-agente-revision-catalogo.sql"


@pytest.fixture(scope="module")
def entorno(bd):
    agente = f"agente_prueba_{secrets.token_hex(3)}"
    with psycopg.connect(bd, autocommit=True) as c:
        c.execute(SCRIPT.read_text().replace(":'clave'", "'x'").replace("agente_revision_catalogo", agente))
        cargar(c, [articulo(f"RAD0030{i}", panal_alto=400, panal_alto_unidad=1, panal_largo=518, panal_largo_unidad=1)
                   for i in range(1, 5)])
        op, sup = crear_usuario(c, "op1", "OPERADOR"), crear_usuario(c, "sup1", "SUPERVISOR")
        validar(c, "RAD00301", op, sup, parte_id=7001)
        validar(c, "RAD00302", op, sup, parte_id=7001)                          # dos artículos usan la misma parte
        validar(c, "RAD00303", op, sup, parte_id=7003)                          # RAD00304 queda pendiente
        a = c.execute("select id from app.articulo where item_code = 'RAD00301'").fetchone()[0]
        c.execute("""insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, sub_model_id, engine_config_id, origen,
                                                          confirmado_por, confirmado_en)
                     values (%s, 10, 5, 7, 'MANUAL', %s, now())""", (a, op))
    return agente, sup


def como(bd, rol):
    c = psycopg.connect(bd, autocommit=True)
    c.execute(f"set role {rol}")
    return c


def registrar(c, cambios) -> dict:
    return c.execute("select app.fn_registrar_cambios_catalogo(%s)", (json.dumps(cambios),)).fetchone()[0]


def tareas(bd) -> list[tuple]:
    with psycopg.connect(bd) as c:
        return c.execute("""select a.item_code, t.detalle ->> 'estado', t.detalle ->> 'nota', t.estado::text
                            from app.tarea_verificacion t join app.articulo a on a.id = t.articulo_id
                            where t.origen = 'CAMBIO_CATALOGO' order by t.id""").fetchall()


def test_01_que_revisar_y_lo_validado(bd, entorno):
    agente, _ = entorno
    with como(bd, agente) as c:
        assert c.execute("select * from app.fn_partes_emparejadas()").fetchall() == [(7001, 2), (7003, 1)]
        filas = c.execute("select * from app.fn_datos_emparejamiento(array[7001, 7003]::bigint[])").fetchall()
    assert [(f[0], f[1]) for f in filas] == [(7001, "RAD00301"), (7001, "RAD00302"), (7003, "RAD00303")]
    parte, item, _, linea, principal, validado_en, _, _, atributos, aplicaciones = filas[0]
    assert (linea, principal, validado_en is not None) == ("IMPORTADO", True, True)
    assert atributos and all("valor_texto" in v or "valor_num" in v for v in atributos.values())   # solo lo confirmado
    assert {"base_vehicle_id": 10, "sub_model_id": 5, "engine_config_id": 7} in aplicaciones   # además del vehículo principal


def test_02_cambio_de_estado_a_todos_los_articulos_de_la_parte(bd, entorno):
    agente, _ = entorno
    with como(bd, agente) as c:
        r = registrar(c, [{"parte_id": 7001, "estado": "FUSIONADA", "fusionada_en_id": 9001}, {"parte_id": 8888, "estado": "NO_EXISTE"}])
        assert r == {"recibidos": 2, "tareas": 2, "repetidos": 0}                 # 8888 no la usa nadie
        assert registrar(c, [{"parte_id": 7001, "estado": "FUSIONADA", "fusionada_en_id": 9001}]) == {
            "recibidos": 1, "tareas": 0, "repetidos": 2}
    assert tareas(bd) == [("RAD00301", "FUSIONADA", None, "ABIERTA"), ("RAD00302", "FUSIONADA", None, "ABIERTA")]


def test_03_datos_que_cambiaron_con_nota_para_un_articulo(bd, entorno):
    agente, _ = entorno
    cambio = {"parte_id": 7003, "estado": "DATOS_CAMBIARON", "item_code": "rad00303", "huella": "h1", "campos": ["267"],
              "nota": "El catálogo ahora dice alto 410 mm; el artículo se validó con 400 mm."}
    with como(bd, agente) as c:
        assert registrar(c, [cambio])["tareas"] == 1
    assert tareas(bd)[-1] == ("RAD00303", "DATOS_CAMBIARON", cambio["nota"], "ABIERTA")


def test_04_lo_resuelto_no_vuelve_y_un_cambio_nuevo_si(bd, entorno):
    agente, sup = entorno
    with psycopg.connect(bd, autocommit=True) as c:                              # el supervisor la revisa: conforme
        t = c.execute("select id from app.tarea_verificacion where detalle ->> 'clave' = 'DATOS_CAMBIARON:h1'").fetchone()[0]
        c.execute("select app.fn_resolver_verificacion(%s, %s, 'CONFORME')", (t, sup))
    base = {"parte_id": 7003, "estado": "DATOS_CAMBIARON", "item_code": "RAD00303", "nota": "El alto cambió otra vez en el catálogo."}
    with como(bd, agente) as c:
        assert registrar(c, [{**base, "huella": "h1"}]) == {"recibidos": 1, "tareas": 0, "repetidos": 1}   # el ciclo cierra
        assert registrar(c, [{**base, "huella": "h2"}])["tareas"] == 1                                   # cambio nuevo: sí


@pytest.mark.parametrize("malo", [
    [{"parte_id": 7001, "estado": "FUSIONADA"}],
    [{"parte_id": "7001", "estado": "NO_EXISTE"}],
    [{"parte_id": 7001, "estado": "OTRO"}],
    [{"parte_id": 7003, "estado": "DATOS_CAMBIARON", "huella": "h", "nota": "corta"}],
    [{"parte_id": 7003, "estado": "DATOS_CAMBIARON", "nota": "Una nota suficientemente larga."}],
    [{"parte_id": 7003, "estado": "NO_EXISTE", "campos": "267"}],
    {"parte_id": 7001},
])
def test_05_formas_invalidas(bd, entorno, malo):
    agente, _ = entorno
    with como(bd, agente) as c, pytest.raises(psycopg.errors.RaiseException, match="CAMBIOS_INVALIDOS"):
        registrar(c, malo)


def test_06_no_toca_nada_mas(bd, entorno):
    agente, _ = entorno
    with como(bd, agente) as c:
        for sql in ("select count(*) from app.articulo_parte", "select count(*) from app.tarea_verificacion",
                    "select count(*) from app.articulo", "select app.fn_procesar_staging(1)",
                    "insert into staging.lote default values"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                c.execute(sql)


def test_07_cambios_distintos_del_mismo_articulo_se_ven_todos(bd, entorno):
    """Con una verificación abierta para un artículo, otro cambio distinto también se registra (no se pierde ni se cuenta como repetido)."""
    agente, _ = entorno
    otro = {"parte_id": 7001, "estado": "DATOS_CAMBIARON", "item_code": "RAD00301", "huella": "z9",
            "nota": "El catálogo quitó el OEM 16400-35090 de esta parte."}
    with como(bd, agente) as c:                                                   # RAD00301 ya tiene abierta la FUSIONADA de 7001
        assert registrar(c, [otro]) == {"recibidos": 1, "tareas": 1, "repetidos": 0}
    abiertas = [t for t in tareas(bd) if t[0] == "RAD00301" and t[3] == "ABIERTA"]
    assert [t[1] for t in abiertas] == ["FUSIONADA", "DATOS_CAMBIARON"]
