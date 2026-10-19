"""Nexo núcleo: carga de staging, normalización, hash, inactivos, calidad SAP y máquina de estados.

Escenario secuencial con artículos reales de SAP (valores de la exploración del 2026-10-15).
"""

import psycopg
import pytest

from .apoyo import art, articulo, cargar, completar, falla, transicionar

ARTICULOS = [
    articulo("RAD00003", descripcion="RADIADOR FORD DUTY M 09/13 MT", numero_parte_proveedor="ZC-IS011AT",
             codigo_anterior="13098", marca_vehiculo_codigo="00035", modelo_vehiculo_codigo=71, modelo_vehiculo="HEAVY DUTY",
             anio_desde=2009, anio_hasta=2013, transmision="MT",
             panal_alto=35, panal_alto_unidad=2, panal_largo=65.8, panal_largo_unidad=2, panal_ancho=2.2, panal_ancho_unidad=2,
             tipo_flujo="Cross Flow", entrada_ubicacion="Top Right", incluye_tapon="S", tamano_panal="Pequeño"),
    articulo("RAD00004", descripcion="RADIADOR ISUZU D-MAX DIESEL M 05/10  MT", numero_parte_proveedor="ZC-IS011",
             marca_vehiculo_codigo="49", modelo_vehiculo_codigo=6, modelo_vehiculo="DMAX", anio_desde=2005, anio_hasta=2012,
             transmision="CVT", tamano_panal="Proyecto"),
    articulo("RAD00317", descripcion="RADIADOR TOYOTA 22R COBRE/LATON 945RLT MT", subcategoria_codigo="2502",
             subcategoria_nombre="FABRICADOS", marca_vehiculo_codigo="RLT", codigo_anterior="945RLT"),
    articulo("RLT00010", descripcion="RAD. UNIVERSAL 2 FILAS", subcategoria_codigo="2502", subcategoria_nombre="FABRICADOS",
             marca_vehiculo_codigo="137"),                               # existe en @IGT_MARCAS pero es basura
    articulo("RAD00001", descripcion="RADIADOR BMW 325 06-10 CON REBALSE 2882 INACTIVO", marca_vehiculo_codigo="00010",
             congelado_sap="Y"),
    articulo("RAD00999", descripcion="RADIADOR PRUEBA INACTIVO", marca_vehiculo_codigo="00117", anio_desde=2098, anio_hasta=2002),
    articulo("ABR00001", descripcion="ABRAZADERA 2 PULGADAS", categoria_codigo="01", subcategoria_codigo="0101",
             subcategoria_nombre="AUTOMOTRIZ"),
    articulo("RLT00005", descripcion="RAD. MITSUBISHI L200 A-RLT", subcategoria_codigo="2505", subcategoria_nombre="MODIFICADOS"),
]


@pytest.fixture(scope="module")
def usuarios(bd):
    ids = {}
    with psycopg.connect(bd, autocommit=True) as c:
        for usuario, roles in [("op1", ["OPERADOR"]), ("op2", ["OPERADOR"]), ("sup1", ["SUPERVISOR"]), ("sup2", ["SUPERVISOR"])]:
            uid = c.execute("insert into app.usuario (usuario, nombre, password_hash) values (%s, %s, 'x') returning id",
                            (usuario, usuario)).fetchone()[0]
            for r in roles:
                c.execute("insert into app.usuario_rol values (%s, %s)", (uid, r))
            ids[usuario] = uid
    return ids


def test_01_alta_filtra_y_normaliza(conn):
    res = cargar(conn, ARTICULOS)
    assert res["nuevos"] == 6 and res["descartados"] == 2, res        # abrazadera y MODIFICADOS no entran

    a = art(conn, "RAD00003")
    assert a["estado"] == "PENDIENTE" and a["linea"] == "IMPORTADO" and a["part_terminology_id"] == 2172
    assert (a["panal_alto_mm"], a["panal_largo_mm"], a["panal_ancho_mm"]) == (350, 658, 22)  # cm → mm
    assert a["transmision"] == "MANUAL" and a["tipo_flujo"] == "HORIZONTAL" and a["incluye_tapon"] is True
    assert a["entrada_ubicacion"] == "ARRIBA_DERECHA" and a["marca_vehiculo"] == "FORD"
    assert a["tamano_panal"] == "PEQUENO"                                 # en OITM viene como palabra
    assert a["codigo_anterior"] == ["13098"]

    assert art(conn, "RAD00004")["marca_vehiculo_codigo"] == "00049"     # '49' → 5 dígitos
    assert art(conn, "RAD00004")["descripcion"] == "RADIADOR ISUZU D-MAX DIESEL M 05/10 MT"  # espacios colapsados
    assert art(conn, "RAD00317")["linea"] == "FABRICADO"


