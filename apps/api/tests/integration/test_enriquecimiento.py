"""Nexo enriquecimiento: requisitos para revisión, atributos SAP, equivalencias y herencia, fotos y verificación, auditoría,
código equivalente de fabricados.

Par real de SAP (2026-10-15): RAD00253 (importado, Volvo S40) y su fabricado RLT00496 (U_CodAnterior = RAD00253).
"""

import psycopg
import pytest

from .apoyo import art, articulo, cargar, crear_usuario, falla, transicionar

ARTICULOS = [
    articulo("RAD00253", descripcion="RADIADOR VOLVO S40 M 95/98 1.6 MT", marca_vehiculo_codigo="00121",
             anio_desde=1995, anio_hasta=1998, transmision="MT",
             panal_alto=37.5, panal_alto_unidad=2, panal_largo=64.8, panal_largo_unidad=2, panal_ancho=2.6, panal_ancho_unidad=2,
             filas_panal=2, material_panal="Aluminum", material_tanque="0", tipo_flujo="Cross Flow", entrada_diametro="35,5mm",
             tipo_panal="C", dimension_tanque="545*54.5"),
    articulo("RLT00496", descripcion="RAD. VOLVO S40 M 95/98 1.6 M/03 A-RLT", subcategoria_codigo="2502",
             subcategoria_nombre="FABRICADOS", codigo_anterior="RAD00253", marca_vehiculo_codigo="00121"),
    articulo("RLT00573", descripcion="RAD. TOYOTA HILUX 2.4 M/03 A-RLT", subcategoria_codigo="2502",
             subcategoria_nombre="FABRICADOS", codigo_anterior="Z3-4667", marca_vehiculo_codigo="00117"),
    articulo("INT00048", descripcion="INTERCOOLER PRUEBA", categoria_codigo="18", subcategoria_codigo="1801"),
]


def aid(c, item_code: str) -> int:
    return c.execute("select id from app.articulo where item_code = %s", (item_code,)).fetchone()[0]


def requisitos(c, item_code: str) -> list[str]:
    return c.execute("select app.fn_requisitos_por_validar(%s)", (aid(c, item_code),)).fetchone()[0]


@pytest.fixture(scope="module")
def u(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, ARTICULOS)
        return {"op": crear_usuario(c, "e_op", "OPERADOR"), "sup": crear_usuario(c, "e_sup", "SUPERVISOR"),
                "sup2": crear_usuario(c, "e_sup2", "SUPERVISOR"), "fotos": crear_usuario(c, "e_fotos", "FOTOS")}


def test_01_requisitos_explican_lo_que_falta(conn, u):
    falta = requisitos(conn, "RAD00253")
    assert "APLICACION_O_EMPAREJAMIENTO" in falta and "ATRIBUTO:Core Height" in falta
    assert "EQUIVALENTE_IMPORTADO" not in requisitos(conn, "RLT00496")  # la equivalencia no bloquea (pregunta 24)
    falla(conn, "REQUISITOS_INCOMPLETOS", transicionar, "RAD00253", "POR_VALIDAR", "USUARIO", u["op"])


def test_02_atributos_sap_son_sugerencia_hasta_confirmar(conn, u):
    a = aid(conn, "RAD00253")
    n = conn.execute("select app.fn_precargar_atributos_sap(%s)", (a,)).fetchone()[0]
    assert n == 10                         # medidas, filas, material panal, flujo, diámetro, tipo panal, tanque; '0' = vacío
    sap = {r[0]: r[1:] for r in conn.execute(
        "select paid, valor_num, uom_code, valid_value_id, origen, confirmado_por from app.articulo_atributo where articulo_id = %s", (a,))}
    assert sap[267] == (375, "MM", None, "SAP", None)                    # 37,5 cm → mm
    assert sap[302][2] == 203 and sap[7448][2] == 391                    # Aluminum, Cross Flow (valores PAdb)
    assert sap[570][:2] == (35.5, "MM")                                  # '35,5mm' → 35.5 MM
    assert (sap[270][:2], sap[316][:2]) == ((545, "MM"), (54.5, "MM"))  # dimensión tanques 545*54.5
    assert conn.execute("select valor_texto from app.articulo_atributo where articulo_id = %s and paid = 3664", (a,)).fetchone()[0] == "C"
    assert "ATRIBUTO:Core Height" in requisitos(conn, "RAD00253")         # sugerido no cuenta
    etiquetas = dict(conn.execute("select paid, etiqueta from meta.atributo_config where part_terminology_id = 2172").fetchall())
    assert (etiquetas[269], etiquetas[268]) == ("Largo", "Ancho")         # vocabulario del negocio

    conn.execute("update app.articulo_atributo set confirmado_por = %s, confirmado_en = now() where articulo_id = %s", (u["op"], a))
    assert requisitos(conn, "RAD00253") == ["APLICACION_O_EMPAREJAMIENTO", "ATRIBUTO:Tank Material"]
    conn.execute("update meta.atributo_config set obligatorio = false where part_terminology_id = 2172 and paid = 305")
    assert requisitos(conn, "RAD00253") == ["APLICACION_O_EMPAREJAMIENTO"]  # opcional: ya no bloquea
    conn.execute("update meta.atributo_config set obligatorio = true where part_terminology_id = 2172 and paid = 305")
    assert "ATRIBUTO:Tank Material" in requisitos(conn, "RAD00253")
    conn.execute("insert into app.articulo_atributo (articulo_id, paid, valid_value_id, origen, confirmado_por, confirmado_en) "
                 "values (%s, 305, 890, 'MANUAL', %s, now())", (a, u["op"]))   # el operador captura lo que falta
    assert requisitos(conn, "RAD00253") == ["APLICACION_O_EMPAREJAMIENTO"]


