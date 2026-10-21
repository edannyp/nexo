"""Staging con una fila por artículo y lote (migraciones 0013 y 0015): el ETL solo agrega filas, marcas y modelos se validan con los del mismo
lote, un lote no se procesa dos veces y Nexo conserva los últimos lotes procesados."""

import json

import psycopg
import pytest

from .apoyo import art, articulo, cargar


def lote_crudo(c, marcas: list[tuple[str, str]], filas: list[dict]) -> int:
    lote = c.execute("insert into staging.lote (completo) values (false) returning lote_id").fetchone()[0]
    for codigo, nombre in marcas:
        c.execute("insert into staging.sap_marca values (%s, %s, %s)", (codigo, nombre, lote))
    for f in filas:
        cols = list(f) + ["datos_sap", "extraido_en", "lote_id"]
        c.execute(f"insert into staging.articulo_sap ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})",
                  list(f.values()) + [json.dumps({"ItemCode": f["item_code"]}), "now()", lote])
    return lote


def test_el_mismo_articulo_en_varios_lotes(conn):
    cargar(conn, [articulo("RAD00501")])
    r = cargar(conn, [articulo("RAD00501", descripcion="RADIADOR CAMBIADO")])
    assert r["actualizados"] == 1 and art(conn, "RAD00501")["descripcion"] == "RADIADOR CAMBIADO"
    assert conn.execute("select count(*) from staging.articulo_sap where item_code = 'RAD00501'").fetchone()[0] == 2


def test_la_marca_se_valida_con_las_del_mismo_lote(conn):
    lote = lote_crudo(conn, [("00117", "TOYOTA")], [articulo("RAD00502", marca_vehiculo_codigo="117")])
    conn.execute("select app.fn_procesar_staging(%s)", (lote,))
    assert art(conn, "RAD00502")["marca_vehiculo"] == "TOYOTA"
    lote = lote_crudo(conn, [("00049", "ISUZU")], [articulo("RAD00502", marca_vehiculo_codigo="117")])   # este lote no trae TOYOTA
    conn.execute("select app.fn_procesar_staging(%s)", (lote,))
    assert art(conn, "RAD00502")["marca_vehiculo_codigo"] is None                                   # no usa marcas de otro lote


def test_un_lote_no_se_procesa_dos_veces(conn):
    lote = lote_crudo(conn, [], [articulo("RAD00503")])
    conn.execute("select app.fn_procesar_staging(%s)", (lote,))
    with pytest.raises(psycopg.errors.RaiseException, match="LOTE_YA_PROCESADO"):
        conn.execute("select app.fn_procesar_staging(%s)", (lote,))


def test_se_conservan_los_ultimos_lotes_procesados(conn):
    conservar = int(conn.execute("select valor::int from meta.parametro where clave = 'etl.lotes_conservados'").fetchone()[0])
    for _ in range(conservar + 3):
        cargar(conn, [articulo("RAD00504")])
    con_filas = conn.execute("select count(distinct lote_id) from staging.articulo_sap").fetchone()[0]
    assert con_filas == conservar
    assert conn.execute("select count(*) from staging.lote where procesado_en is not null").fetchone()[0] >= conservar + 3


def test_los_lotes_sin_procesar_tambien_se_limpian(conn):
    conservar = int(conn.execute("select valor::int from meta.parametro where clave = 'etl.lotes_conservados'").fetchone()[0])
    abandonado = lote_crudo(conn, [], [articulo("RAD00505")])               # el ETL escribió y nunca llamó a fn_procesar_staging
    cargar(conn, [articulo("RAD00505")])
    reciente = lote_crudo(conn, [], [articulo("RAD00505")])                 # un fallo reciente se conserva para diagnosticarlo
    filas = lambda lote: conn.execute("select count(*) from staging.articulo_sap where lote_id = %s", (lote,)).fetchone()[0]
    assert filas(abandonado) == 1
    for _ in range(conservar - 1):
        cargar(conn, [articulo("RAD00505")])
    assert filas(abandonado) == 0 and filas(reciente) == 1                # dentro de la ventana de lotes conservados
    cargar(conn, [articulo("RAD00505")])
    assert filas(reciente) == 0                                             # ya quedó fuera de la ventana
    assert conn.execute("select count(*) from staging.lote where lote_id = %s", (abandonado,)).fetchone()[0] == 1


def test_datos_sap_se_actualiza_aunque_no_cambie_la_huella(conn):
    lote = lote_crudo(conn, [], [articulo("RAD00506")])
    conn.execute("select app.fn_procesar_staging(%s)", (lote,))
    lote = conn.execute("insert into staging.lote (completo) values (false) returning lote_id").fetchone()[0]
    f = articulo("RAD00506")
    cols = list(f) + ["datos_sap", "extraido_en", "lote_id"]
    conn.execute(f"insert into staging.articulo_sap ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})",
                 list(f.values()) + [json.dumps({"ItemCode": "RAD00506", "U_ID_Aces": None}), "now()", lote])
    r = conn.execute("select app.fn_procesar_staging(%s)", (lote,)).fetchone()[0]
    assert r["sin_cambios"] == 1
    assert art(conn, "RAD00506")["datos_sap"] == {"ItemCode": "RAD00506", "U_ID_Aces": None}
