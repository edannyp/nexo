"""Panorama, calidad SAP, ventas (ADR 0022) e importación de fotos (ADR 0013) contra una base desechable.

ClickHouse y MinIO se sustituyen por fuentes falsas: las pruebas no dependen de sistemas externos.
"""

from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.adapters.clickhouse import Referencia, VentaMes
from nexo_api.auth.dependencias import Permiso, Rol, Usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app
from nexo_api.tareas.fotos import importar_fotos
from nexo_api.tareas.ventas import actualizar_ventas, inicio_ventana

from .apoyo import articulo, cargar, completar, crear_usuario, transicionar


def mes(atras: int) -> date:
    """Primer día del mes `atras` meses antes del mes en curso (1 = el último mes completo)."""
    hoy = date.today()
    total = hoy.year * 12 + hoy.month - 1 - atras
    return date(total // 12, total % 12 + 1, 1)


class VentasFalsas:
    def ventas_mensuales(self, desde):
        # RAD00188 vende 100/mes en el periodo y 80/mes en el anterior; RAD00174 vende 10/mes; RAD00999 no existe en Nexo
        for atras in range(1, 25):
            yield VentaMes("RAD00188", mes(atras), 100 if atras <= 12 else 80)
            yield VentaMes("RAD00174", mes(atras), 10)
            yield VentaMes("RAD00999", mes(atras), 5000)

    def referencias(self):
        yield Referencia("RAD00188", "AX", mes(1))                             # la clase viene de aquí (ADR 0023)
        yield Referencia("RAD00174", "CZ", mes(1))
        yield Referencia("RAD00999", "AX", mes(1))


class FotosFalsas:
    bucket = "rlt-dru"

    def listar(self, prefijo):
        objetos = [
            "imagenes_inventario/25_RADIADORES/RAD00188/RAD00188_2.webp",
            "imagenes_inventario/25_RADIADORES/RAD00188/RAD00188_1.webp",
            "imagenes_inventario/25_RADIADORES/RAD00617_REVISIÓN/foto.webp",   # carpeta que no es un artículo
            "imagenes_inventario/25_RADIADORES/TEST.svg",                     # fuera de la convención
            "imagenes_inventario/01_ABRAZADERA/ABR00001/ABR00001_1.webp",     # categoría fuera de alcance: ni se lista
        ]
        return (o for o in objetos if o.startswith(prefijo))


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [
            articulo("RAD00188", panal_alto=40, panal_alto_unidad=2),
            articulo("RAD00174"),
            articulo("RAD00003", anio_desde=2014, anio_hasta=2009),                       # años invertidos → hallazgo
            articulo("RLT00496", subcategoria_codigo="2502", subcategoria_nombre="FABRICADOS"),
        ])
        op = crear_usuario(c, "pan_op", "OPERADOR")
        sup = crear_usuario(c, "pan_sup", "SUPERVISOR")
        completar(c, "RAD00174", op)
        transicionar(c, "RAD00174", "POR_VALIDAR", "USUARIO", op)
        transicionar(c, "RAD00174", "RECHAZADO", "USUARIO", sup, "Faltan años")
        c.execute("select app.fn_precargar_atributos_sap(id) from app.articulo where item_code = 'RAD00188'")
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    with motor.connect() as c:
        r_ventas = actualizar_ventas(c, VentasFalsas())
    with motor.connect() as c:
        r_fotos = importar_fotos(c, FotosFalsas())
    with motor.connect() as c:
        r_fotos_2 = importar_fotos(c, FotosFalsas())
    return motor, {"op": op, "sup": sup}, r_ventas, (r_fotos, r_fotos_2)


def cliente(motor, roles=(Rol.SUPERVISOR,), permisos=()) -> TestClient:
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: Usuario(99, "x", "X", None, frozenset(roles), frozenset(permisos), False)
    return TestClient(app)


def test_ventana_de_ventas_cubre_dos_periodos_completos():
    assert inicio_ventana(date(2026, 10, 19), 12) == date(2024, 10, 1)
    assert inicio_ventana(date(2026, 1, 5), 3) == date(2025, 7, 1)


def test_actualizar_ventas_solo_guarda_articulos_de_nexo(entorno):
    _, _, r, _ = entorno
    assert r.articulos == 2 and r.filas == 48 and r.referencias == 2      # RAD00999 no existe en Nexo