def test_03_aplicaciones_vehiculo_o_equipo(conn, u):
    a = aid(conn, "RAD00253")
    ins = ("insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, equipment_base_id, sub_model_id, engine_config_id, origen, "
           "parte_id, confirmado_por, confirmado_en) values (%s, %s, %s, %s, %s, 'CONSOLIDACION', 7001, %s, now())")
    for bv in (5001995, 5001996, 1000000007):                            # AutoCare y MercadoExterno (≥ 1e9)
        conn.execute(ins, (a, bv, None, 20, 4704, u["op"]))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(ins, (a, 5001997, 700001, None, None, u["op"]))     # vehículo y equipo a la vez
    with pytest.raises(psycopg.errors.CheckViolation, match="aplicacion_vehiculo_completa"):
        conn.execute(ins, (a, 5001997, None, None, 4704, u["op"]))       # vehículo confirmado sin submodelo (decisión UX 4)
    conn.execute(ins, (a, None, 700001, None, None, u["op"]))            # equipo: no lleva submodelo ni motor
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, (a, 5001995, None, 20, 4704, u["op"]))         # duplicada
    conn.execute("insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por) "
                 "values (%s, 7001, true, 'CONSOLIDACION', %s)", (a, u["op"]))
    with pytest.raises(psycopg.errors.UniqueViolation):                  # solo una parte principal
        conn.execute("insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por) "
                     "values (%s, 7002, true, 'CONSOLIDACION', %s)", (a, u["op"]))
    assert requisitos(conn, "RAD00253") == []
    assert transicionar(conn, "RAD00253", "POR_VALIDAR", "USUARIO", u["op"]) == "POR_VALIDAR"
    assert transicionar(conn, "RAD00253", "VALIDADO", "USUARIO", u["sup"]) == "VALIDADO"


def test_04_equivalencia_y_herencia(conn, u):
    ins = "insert into app.articulo_equivalencia (fabricado_id, importado_id, origen) values (%s, %s, 'SAP_COD_ANTERIOR')"
    with pytest.raises(psycopg.Error, match="FABRICADO → IMPORTADO"):
        conn.execute(ins, (aid(conn, "RAD00253"), aid(conn, "RLT00496")))  # al revés
    with pytest.raises(psycopg.Error, match="categorías distintas"):
        conn.execute(ins, (aid(conn, "RLT00496"), aid(conn, "INT00048")))  # radiador ↔ intercooler
    conn.execute(ins, (aid(conn, "RLT00496"), aid(conn, "RAD00253")))
    falla(conn, "SIN_EQUIVALENTE_CONFIRMADO",
          lambda c: c.execute("select app.fn_heredar_de_equivalente(%s, %s)", (aid(c, "RLT00496"), u["op"])))

    conn.execute("update app.articulo_equivalencia set estado = 'CONFIRMADA', confirmado_por = %s, confirmado_en = now() "
                 "where fabricado_id = %s", (u["op"], aid(conn, "RLT00496")))
    r = conn.execute("select app.fn_heredar_de_equivalente(%s, %s)", (aid(conn, "RLT00496"), u["op"])).fetchone()[0]
    assert r["partes"] == 1 and r["aplicaciones_sugeridas"] == 4             # 3 vehículos + 1 equipo
    f = aid(conn, "RLT00496")
    sugeridas = conn.execute("select count(*) from app.articulo_aplicacion where articulo_id = %s and origen = 'HEREDADO_EQUIVALENTE' "
                             "and confirmado_por is null", (f,)).fetchone()[0]
    assert sugeridas == 4                                                # el operador las confirma
    falta = requisitos(conn, "RLT00496")
    assert "APLICACION_O_EMPAREJAMIENTO" not in falta                   # heredó la parte


