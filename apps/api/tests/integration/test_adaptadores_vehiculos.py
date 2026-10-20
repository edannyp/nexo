"""Adaptadores de vehículos contra bases locales: AutoCare con un esquema VCdb mínimo sintético y MercadoExterno con sus migraciones
reales (db/mercado_externo) y la referencia mínima de db/pruebas. Sin redes externas."""

import os
import subprocess
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine

from nexo_api.adapters.vehiculos import LIMITE_MERCADO, AutoCare, MercadoExterno, NuevoVehiculo, Vehiculos

HOST = os.getenv("PRUEBAS_PG_HOST", "postgres")
ADMIN = f"host={HOST} dbname=postgres user=postgres password=postgres"
RAIZ = Path(__file__).resolve().parents[4]
DATOS = Path(__file__).parent / "datos"


def base_nueva(nombre: str) -> str:
    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f"drop database if exists {nombre} with (force)")
        c.execute(f"create database {nombre}")
    return f"host={HOST} dbname={nombre} user=postgres password=postgres"


def motor(dsn: str):
    p = dict(x.split("=") for x in dsn.split())
    return create_engine(f"postgresql+psycopg://postgres:postgres@{p['host']}:5432/{p['dbname']}")


@pytest.fixture(scope="module")
def autocare() -> AutoCare:
    dsn = base_nueva("nexo_prueba_vcdb")
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute((DATOS / "vcdb_minimo.sql").read_text())
    return AutoCare(motor(dsn))


@pytest.fixture(scope="module")
def mercado() -> MercadoExterno:
    dsn = base_nueva("nexo_prueba_mercado")
    subprocess.run(["uv", "run", "-q", str(RAIZ / "db" / "aplicar.py"), "mercado_externo", "--dsn", dsn], check=True,
                   capture_output=True)
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute((RAIZ / "db" / "pruebas" / "ref_minimo_mercado.sql").read_text())
    return MercadoExterno(motor(dsn))


def test_autocare_marcas_y_modelos_por_anios(autocare):
    assert [m.nombre for m in autocare.marcas(1986, 1987)] == ["Toyota"]
    assert [m.nombre for m in autocare.modelos(1, 1986, 1987)] == ["Hilux", "Pickup"]
    assert [m.nombre for m in autocare.modelos(1, 1986, 1986)] == ["Pickup"]


def test_autocare_configuraciones_juntan_regiones(autocare):
    cfg = sorted(autocare.configuraciones(1, 10, 1986, 1987), key=lambda c: (c.anio, c.sub_model_id))
    assert [(c.anio, c.base_vehicle_id, c.submodelo, c.engine_config_id, c.regiones) for c in cfg] == [
        (1986, 5001, "DLX", 4704, ["CAN", "USA"]), (1987, 5002, "DLX", 4704, ["USA"]), (1987, 5002, "SR5", 4705, ["USA"])]
    assert cfg[0].motor == "2.4L L4 22R · Gasolina" and cfg[2].motor == "2.4L L4 · Gasolina · Turbo"
    assert {c.catalogo for c in cfg} == {"AUTOCARE"}


def test_autocare_etiquetas_por_id(autocare):
    bv = autocare.base_vehicles([5001, 6001])
    assert (bv[5001].anio, bv[5001].marca, bv[5001].modelo) == (1986, "Toyota", "Pickup") and bv[6001].modelo == "D-Max"
    assert autocare.submodelos([100, 101]) == {100: "DLX", 101: "SR5"}
    assert autocare.motores([4704]) == {4704: "2.4L L4 22R · Gasolina"}
    assert autocare.base_vehicles([]) == {} and autocare.motores([]) == {}


def test_mercado_registra_vehiculo_nuevo_con_su_configuracion(mercado):
    nuevo = NuevoVehiculo(marca="Great Wall", modelo="Wingle 5", desde=2015, hasta=2016, submodelo="Base", litros=Decimal("2.2"),
                          cilindros=4, combustible="Diesel", aspiracion=None, designacion="GW4D20", fuente="https://ejemplo.test/ficha",
                          regiones=["GTM"], creado_por="nexo:prueba")
    cfg = mercado.registrar(nuevo)
    assert [c.anio for c in cfg] == [2015, 2016] and len({c.engine_config_id for c in cfg}) == 1
    assert all(c.base_vehicle_id >= LIMITE_MERCADO and c.sub_model_id >= LIMITE_MERCADO for c in cfg)
    assert cfg[0].motor == "2.2L 4 cil. GW4D20 · Diésel"
    assert mercado.registrar(nuevo)[0].engine_config_id == cfg[0].engine_config_id      # registrar dos veces no duplica

    marca = next(m for m in mercado.marcas(2015, 2016) if m.nombre == "Great Wall")
    modelo = next(m for m in mercado.modelos(marca.id, 2015, 2016) if m.nombre == "Wingle 5")
    leidas = mercado.configuraciones(marca.id, modelo.id, 2015, 2016)
    assert {(c.anio, c.submodelo, c.regiones[0], c.catalogo) for c in leidas} == {(2015, "Base", "GTM", "MERCADO_EXTERNO"),
                                                                                 (2016, "Base", "GTM", "MERCADO_EXTERNO")}
    bv = mercado.base_vehicles([cfg[0].base_vehicle_id])[cfg[0].base_vehicle_id]
    assert (bv.anio, bv.marca, bv.modelo) == (2015, "Great Wall", "Wingle 5")
    assert mercado.submodelos([cfg[0].sub_model_id]) == {cfg[0].sub_model_id: "Base"}
    assert mercado.motores([cfg[0].engine_config_id]) == {cfg[0].engine_config_id: "2.2L 4 cil. GW4D20 · Diésel"}


def test_mercado_reutiliza_vehiculo_base_de_autocare(mercado):
    cfg = mercado.registrar(NuevoVehiculo(marca="Changan", modelo="CS35", desde=2018, hasta=2018, submodelo="Comfort", litros=None,
                                          cilindros=None, combustible=None, aspiracion=None, designacion="JL475",
                                          fuente="https://ejemplo.test/cs35", regiones=None, creado_por="nexo:prueba"))
    assert cfg[0].base_vehicle_id == 812018 and cfg[0].engine_config_id >= LIMITE_MERCADO


def test_vehiculos_une_catalogos_y_enruta_por_id(autocare, mercado):
    v = Vehiculos(autocare, mercado)
    nombres = [m.nombre for m in v.marcas(2012, 2016)]
    assert "Isuzu" in nombres and "Great Wall" in nombres and nombres == sorted(nombres, key=str.lower)
    propio = next(c for c in mercado.configuraciones(*_great_wall(mercado), 2015, 2015))
    bvs = v.base_vehicles([5001, propio.base_vehicle_id, None])
    assert bvs[5001].modelo == "Pickup" and bvs[propio.base_vehicle_id].modelo == "Wingle 5"
    assert v.motores([4704, propio.engine_config_id]).keys() == {4704, propio.engine_config_id}


def _great_wall(mercado) -> tuple[int, int]:
    marca = next(m for m in mercado.marcas(2015, 2016) if m.nombre == "Great Wall")
    return marca.id, next(m.id for m in mercado.modelos(marca.id, 2015, 2016) if m.nombre == "Wingle 5")
