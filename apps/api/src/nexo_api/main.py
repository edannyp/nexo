"""Aplicación FastAPI. Todas las rutas bajo `/api/v1`; documentación en `/api/docs`."""

from importlib.metadata import version

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from .auth import router as sesion
from .auth import usuarios
from .core import errores
from .modules import calidad_sap, catalogos, panorama, preferencias, salud, ventas


def nombre_operacion(ruta: APIRoute) -> str:
    """operationId = nombre de la función (`listar_categorias` → hook `useListarCategorias` en el cliente)."""
    return ruta.name


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Nexo API",
        version=version("nexo-api"),
        description="Puente de gobernanza del artículo entre SAP, AutoCare y el catálogo maestro.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        generate_unique_id_function=nombre_operacion,
    )
    errores.registrar(app)
    v1 = APIRouter(prefix="/api/v1")
    for modulo in (salud, sesion, usuarios, preferencias, catalogos, panorama, calidad_sap, ventas):
        v1.include_router(modulo.router)
    app.include_router(v1)
    return app


app = crear_app()