def test_05_foto_nueva_en_validado_crea_verificacion(conn, u):
    a = aid(conn, "RAD00253")
    img = conn.execute("insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto, subida_por) values "
                       "(%s, 'PROPIA', 'rlt-dru', 'imagenes_inventario/25_RADIADORES/RAD00253/RAD00253_1.webp', %s) returning id",
                       (a, u["fotos"])).fetchone()[0]
    tarea = conn.execute("select id, origen, detalle ->> 'imagen_id' from app.tarea_verificacion where articulo_id = %s and estado = 'ABIERTA'",
                         (a,)).fetchone()
    assert tarea[1] == "NUEVA_FOTO" and int(tarea[2]) == img
    with pytest.raises(psycopg.Error, match="ROL_INSUFICIENTE"):
        conn.execute("select app.fn_resolver_verificacion(%s, %s, 'CONFORME')", (tarea[0], u["op"]))
    conn.execute("select app.fn_resolver_verificacion(%s, %s, 'CONFORME')", (tarea[0], u["sup"]))
    assert conn.execute("select validada from app.articulo_imagen where id = %s", (img,)).fetchone()[0] is True
    assert art(conn, "RAD00253")["estado"] == "VALIDADO"                  # conforme: no cambia el estado


def test_06_verificacion_con_hallazgo_reabre(conn, u):
    assert conn.execute("select app.fn_generar_muestreo(10, 1::smallint)").fetchone()[0] >= 1
    tarea = conn.execute("select t.id from app.tarea_verificacion t join app.articulo a on a.id = t.articulo_id "
                         "where a.item_code = 'RAD00253' and t.estado = 'ABIERTA' and t.origen = 'MUESTREO'").fetchone()[0]
    with pytest.raises(psycopg.errors.CheckViolation):                   # hallazgo sin nota
        conn.execute("select app.fn_resolver_verificacion(%s, %s, 'CON_HALLAZGO')", (tarea, u["sup2"]))
    conn.execute("select app.fn_resolver_verificacion(%s, %s, 'CON_HALLAZGO', 'Año 1998 no coincide con la foto')", (tarea, u["sup2"]))
    a = art(conn, "RAD00253")
    assert a["estado"] == "PENDIENTE"
    motivo = conn.execute("select motivo from audit.bitacora_articulo where articulo_id = %s order by id desc limit 1", (a["id"],)).fetchone()[0]
    assert motivo == "VERIFICACION"


def test_07_auditoria_guarda_antes_y_despues(conn, u):
    a = aid(conn, "RAD00253")
    with conn.transaction():
        conn.execute("select set_config('app.usuario_id', %s, true)", (str(u["op"]),))
        conn.execute("delete from app.articulo_aplicacion where articulo_id = %s and base_vehicle_id = 1000000007", (a,))
    actor, antes = conn.execute("select actor, antes from audit.auditoria_evento where entidad = 'app.articulo_aplicacion' "
                                "and accion = 'DELETE' order by id desc limit 1").fetchone()
    assert actor == str(u["op"]) and antes["base_vehicle_id"] == 1000000007


def revision(c, item_code: str) -> dict:
    cur = c.execute("select * from app.v_revision_fabricados where item_code = %s", (item_code,))
    return dict(zip([d.name for d in cur.description], cur.fetchone(), strict=True))


def capturar_codigo(c, item_code: str, codigo, usuario_id: int) -> None:
    with c.transaction():
        c.execute("select set_config('app.usuario_id', %s, true)", (str(usuario_id),))
        c.execute("update app.articulo set codigo_equivalente = %s where item_code = %s", (codigo, item_code))


