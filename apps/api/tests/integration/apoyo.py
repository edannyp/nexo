"""Ayudantes compartidos por las pruebas de integración de Nexo."""

import json

import psycopg
import pytest

MARCAS = [("00010", "BMW"), ("00035", "FORD"), ("00049", "ISUZU"), ("00117", "TOYOTA"), ("00121", "VOLVO"),
          ("00136", "RLT"), ("00137", "UNIVERSAL")]                        # códigos reales de @IGT_MARCAS
MODELOS = [("00035", 71, "HEAVY DUTY", "G"), ("00049", 6, "DMAX", "M")]

BASE = {
    "descripcion": None, "categoria_codigo": "25", "subcategoria_codigo": "2501", "subcategoria_nombre": "IMPORTADOS",
    "material_codigo": "1", "material_descripcion": "PLASTICO ALUMINIO", "numero_parte_proveedor": None,
    "codigo_anterior": None, "marca_vehiculo_codigo": None, "modelo_vehiculo_codigo": None, "modelo_vehiculo": None,
    "anio_desde": None, "anio_hasta": None, "transmision": None, "panal_alto": None, "panal_alto_unidad": None,
    "panal_largo": None, "panal_largo_unidad": None, "panal_ancho": None, "panal_ancho_unidad": None,
    "tipo_flujo": None, "entrada_ubicacion": None, "incluye_tapon": None, "congelado_sap": "N",
}


def articulo(item_code: str, **campos) -> dict:
    return {**BASE, "item_code": item_code, **campos}


def cargar(c: psycopg.Connection, filas: list[dict], completo: bool = False) -> dict:
    """Lo que hace el ETL: un lote en staging y luego fn_procesar_staging. `completo` = foto completa (migración 0012)."""
    lote = c.execute("insert into staging.lote (completo) values (%s) returning lote_id", (completo,)).fetchone()[0]
    for codigo, nombre in MARCAS:
        c.execute("insert into staging.sap_marca values (%s, %s, %s) on conflict (marca_codigo) do update set lote_id = excluded.lote_id",
                  (codigo, nombre, lote))
    for marca, modelo, nombre, tamano in MODELOS:
        c.execute("insert into staging.sap_modelo values (%s, %s, %s, %s, %s) on conflict (marca_codigo, modelo_codigo) "
                  "do update set lote_id = excluded.lote_id", (marca, modelo, nombre, tamano, lote))
    for f in filas:
        cols = list(f) + ["datos_sap", "extraido_en", "lote_id"]
        vals = list(f.values()) + [json.dumps({"ItemCode": f["item_code"]}), "now()", lote]
        set_ = ", ".join(f"{k} = excluded.{k}" for k in cols if k != "item_code")
        c.execute(f"insert into staging.articulo_sap ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))}) "
                  f"on conflict (item_code) do update set {set_}", vals)
    return c.execute("select app.fn_procesar_staging(%s)", (lote,)).fetchone()[0]


def art(c, item_code: str) -> dict:
    cur = c.execute("select * from app.articulo where item_code = %s", (item_code,))
    return dict(zip([d.name for d in cur.description], cur.fetchone(), strict=True))


def transicionar(c, item_code: str, destino: str, actor_tipo: str, actor, motivo=None, version=None):
    return c.execute("select (app.fn_transicionar(id, %s, %s, %s, %s, null, %s)).estado from app.articulo where item_code = %s",
                     (destino, actor_tipo, str(actor), motivo, version, item_code)).fetchone()[0]


def falla(c, contiene: str, fn, *args, **kw):
    with pytest.raises(psycopg.Error) as e:
        fn(c, *args, **kw)
    assert contiene in str(e.value), str(e.value)




def crear_usuario(c, usuario: str, *roles: str) -> int:
    uid = c.execute("insert into app.usuario (usuario, nombre, password_hash) values (%s, %s, 'x') returning id",
                    (usuario, usuario)).fetchone()[0]
    for r in roles:
        c.execute("insert into app.usuario_rol values (%s, %s)", (uid, r))
    return uid


def completar(c, item_code: str, usuario_id: int, parte_id: int = 5001) -> None:
    """Lo que hace el operador antes de enviar a revisión: emparejar y confirmar los atributos obligatorios."""
    aid = c.execute("select id from app.articulo where item_code = %s", (item_code,)).fetchone()[0]
    c.execute("insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por) "
              "values (%s, %s, true, 'CONSOLIDACION', %s) on conflict do nothing", (aid, parte_id, usuario_id))
    c.execute("""insert into app.articulo_atributo (articulo_id, paid, valor_texto, origen, confirmado_por, confirmado_en)
                 select a.id, r.paid, 'confirmado', 'MANUAL', %s, now()
                 from app.articulo a join meta.atributo_config r on r.part_terminology_id = a.part_terminology_id
                 where a.id = %s and r.habilitado and r.obligatorio on conflict (articulo_id, paid) do nothing""", (usuario_id, aid))


def validar(c, item_code: str, operador_id: int, supervisor_id: int, parte_id: int = 5001) -> None:
    """Lleva el artículo a VALIDADO por el camino normal: el operador completa y envía, el supervisor valida."""
    completar(c, item_code, operador_id, parte_id)
    transicionar(c, item_code, "POR_VALIDAR", "USUARIO", operador_id)
    transicionar(c, item_code, "VALIDADO", "USUARIO", supervisor_id)