def test_02_inactivos_y_calidad(conn):
    assert (art(conn, "RAD00001")["activo"], art(conn, "RAD00001")["motivo_inactivo"]) == (False, "SAP_CONGELADO")
    assert art(conn, "RAD00999")["motivo_inactivo"] == "NOMBRE_INACTIVO"
    rlt = art(conn, "RAD00317")
    assert rlt["marca_vehiculo_codigo"] is None                          # 'RLT' es basura: no se interpreta
    hallazgos = dict(conn.execute("select a.item_code || ':' || h.tipo, h.valor from app.hallazgo_calidad_sap h "
                                  "join app.articulo a on a.id = h.articulo_id").fetchall())
    assert hallazgos["RAD00317:MARCA_INVALIDA"] == "RLT"
    assert art(conn, "RLT00010")["marca_vehiculo_codigo"] is None and hallazgos["RLT00010:MARCA_INVALIDA"] == "137"
    assert "RAD00999:NOMBRE_INACTIVO_SIN_CONGELAR" in hallazgos
    assert hallazgos["RAD00999:ANIOS_INVERTIDOS"] == "2098 > 2002"
    no_reconocidos = dict(conn.execute("select h.campo_sap, h.valor from app.hallazgo_calidad_sap h join app.articulo a on a.id = h.articulo_id "
                                       "where a.item_code = 'RAD00004' and h.tipo = 'VALOR_NO_RECONOCIDO'").fetchall())
    assert no_reconocidos == {"U_transmision": "CVT", "U_Tamanio": "Proyecto"}   # quedan en null y se reportan
    assert art(conn, "RAD00004")["transmision"] is None


def test_03_hash_estable_y_cambios_cosmeticos(conn):
    assert cargar(conn, ARTICULOS)["sin_cambios"] == 6
    cosmetico = [articulo(**{**ARTICULOS[0], "descripcion": "  RADIADOR   FORD DUTY M 09/13 MT ",
                             "panal_alto": 350, "panal_alto_unidad": 1})]   # mismos datos, en mm y con espacios
    assert cargar(conn, cosmetico)["sin_cambios"] == 1


def test_04_comentarios_con_nombre_sap(conn):
    comentario = conn.execute("select col_description('app.articulo'::regclass, attnum) from pg_attribute "
                              "where attrelid = 'app.articulo'::regclass and attname = 'panal_alto_mm'").fetchone()[0]
    assert comentario.startswith("SAP: OITM.SHeight1")


def test_05_reserva_siguiente(conn, usuarios):
    sig = "select (app.fn_tomar_siguiente(%s, '{PENDIENTE}', 1::smallint, 'IMPORTADO')).item_code"
    a1 = conn.execute(sig, (usuarios["op1"],)).fetchone()[0]
    a2 = conn.execute(sig, (usuarios["op2"],)).fetchone()[0]
    assert {a1, a2} == {"RAD00003", "RAD00004"}                          # inactivos y fabricados no salen
    assert conn.execute(sig, (usuarios["op1"],)).fetchone()[0] == a1      # ya tiene uno: se lo devuelve
    assert conn.execute(sig, (usuarios["sup1"],)).fetchone()[0] is None   # bandeja agotada


