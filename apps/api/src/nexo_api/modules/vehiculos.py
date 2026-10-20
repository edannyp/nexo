"""Selector de vehículos (propuesta UX §6.4 "Pestaña Aplicaciones"): marca → modelo → configuraciones (submodelo + motor) por año,
de AutoCare y MercadoExterno juntos; y alta de vehículos fuera de AutoCare (ADR 0014)."""

from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import create_engine

from ..adapters.vehiculos import AutoCare, MercadoExterno, NuevoVehiculo, Vehiculos
from ..auth.dependencias import UsuarioActual
from ..core.config import config
from ..core.errores import Problema

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

Anio = Annotated[int, Query(ge=1900, le=2100)]


@lru_cache
def _vehiculos() -> Vehiculos | None:
    cfg = config()
    url_ac, url_me = cfg.url_externa("autocare"), cfg.url_externa("mercado_externo")
    if not (url_ac and url_me):
        return None
    return Vehiculos(AutoCare(create_engine(url_ac, pool_pre_ping=True, pool_size=3)),
                     MercadoExterno(create_engine(url_me, pool_pre_ping=True, pool_size=3)))


def obtener_vehiculos() -> Vehiculos | None:
    """Dependencia sustituible en pruebas. None si la API no tiene AutoCare/MercadoExterno configurados."""
    return _vehiculos()


def requerir_vehiculos(v: Annotated[Vehiculos | None, Depends(obtener_vehiculos)]) -> Vehiculos:
    if v is None:
        raise Problema(503, "Catálogo de vehículos no configurado", "Faltan AUTOCARE_* o MERCADO_EXTERNO_* en el entorno de la API.")
    return v


Catalogo = Annotated[Vehiculos, Depends(requerir_vehiculos)]
CatalogoOpcional = Annotated[Vehiculos | None, Depends(obtener_vehiculos)]


class OpcionVehiculo(BaseModel):
    id: int
    nombre: str


class AnioConfiguracion(BaseModel):
    anio: int
    base_vehicle_id: int
    engine_config_id: int                # AutoCare cambia el id del motor entre rangos de años aunque se lea igual
    regiones: list[str]
    catalogo: str


class ConfiguracionAgrupada(BaseModel):
    """Un submodelo + motor (como lo lee el operador) y los años en que existe; cada año lleva su propio motor de VCdb."""
    sub_model_id: int
    submodelo: str
    motor: str
    anios: list[AnioConfiguracion]
    completa: bool                       # existe en todos los años pedidos
    catalogo: str


def _rango(desde: int, hasta: int) -> None:
    if hasta < desde or hasta - desde > 40:
        raise Problema(422, "Rango de años no válido", errors=[{"campo": "hasta", "mensaje": "Revisa los años (máximo 40)."}])


@router.get("/marcas", response_model=list[OpcionVehiculo], summary="Marcas con vehículos en esos años (AutoCare + MercadoExterno)")
def listar_marcas(_: UsuarioActual, v: Catalogo, desde: Anio, hasta: Anio) -> list[OpcionVehiculo]:
    _rango(desde, hasta)
    return [OpcionVehiculo(id=m.id, nombre=m.nombre) for m in v.marcas(desde, hasta)]


@router.get("/modelos", response_model=list[OpcionVehiculo], summary="Modelos de la marca en esos años")
def listar_modelos(_: UsuarioActual, v: Catalogo, marca_id: int, desde: Anio, hasta: Anio) -> list[OpcionVehiculo]:
    _rango(desde, hasta)
    return [OpcionVehiculo(id=m.id, nombre=m.nombre) for m in v.modelos(marca_id, desde, hasta)]


def agrupar(configuraciones, desde: int, hasta: int) -> list[ConfiguracionAgrupada]:
    grupos: dict[tuple[int, str], dict] = {}
    for c in configuraciones:
        g = grupos.setdefault((c.sub_model_id, c.motor), {
            "sub_model_id": c.sub_model_id, "submodelo": c.submodelo, "motor": c.motor, "catalogo": c.catalogo, "anios": {}})
        g["anios"].setdefault((c.anio, c.engine_config_id), AnioConfiguracion(
            anio=c.anio, base_vehicle_id=c.base_vehicle_id, engine_config_id=c.engine_config_id, regiones=c.regiones,
            catalogo=c.catalogo))
    total = hasta - desde + 1
    salida = [ConfiguracionAgrupada(**{**g, "anios": sorted(g["anios"].values(), key=lambda a: (a.anio, a.engine_config_id)),
                                       "completa": len({a for a, _ in g["anios"]}) == total}) for g in grupos.values()]
    return sorted(salida, key=lambda g: (g.submodelo.lower(), g.motor))


@router.get("/configuraciones", response_model=list[ConfiguracionAgrupada],
            summary="Combinaciones submodelo + motor del modelo en esos años, con los años y regiones en que existen")
def listar_configuraciones(_: UsuarioActual, v: Catalogo, marca_id: int, modelo_id: int, desde: Anio, hasta: Anio
                           ) -> list[ConfiguracionAgrupada]:
    _rango(desde, hasta)
    return agrupar(v.configuraciones(marca_id, modelo_id, desde, hasta), desde, hasta)


class VehiculoExterno(BaseModel):
    marca: str = Field(min_length=1, max_length=80)
    modelo: str = Field(min_length=1, max_length=80)
    desde: int = Field(ge=1900, le=2100)
    hasta: int = Field(ge=1900, le=2100)
    submodelo: str = Field(min_length=1, max_length=80, description="«Base» si no tiene otro nombre")
    litros: Decimal | None = Field(None, gt=0, lt=30)
    cilindros: int | None = Field(None, ge=1, le=16)
    combustible: str | None = Field(None, max_length=30)
    aspiracion: str | None = Field(None, max_length=30)
    designacion: str | None = Field(None, max_length=40, description="Código del motor, p. ej. 4G63")
    fuente: str = Field(min_length=5, max_length=500, description="URL o ficha técnica que respalda el vehículo")
    regiones: list[str] | None = Field(None, description="Abreviaturas VCdb: GTM, SLV…")

    @model_validator(mode="after")
    def motor_identificable(self) -> "VehiculoExterno":
        if self.litros is None and not self.designacion:
            raise ValueError("Indica los litros o el código del motor.")
        if self.hasta < self.desde or self.hasta - self.desde > 40:
            raise ValueError("Revisa los años (máximo 40).")
        return self


@router.post("/externos", response_model=list[ConfiguracionAgrupada], status_code=201,
             summary="Registrar en MercadoExterno un vehículo que no está en AutoCare (marca, modelo, años, submodelo y motor)")
def registrar_vehiculo_externo(datos: VehiculoExterno, usuario: UsuarioActual, v: Catalogo) -> list[ConfiguracionAgrupada]:
    nuevas = v.registrar(NuevoVehiculo(
        marca=datos.marca.strip(), modelo=datos.modelo.strip(), desde=datos.desde, hasta=datos.hasta, submodelo=datos.submodelo.strip(),
        litros=datos.litros, cilindros=datos.cilindros, combustible=datos.combustible, aspiracion=datos.aspiracion,
        designacion=datos.designacion, fuente=datos.fuente.strip(), regiones=[r.upper() for r in datos.regiones or []] or None,
        creado_por=f"nexo:{usuario.usuario}"))
    return agrupar(nuevas, datos.desde, datos.hasta)
