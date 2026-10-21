"""ETL de SAP con foto completa (migración 0012): lo que ya no viene se inactiva como NO_EN_SAP y se reactiva si vuelve; un lote al
que le faltan demasiados se rechaza entero; un cambio en SAP de un artículo Por validar lo regresa a Pendiente."""

import psycopg
import pytest

from .apoyo import art, articulo, cargar, completar, crear_usuario, transicionar

CODIGOS = [f"RAD00{400 + i}" for i in range(20)]


def foto(*, sin=(), **cambios):
    """Todos los artículos de la base de prueba, menos `sin`; `cambios` = {item_code: {campo: valor}}."""
    return [articulo(c, **cambios.get(c, {})) for c in CODIGOS if c not in sin]


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, foto(), completo=True)
        ids = {u: crear_usuario(c, u, r) for u, r in (("op1", "OPERADOR"), ("sup1", "SUPERVISOR"))}
    return bd, ids


def test_01_foto_completa_sin_faltantes(entorno):
    bd, _ = entorno
    with psycopg.connect(bd, autocommit=True) as c:
        r = cargar(c, foto(), completo=True)
    assert (r["sin_cambios"], r["no_en_sap"], r["inactivados"]) == (20, 0, 0)


def test_02_lo_que_no_viene_se_inactiva_y_vuelve_si_reaparece(entorno):
    bd, ids = entorno
    with psycopg.connect(bd, autocommit=True) as c:
        c.execute("select app.fn_reservar((select id from app.articulo where item_code = 'RAD00401'), %s)", (ids["op1"],))
        r = cargar(c, foto(sin=("RAD00401", "RAD00402")), completo=True)
        assert r["no_en_sap"] == 2
        a = art(c, "RAD00401")
        assert (a["activo"], a["motivo_inactivo"], a["asignado_a"]) == (False, "NO_EN_SAP", None)    # y se libera la reserva
        motivo = c.execute("""select motivo from audit.bitacora_articulo where tipo = 'INACTIVADO'
                              and articulo_id = %s""", (a["id"],)).fetchone()[0]
        assert motivo == "NO_EN_SAP"
        r = cargar(c, foto(), completo=True)                                     # reaparecen en SAP
        assert (r["activados"], r["no_en_sap"]) == (2, 0)
        assert art(c, "RAD00401")["activo"] and art(c, "RAD00401")["motivo_inactivo"] is None


def test_03_un_lote_al_que_le_faltan_demasiados_se_rechaza_entero(entorno):
    bd, _ = entorno
    with psycopg.connect(bd, autocommit=True) as c:
        antes = c.execute("select count(*) from app.articulo where activo").fetchone()[0]
        with pytest.raises(psycopg.errors.RaiseException, match="LOTE_INCOMPLETO"):
            cargar(c, foto(sin=CODIGOS[:12], RAD00419={"descripcion": "CAMBIO QUE NO DEBE QUEDAR"}), completo=True)
        assert c.execute("select count(*) from app.articulo where activo").fetchone()[0] == antes
        assert art(c, "RAD00419")["descripcion"] != "CAMBIO QUE NO DEBE QUEDAR"     # nada a medias
        assert c.execute("select count(*) from staging.lote where procesado_en is null").fetchone()[0] == 1


def test_04_un_lote_parcial_no_inactiva_nada(entorno):
    bd, _ = entorno
    with psycopg.connect(bd, autocommit=True) as c:
        r = cargar(c, foto(sin=CODIGOS[:15]))                                   # completo = False
    assert (r["no_en_sap"], r["inactivados"]) == (0, 0)


def test_05_cambio_en_sap_de_un_por_validar_lo_regresa_a_pendiente(entorno):
    bd, ids = entorno
    with psycopg.connect(bd, autocommit=True) as c:
        for item in ("RAD00410", "RAD00411"):
            completar(c, item, ids["op1"])
            assert transicionar(c, item, "POR_VALIDAR", "USUARIO", ids["op1"]) == "POR_VALIDAR"
        r = cargar(c, foto(RAD00410={"descripcion": "RADIADOR CORREGIDO EN SAP"}), completo=True)
        assert r["reabiertos"] == 1
        assert art(c, "RAD00410")["estado"] == "PENDIENTE" and art(c, "RAD00411")["estado"] == "POR_VALIDAR"
        motivo = c.execute("""select motivo from audit.bitacora_articulo where tipo = 'TRANSICION' and articulo_id = %s
                              order by id desc limit 1""", (art(c, "RAD00410")["id"],)).fetchone()[0]
        assert motivo == "HASH_CAMBIO"