def test_importar_fotos_es_repetible_y_reporta_anomalias(entorno):
    _, _, _, (primera, segunda) = entorno
    assert (primera.importadas, primera.articulos) == (2, 1)
    assert primera.carpetas_sin_articulo == ["RAD00617_REVISIÓN"]
    assert primera.no_son_imagen == ["imagenes_inventario/25_RADIADORES/TEST.svg"]
    assert (segunda.importadas, segunda.ya_estaban) == (0, 2)


def test_panorama(entorno):
    motor, usuarios, _, _ = entorno
    d = cliente(motor).get("/api/v1/panorama?cat=25&linea=IMPORTADO").json()
    assert d["activos"] == 3
    assert d["por_estado"] == {"PENDIENTE": 2, "POR_VALIDAR": 0, "RECHAZADO": 1, "VALIDADO": 0, "SINCRONIZADO": 0}
    assert d["cobertura"] == {"con_foto": 1, "fotos": 2, "emparejados": 1, "con_aplicacion": 0}
    assert d["atencion"]["rechazados"] == 1 and d["atencion"]["hallazgos_sap"] >= 1

    alto = next(a for a in d["ficha"]["atributos"] if a["etiqueta"] == "Alto")
    assert (alto["confirmados"], alto["sugeridos"], alto["faltan"]) == (1, 1, 1)   # RAD00174 completo; RAD00188 sugerido desde SAP
    assert d["ficha"]["completos"] == 1

    prod = {p["usuario_id"]: p for p in d["productividad"]}
    assert prod[usuarios["op"]]["enviados"] == 1 and prod[usuarios["sup"]]["rechazados"] == 1

    v = d["ventas"]
    assert v["disponible"] and v["meses"] == 12 and v["sin_venta"] == 1
    clases = {c["clase"]: c for c in v["por_clase"]}
    assert clases["A"]["articulos"] == 1 and float(clases["A"]["participacion"]) == pytest.approx(100 / 110, abs=1e-4)
    top = v["prioridad"][0]
    assert top["item_code"] == "RAD00188" and top["clase"] == "A" and float(top["tendencia"]) == pytest.approx(0.25)


def test_panorama_de_otro_tipo_y_categoria_invalida(entorno):
    motor, _, _, _ = entorno
    c = cliente(motor)
    assert c.get("/api/v1/panorama?cat=25&linea=FABRICADO").json()["activos"] == 1
    r = c.get("/api/v1/panorama?cat=99&linea=IMPORTADO")
    assert r.status_code == 422 and r.json()["errors"][0]["campo"] == "cat"


def test_calidad_sap_y_csv(entorno):
    motor, _, _, _ = entorno
    assert cliente(motor, roles=(Rol.OPERADOR,)).get("/api/v1/hallazgos-sap?cat=25").status_code == 403
    c = cliente(motor)
    d = c.get("/api/v1/hallazgos-sap?cat=25&linea=IMPORTADO").json()
    assert any(g["tipo"] == "ANIOS_INVERTIDOS" for g in d["grupos"])
    assert any(h["item_code"] == "RAD00003" and h["valor"] == "2014 > 2009" for h in d["hallazgos"])
    csv = c.get("/api/v1/hallazgos-sap/csv?cat=25&linea=IMPORTADO")
    assert csv.headers["content-type"].startswith("text/csv") and csv.text.startswith("﻿Artículo,")
    assert "hallazgos-sap-25-importado.csv" in csv.headers["content-disposition"]


def test_ventas_requiere_permiso(entorno):
    motor, _, _, _ = entorno
    assert cliente(motor, roles=(Rol.ADMINISTRADOR,)).get("/api/v1/ventas?cat=25").status_code == 403
    d = cliente(motor, permisos=(Permiso.VER_ANALISIS_VENTAS,)).get("/api/v1/ventas?cat=25&linea=IMPORTADO").json()
    assert len(d["serie"]) == 24 and float(d["serie"][-1]["unidades"]) == 110
    assert [a["item_code"] for a in d["articulos"]] == ["RAD00188", "RAD00174"]
    assert d["articulos"][0]["serie"] == ["100.00"] * 12 and d["articulos"][0]["abcxyz_empresa"] == "AX"