def test_08_codigo_equivalente_se_valida_con_foto(conn, u):
    f = aid(conn, "RLT00573")
    assert revision(conn, "RLT00573")["estado_codigo"] == "SIN_CODIGO"

    capturar_codigo(conn, "RLT00573", "Z3-4667", u["op"])                 # código de proveedor: texto libre
    r = revision(conn, "RLT00573")
    assert (r["codigo_equivalente"], r["codigo_equivalente_por"], r["estado_codigo"]) == ("Z3-4667", u["op"], "ESPERA_FOTO")
    assert conn.execute("select count(*) from app.articulo_equivalencia where fabricado_id = %s", (f,)).fetchone()[0] == 0

    capturar_codigo(conn, "RLT00573", " rad00253 ", u["op"])              # ItemCode de un importado: se sugiere la equivalencia
    assert revision(conn, "RLT00573")["codigo_equivalente"] == "RAD00253"
    assert conn.execute("select origen, estado from app.articulo_equivalencia where fabricado_id = %s", (f,)).fetchone() == ("MANUAL", "SUGERIDA")

    validar = "select app.fn_validar_codigo_equivalente(%s, %s)"
    falla(conn, "ROL_INSUFICIENTE", lambda c: c.execute(validar, (f, u["op"])))
    falla(conn, "SIN_FOTO_VALIDADA", lambda c: c.execute(validar, (f, u["sup"])))

    conn.execute("insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto, subida_por, validada, validada_por, validada_en) "
                 "values (%s, 'PROPIA', 'rlt-dru', 'imagenes_inventario/25_RADIADORES/RLT00573/RLT00573_1.webp', %s, true, %s, now())",
                 (f, u["fotos"], u["sup"]))
    assert revision(conn, "RLT00573")["estado_codigo"] == "LISTO_PARA_VALIDAR"
    conn.execute(validar, (f, u["sup"]))
    assert revision(conn, "RLT00573")["estado_codigo"] == "VALIDADO"

    capturar_codigo(conn, "RLT00573", "Z3-4667", u["op"])                 # cambiar el código invalida la validación
    r = revision(conn, "RLT00573")
    assert r["estado_codigo"] == "LISTO_PARA_VALIDAR" and r["codigo_equivalente_validado_por"] is None


def test_09_catalogo_configurable_de_atributos(conn, u):
    rad, inter = aid(conn, "RAD00253"), aid(conn, "INT00048")
    ins = "insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, valid_value_id, valor_texto, origen) values (%s, %s, %s, %s, %s, %s, 'MANUAL')"
    falla(conn, "ATRIBUTO_NO_HABILITADO", lambda c: c.execute(ins, (inter, 267, 300, "MM", None, None)))   # intercooler sin configurar
    falla(conn, "ATRIBUTO_NO_HABILITADO", lambda c: c.execute(ins, (rad, 3683, None, None, None, "Yes")))  # PAdb lo admite, no habilitado
    falla(conn, "VALOR_NO_VALIDO", lambda c: c.execute(ins, (rad, 302, None, None, 999, None)))
    falla(conn, "REQUIERE_UOM", lambda c: c.execute(ins, (rad, 267, 400, None, None, None)))

    # El administrador habilita un atributo más (sin migración) y ya se puede capturar; es opcional
    conn.execute("insert into meta.atributo_config (part_terminology_id, paid, nombre, habilitado, etiqueta, grupo, orden) "
                 "values (2172, 3683, 'Radiator Cap Included', true, 'Incluye tapón', 'INCLUYE', 12)")
    conn.execute(ins, (rad, 3683, None, None, None, "Yes"))
    ficha = {r[0]: r[1:] for r in conn.execute(
        "select etiqueta, obligatorio, confirmado from app.v_ficha_atributo where articulo_id = %s", (rad,))}
    assert ficha["Incluye tapón"] == (False, False) and ficha["Largo"] == (True, True) and len(ficha) == 12
    assert "ATRIBUTO:Radiator Cap Included" not in requisitos(conn, "RAD00253")

    # Deshabilitar un atributo: no se exige ni se precarga
    conn.execute("update meta.atributo_config set habilitado = false, obligatorio = false where part_terminology_id = 2172 and paid = 570")
    f = aid(conn, "RLT00573")
    conn.execute("update app.articulo set entrada_diametro = '40mm' where id = %s", (f,))
    conn.execute("select app.fn_precargar_atributos_sap(%s)", (f,))
    assert conn.execute("select count(*) from app.articulo_atributo where articulo_id = %s and paid = 570", (f,)).fetchone()[0] == 0
    assert not any(r.startswith("ATRIBUTO:Inlet Diameter") for r in requisitos(conn, "RLT00573"))
    with pytest.raises(psycopg.errors.CheckViolation):                   # obligatorio exige habilitado
        conn.execute("update meta.atributo_config set obligatorio = true where part_terminology_id = 2172 and paid = 570")
    assert conn.execute("select count(*) from audit.auditoria_evento where entidad = 'meta.atributo_config'").fetchone()[0] >= 2
