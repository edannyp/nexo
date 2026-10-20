"""Vehículos para las aplicaciones: AutoCare (VCdb, solo lectura) + MercadoExterno (fuera de AutoCare, ADR 0014).

En VCdb una aplicación es vehículo base (año + marca + modelo) + submodelo + motor; las regiones son detalle. En MercadoExterno lo
mismo vive en `vcdb.configuracion`. Los IDs ≥ 1 000 000 000 son de MercadoExterno; los menores, de AutoCare.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Protocol

from sqlalchemy import Engine, text

from .externa import disponible

LIMITE_MERCADO = 1_000_000_000

COMBUSTIBLE = {"GAS": "Gasolina", "DIESEL": "Diésel", "ELECTRIC": "Eléctrico", "FLEX": "Flex", "HYBRID": "Híbrido",
               "LPG": "Gas LP", "CNG": "Gas natural", "GASOLINA": "Gasolina", "DIÉSEL": "Diésel"}


def texto_motor(litros: Decimal | float | None, bloque: str | None, cilindros: int | str | None, designacion: str | None,
                combustible: str | None, aspiracion: str | None) -> str:
    """'2.4L L4 22R · Gasolina' · '3.0L V6 · Diésel · Turbo'."""
    partes = []
    if litros is not None:
        partes.append(f"{float(litros):.1f}L")
    if cilindros:
        partes.append(f"{(bloque or '').strip()}{cilindros}" if bloque and bloque.strip() not in ("", "-") else f"{cilindros} cil.")
    if designacion and designacion.strip() not in ("", "-"):
        partes.append(designacion.strip())
    texto = " ".join(partes) or "Motor"
    if combustible:
        texto += f" · {COMBUSTIBLE.get(combustible.strip().upper(), combustible.strip().title())}"
    if aspiracion and "turbo" in aspiracion.lower():
        texto += " · Turbo"
    return texto


@dataclass(frozen=True)
class Marca:
    id: int
    nombre: str


@dataclass(frozen=True)
class Modelo:
    id: int
    nombre: str


@dataclass(frozen=True)
class Configuracion:
    anio: int
    base_vehicle_id: int
    sub_model_id: int
    submodelo: str
    engine_config_id: int
    motor: str
    catalogo: str                         # AUTOCARE o MERCADO_EXTERNO
    regiones: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BaseVehicle:
    anio: int
    marca: str
    modelo: str


@dataclass(frozen=True)
class NuevoVehiculo:
    marca: str
    modelo: str
    desde: int
    hasta: int
    submodelo: str
    litros: Decimal | None
    cilindros: int | None
    combustible: str | None
    aspiracion: str | None
    designacion: str | None
    fuente: str                           # URL o ficha técnica (evidencia obligatoria en MercadoExterno)
    regiones: list[str] | None
    creado_por: str


class Catalogo(Protocol):
    def marcas(self, desde: int, hasta: int) -> list[Marca]: ...
    def modelos(self, marca_id: int, desde: int, hasta: int) -> list[Modelo]: ...
    def configuraciones(self, marca_id: int, modelo_id: int, desde: int, hasta: int) -> list[Configuracion]: ...
    def base_vehicles(self, ids: Iterable[int]) -> dict[int, BaseVehicle]: ...
    def submodelos(self, ids: Iterable[int]) -> dict[int, str]: ...
    def motores(self, ids: Iterable[int]) -> dict[int, str]: ...


class AutoCare:
    """VCdb en la base autocare_global (solo lectura). Marcas y modelos se guardan en memoria: AutoCare solo cambia al publicar
    una versión nueva (reiniciar la API después de cargarla)."""

    def __init__(self, motor: Engine):
        self.motor = motor
        self.marcas = lru_cache(maxsize=256)(self._marcas)  # type: ignore[method-assign]
        self.modelos = lru_cache(maxsize=2048)(self._modelos)  # type: ignore[method-assign]

    def _filas(self, sql: str, p: dict) -> list:
        with disponible("AutoCare"), self.motor.connect() as c:
            c.execute(text("set transaction read only"))
            return c.execute(text(sql), p).all()

    def _marcas(self, desde: int, hasta: int) -> list[Marca]:
        return [Marca(f.make_id, f.make_name) for f in self._filas("""
            select distinct mk.make_id, mk.make_name from vcdb_base.base_vehicle bv join vcdb_base.make mk using (make_id)
            where bv.year_id between :d and :h order by mk.make_name""", {"d": desde, "h": hasta})]

    def _modelos(self, marca_id: int, desde: int, hasta: int) -> list[Modelo]:
        return [Modelo(f.model_id, f.model_name) for f in self._filas("""
            select distinct mo.model_id, mo.model_name from vcdb_base.base_vehicle bv join vcdb_base.model mo using (model_id)
            where bv.make_id = :m and bv.year_id between :d and :h order by mo.model_name""", {"m": marca_id, "d": desde, "h": hasta})]

    def configuraciones(self, marca_id: int, modelo_id: int, desde: int, hasta: int) -> list[Configuracion]:
        filas = self._filas("""
            select bv.year_id, bv.base_vehicle_id, v.sub_model_id, sm.sub_model_name, ec.engine_config_id,
                   eb.liter, eb.block_type, eb.cylinders, ed.engine_designation_name, ft.fuel_type_name, asp.aspiration_name,
                   array_agg(distinct r.region_abbr order by r.region_abbr) as regiones
            from vcdb_base.base_vehicle bv
            join vcdb_base.vehicle v on v.base_vehicle_id = bv.base_vehicle_id
            join vcdb_base.sub_model sm on sm.sub_model_id = v.sub_model_id
            join vcdb_parts.region r on r.region_id = v.region_id
            join vcdb_config.vehicle_to_engine_config vec on vec.vehicle_id = v.vehicle_id
            join vcdb_config.engine_config ec on ec.engine_config_id = vec.engine_config_id
            left join vcdb_parts.engine_base eb on eb.engine_base_id = ec.engine_base_id
            left join vcdb_parts.engine_designation ed on ed.engine_designation_id = ec.engine_designation_id
            left join vcdb_parts.fuel_type ft on ft.fuel_type_id = ec.fuel_type_id
            left join vcdb_parts.aspiration asp on asp.aspiration_id = ec.aspiration_id
            where bv.make_id = :m and bv.model_id = :mo and bv.year_id between :d and :h
            group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        """, {"m": marca_id, "mo": modelo_id, "d": desde, "h": hasta})
        return [Configuracion(f.year_id, f.base_vehicle_id, f.sub_model_id, f.sub_model_name, f.engine_config_id,
                              texto_motor(f.liter, f.block_type, f.cylinders, f.engine_designation_name, f.fuel_type_name,
                                          f.aspiration_name), "AUTOCARE", list(f.regiones)) for f in filas]

    def base_vehicles(self, ids: Iterable[int]) -> dict[int, BaseVehicle]:
        ids = list(ids)
        if not ids:
            return {}
        return {f.base_vehicle_id: BaseVehicle(f.year_id, f.make_name, f.model_name) for f in self._filas("""
            select bv.base_vehicle_id, bv.year_id, mk.make_name, mo.model_name from vcdb_base.base_vehicle bv
            join vcdb_base.make mk using (make_id) join vcdb_base.model mo using (model_id)
            where bv.base_vehicle_id = any(:ids)""", {"ids": ids})}

    def submodelos(self, ids: Iterable[int]) -> dict[int, str]:
        ids = list(ids)
        return dict(self._filas("select sub_model_id, sub_model_name from vcdb_base.sub_model where sub_model_id = any(:ids)",
                                {"ids": ids})) if ids else {}

    def motores(self, ids: Iterable[int]) -> dict[int, str]:
        ids = list(ids)
        if not ids:
            return {}
        return {f.engine_config_id: texto_motor(f.liter, f.block_type, f.cylinders, f.engine_designation_name, f.fuel_type_name,
                                                f.aspiration_name) for f in self._filas("""
            select ec.engine_config_id, eb.liter, eb.block_type, eb.cylinders, ed.engine_designation_name, ft.fuel_type_name,
                   asp.aspiration_name
            from vcdb_config.engine_config ec
            left join vcdb_parts.engine_base eb on eb.engine_base_id = ec.engine_base_id
            left join vcdb_parts.engine_designation ed on ed.engine_designation_id = ec.engine_designation_id
            left join vcdb_parts.fuel_type ft on ft.fuel_type_id = ec.fuel_type_id
            left join vcdb_parts.aspiration asp on asp.aspiration_id = ec.aspiration_id
            where ec.engine_config_id = any(:ids)""", {"ids": ids})}


class MercadoExterno:
    """Vehículos fuera de AutoCare (base mercado_externo). Escribe solo mediante sus funciones de registro."""

    def __init__(self, motor: Engine):
        self.motor = motor

    def _filas(self, sql: str, p: dict) -> list:
        with disponible("MercadoExterno"), self.motor.connect() as c:
            return c.execute(text(sql), p).all()

    def marcas(self, desde: int, hasta: int) -> list[Marca]:
        return [Marca(f.make_id, f.make_name) for f in self._filas("""
            select distinct make_id, make_name from vcdb.v_base_vehicle
            where origen_catalogo = 'MERCADO_EXTERNO' and year_id between :d and :h order by make_name""", {"d": desde, "h": hasta})]

    def modelos(self, marca_id: int, desde: int, hasta: int) -> list[Modelo]:
        return [Modelo(f.model_id, f.model_name) for f in self._filas("""
            select distinct model_id, model_name from vcdb.v_base_vehicle
            where origen_catalogo = 'MERCADO_EXTERNO' and make_id = :m and year_id between :d and :h order by model_name""",
            {"m": marca_id, "d": desde, "h": hasta})]

    def configuraciones(self, marca_id: int, modelo_id: int, desde: int, hasta: int) -> list[Configuracion]:
        filas = self._filas("""
            select v.year_id, c.base_vehicle_id, c.sub_model_id, coalesce(ps.sub_model_name, rs.sub_model_name) as submodelo,
                   c.engine_config_id, e.liter, e.cylinders, e.engine_designation, e.fuel_type, e.aspiration,
                   coalesce((select array_agg(r.region_abbr order by r.region_abbr) from vcdb.base_vehicle_region br
                             join ref.region r using (region_id) where br.base_vehicle_id = c.base_vehicle_id), '{}') as regiones
            from vcdb.configuracion c
            join vcdb.v_base_vehicle v using (base_vehicle_id)
            join vcdb.engine_config e using (engine_config_id)
            left join vcdb.sub_model ps on ps.sub_model_id = c.sub_model_id
            left join ref.sub_model rs on rs.sub_model_id = c.sub_model_id
            where v.make_id = :m and v.model_id = :mo and v.year_id between :d and :h
        """, {"m": marca_id, "mo": modelo_id, "d": desde, "h": hasta})
        return [Configuracion(f.year_id, f.base_vehicle_id, f.sub_model_id, f.submodelo or "—", f.engine_config_id,
                              texto_motor(f.liter, None, f.cylinders, f.engine_designation, f.fuel_type, f.aspiration),
                              "MERCADO_EXTERNO", list(f.regiones)) for f in filas]

    def base_vehicles(self, ids: Iterable[int]) -> dict[int, BaseVehicle]:
        ids = list(ids)
        if not ids:
            return {}
        return {f.base_vehicle_id: BaseVehicle(f.year_id, f.make_name, f.model_name) for f in self._filas(
            "select base_vehicle_id, year_id, make_name, model_name from vcdb.v_base_vehicle where base_vehicle_id = any(:ids)",
            {"ids": ids})}

    def submodelos(self, ids: Iterable[int]) -> dict[int, str]:
        ids = list(ids)
        return dict(self._filas("select sub_model_id, sub_model_name from vcdb.sub_model where sub_model_id = any(:ids)",
                                {"ids": ids})) if ids else {}

    def motores(self, ids: Iterable[int]) -> dict[int, str]:
        ids = list(ids)
        if not ids:
            return {}
        return {f.engine_config_id: texto_motor(f.liter, None, f.cylinders, f.engine_designation, f.fuel_type, f.aspiration)
                for f in self._filas("""select engine_config_id, liter, cylinders, engine_designation, fuel_type, aspiration
                                       from vcdb.engine_config where engine_config_id = any(:ids)""", {"ids": ids})}

    def registrar(self, n: NuevoVehiculo) -> list[Configuracion]:
        """Registra marca/modelo/años (si faltan) y la configuración en cada año. Reutiliza lo que ya existe en AutoCare."""
        evidencia = json.dumps([{"fuente": n.fuente, "registrado_desde": "Nexo", "usuario": n.creado_por}])
        with disponible("MercadoExterno"), self.motor.begin() as c:
            anios = c.execute(text("""
                select anio, base_vehicle_id, catalogo from vcdb.fn_registrar_vehiculo(:marca, :modelo, :d, :h, 'APP'::vcdb.origen,
                  :por, cast(:ev as jsonb), 1.0, cast(:reg as text[]))
            """), {"marca": n.marca, "modelo": n.modelo, "d": n.desde, "h": n.hasta, "por": n.creado_por, "ev": evidencia,
                   "reg": n.regiones or None}).all()
            salida = []
            for f in anios:
                r = c.execute(text("""
                    select sub_model_id, engine_config_id from vcdb.fn_registrar_configuracion(:bv, :sub, :lit, cast(:cil as smallint),
                      :comb, 'APP'::vcdb.origen, :por, :asp, :des, cast(:ev as jsonb))
                """), {"bv": f.base_vehicle_id, "sub": n.submodelo, "lit": n.litros, "cil": n.cilindros, "comb": n.combustible,
                       "por": n.creado_por, "asp": n.aspiracion, "des": n.designacion, "ev": evidencia}).one()
                salida.append(Configuracion(f.anio, f.base_vehicle_id, r.sub_model_id, n.submodelo, r.engine_config_id,
                                            texto_motor(n.litros, None, n.cilindros, n.designacion, n.combustible, n.aspiracion),
                                            "MERCADO_EXTERNO", n.regiones or []))
        return salida


class Vehiculos:
    """AutoCare + MercadoExterno como un solo catálogo para el selector."""

    def __init__(self, autocare: Catalogo, mercado: Catalogo):
        self.autocare, self.mercado = autocare, mercado

    def _por_rango(self, metodo: str, ids: Iterable[int]) -> dict:
        ids = set(i for i in ids if i is not None)
        return getattr(self.autocare, metodo)([i for i in ids if i < LIMITE_MERCADO]) | \
            getattr(self.mercado, metodo)([i for i in ids if i >= LIMITE_MERCADO])

    def marcas(self, desde: int, hasta: int) -> list[Marca]:
        unidas = {m.id: m for m in self.autocare.marcas(desde, hasta) + self.mercado.marcas(desde, hasta)}
        return sorted(unidas.values(), key=lambda m: m.nombre.lower())

    def modelos(self, marca_id: int, desde: int, hasta: int) -> list[Modelo]:
        unidos = {m.id: m for m in self.autocare.modelos(marca_id, desde, hasta) + self.mercado.modelos(marca_id, desde, hasta)}
        return sorted(unidos.values(), key=lambda m: m.nombre.lower())

    def configuraciones(self, marca_id: int, modelo_id: int, desde: int, hasta: int) -> list[Configuracion]:
        return self.autocare.configuraciones(marca_id, modelo_id, desde, hasta) + \
            self.mercado.configuraciones(marca_id, modelo_id, desde, hasta)

    def base_vehicles(self, ids: Iterable[int]) -> dict[int, BaseVehicle]:
        return self._por_rango("base_vehicles", ids)

    def submodelos(self, ids: Iterable[int]) -> dict[int, str]:
        return self._por_rango("submodelos", ids)

    def motores(self, ids: Iterable[int]) -> dict[int, str]:
        return self._por_rango("motores", ids)

    def registrar(self, n: NuevoVehiculo) -> list[Configuracion]:
        return self.mercado.registrar(n)  # type: ignore[attr-defined]
