"""Imágenes compartidas por las pestañas: URLs firmadas de MinIO para mostrar y subida de fotos propias (ADR 0013)."""

import io
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from PIL import Image, ImageOps, UnidentifiedImageError

from ..adapters.minio import AlmacenFotos, Firmador, FotosMinio, SubidaMinio
from ..core.config import config
from ..core.errores import Problema

LADO_MAXIMO = 2400          # px: suficiente para ver detalles del panal, sin guardar fotos de 12 MP
CALIDAD_WEBP = 85
FORMATOS = {"JPEG", "PNG", "WEBP", "MPO"}  # MPO = JPEG de algunas cámaras de celular


@lru_cache
def _firmador() -> Firmador | None:
    try:
        return FotosMinio(config())
    except RuntimeError:
        return None


def obtener_firmador() -> Firmador | None:
    """Firma URLs de objetos de MinIO para verlos. None sin MINIO_*."""
    return _firmador()


@lru_cache
def _almacen() -> AlmacenFotos | None:
    try:
        return SubidaMinio(config())
    except RuntimeError:
        return None


def obtener_almacen() -> AlmacenFotos | None:
    """Subida de fotos propias. None sin la llave de escritura MINIO_FOTOS_*."""
    return _almacen()


FirmadorOpcional = Annotated[Firmador | None, Depends(obtener_firmador)]
AlmacenOpcional = Annotated[AlmacenFotos | None, Depends(obtener_almacen)]


def a_webp(datos: bytes, nombre: str = "") -> bytes:
    """Cualquier JPEG/PNG/WebP → WebP con la orientación de la cámara aplicada y el lado mayor acotado."""
    try:
        img = Image.open(io.BytesIO(datos))
        if img.format not in FORMATOS:
            raise Problema(422, "Formato de imagen no admitido", f"{nombre or 'El archivo'} es {img.format}: usa JPG, PNG o WebP.")
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError) as e:
        raise Problema(422, "No es una imagen", f"{nombre or 'El archivo'} no se pudo leer como imagen.") from e
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    salida = io.BytesIO()
    img.save(salida, "WEBP", quality=CALIDAD_WEBP, method=4)
    return salida.getvalue()
