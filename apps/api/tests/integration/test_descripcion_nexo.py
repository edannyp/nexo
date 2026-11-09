"""Descripción armada por Nexo (migración 0017, ADR 0027): patrón de SAP sin abreviar a partir del vehículo principal, recalculada
sola salvo que una persona la ajuste."""

from .apoyo import art, articulo, cargar, crear_usuario


def principal(c, item_code: str, anios: range, marca: str, modelo: str, motor: str | None = None) -> None:
    a = art(c, item_code)["id"]
    for i, anio in enumerate(anios):
        c.execute("""insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, sub_model_id, engine_config_id, origen,
                                                          confirmado_por, confirmado_en, es_principal, make_id, model_id, anio,
                                                          marca, modelo, motor)
                     values (%s, %s, 5, 7, 'MANUAL', (select min(id) from app.usuario), now(), true, 1, 1, %s, %s, %s, %s)""",
                  (a, 800000 + anio * 10 + i, anio, marca, modelo, motor))


def test_01_patron_de_sap_desde_el_vehiculo_principal(conn):
    crear_usuario(conn, "d_op", "OPERADOR")
    cargar(conn, [articulo("RAD00701", transmision="MT"),
                  articulo("RAD00702", subcategoria_codigo="2502", subcategoria_nombre="FABRICADOS",
                           material_descripcion="COBRE LATON"),
                  articulo("CON00703", categoria_codigo="07", subcategoria_codigo="0701", transmision="AT")])
    assert art(conn, "RAD00701")["descripcion_nexo"] is None                     # sin vehículo principal todavía
    principal(conn, "RAD00701", range(2005, 2016), "Toyota", "Hilux", "2.5L L4 2KD · Diésel")
    assert art(conn, "RAD00701")["descripcion_nexo"] == "RADIADOR TOYOTA HILUX M 05/15 2.5L MT"
    principal(conn, "RAD00702", range(2014, 2015), "Kenworth", "T600A")
    assert art(conn, "RAD00702")["descripcion_nexo"] == "RADIADOR KENWORTH T600A M 14 COBRE LATON"
    principal(conn, "CON00703", range(2006, 2012), "Honda", "Civic", "1.8L L4 R18A1 · Gasolina")
    assert art(conn, "CON00703")["descripcion_nexo"] == "CONDENSADOR HONDA CIVIC M 06/11 1.8L AT"


def test_02_se_recalcula_si_cambia_lo_que_la_forma(conn):
    conn.execute("update app.articulo set transmision = 'AUTOMATICA' where item_code = 'RAD00701'")
    assert art(conn, "RAD00701")["descripcion_nexo"] == "RADIADOR TOYOTA HILUX M 05/15 2.5L AT"
    a = art(conn, "RAD00701")["id"]
    conn.execute("update app.articulo_aplicacion set es_principal = false where articulo_id = %s", (a,))
    assert art(conn, "RAD00701")["descripcion_nexo"] is None                     # sin principal no se inventa


def test_03_ajustada_a_mano_queda_fija_hasta_volver_a_la_automatica(conn):
    a = art(conn, "RAD00702")["id"]
    conn.execute("update app.articulo set descripcion_nexo_manual = true, descripcion_nexo = 'RADIADOR KENWORTH T600A ESPECIAL' "
                 "where id = %s", (a,))
    conn.execute("update app.articulo_aplicacion set anio = 2015 where articulo_id = %s", (a,))
    assert art(conn, "RAD00702")["descripcion_nexo"] == "RADIADOR KENWORTH T600A ESPECIAL"
    conn.execute("update app.articulo set descripcion_nexo_manual = false where id = %s", (a,))
    assert art(conn, "RAD00702")["descripcion_nexo"] == "RADIADOR KENWORTH T600A M 15 COBRE LATON"