def test_06_flujo_con_doble_control(conn, usuarios):
    op1, sup1, sup2 = usuarios["op1"], usuarios["sup1"], usuarios["sup2"]
    completar(conn, "RAD00003", op1)
    completar(conn, "RAD00004", sup2, parte_id=5002)
    assert transicionar(conn, "RAD00003", "POR_VALIDAR", "USUARIO", op1) == "POR_VALIDAR"
    assert art(conn, "RAD00003")["asignado_a"] is None                   # al transicionar se libera la reserva
    falla(conn, "ROL_INSUFICIENTE", transicionar, "RAD00003", "VALIDADO", "USUARIO", op1)
    falla(conn, "MOTIVO_OBLIGATORIO", transicionar, "RAD00003", "RECHAZADO", "USUARIO", sup1)
    assert transicionar(conn, "RAD00003", "RECHAZADO", "USUARIO", sup1, "Falta confirmar años") == "RECHAZADO"
    assert transicionar(conn, "RAD00003", "POR_VALIDAR", "USUARIO", op1) == "POR_VALIDAR"
    assert transicionar(conn, "RAD00003", "VALIDADO", "USUARIO", sup1) == "VALIDADO"

    # Un supervisor puede operar, pero no validar su propio envío
    assert transicionar(conn, "RAD00004", "POR_VALIDAR", "USUARIO", sup2) == "POR_VALIDAR"
    falla(conn, "DOBLE_CONTROL", transicionar, "RAD00004", "VALIDADO", "USUARIO", sup2)
    v = art(conn, "RAD00004")["version"]
    falla(conn, "CONFLICTO_VERSION", transicionar, "RAD00004", "VALIDADO", "USUARIO", sup1, version=v - 1)
    assert transicionar(conn, "RAD00004", "VALIDADO", "USUARIO", sup1, version=v) == "VALIDADO"

    falla(conn, "ARTICULO_INACTIVO", transicionar, "RAD00001", "POR_VALIDAR", "USUARIO", op1)
    falla(conn, "TRANSICION_NO_PERMITIDA", transicionar, "RAD00317", "VALIDADO", "USUARIO", sup1)
    assert transicionar(conn, "RAD00003", "SINCRONIZADO", "PROCESO", "PROCESO:SALIDA") == "SINCRONIZADO"


def test_07_cambio_de_hash_reabre_conservando_y_explica(conn):
    cambio = [articulo(**{**ARTICULOS[0], "anio_hasta": 2014})]
    res = cargar(conn, cambio)
    assert res["actualizados"] == 1 and res["reabiertos"] == 1, res
    assert art(conn, "RAD00003")["estado"] == "PENDIENTE"
    detalle, motivo = conn.execute(
        "select detalle, motivo from audit.bitacora_articulo b join app.articulo a on a.id = b.articulo_id "
        "where a.item_code = 'RAD00003' and b.tipo = 'TRANSICION' order by b.id desc limit 1").fetchone()
    assert motivo == "HASH_CAMBIO" and detalle == {"anio_hasta": {"antes": 2013, "despues": 2014}}


def test_08_sale_y_vuelve_al_alcance(conn):
    fuera = [articulo(**{**ARTICULOS[1], "subcategoria_codigo": "2505", "subcategoria_nombre": "MODIFICADOS"})]
    res = cargar(conn, fuera)
    a = art(conn, "RAD00004")
    assert res["inactivados"] == 1 and res["reabiertos"] == 0            # fuera de alcance: no se reabre
    assert (a["activo"], a["motivo_inactivo"], a["estado"]) == (False, "FUERA_DE_ALCANCE", "VALIDADO")

    res = cargar(conn, [ARTICULOS[1]])
    a = art(conn, "RAD00004")
    assert res["activados"] == 1 and a["activo"] and a["estado"] == "PENDIENTE"  # volvió y su hash cambió: se revisa


def test_09_bitacora_completa(conn):
    tipos = [r[0] for r in conn.execute(
        "select b.tipo || coalesce(':' || b.estado_destino, '') from audit.bitacora_articulo b "
        "join app.articulo a on a.id = b.articulo_id where a.item_code = 'RAD00004' order by b.id").fetchall()]
    assert tipos == ["ALTA:PENDIENTE", "TRANSICION:POR_VALIDAR", "TRANSICION:VALIDADO", "DATOS_SAP", "INACTIVADO",
                     "DATOS_SAP", "TRANSICION:PENDIENTE", "ACTIVADO"], tipos
