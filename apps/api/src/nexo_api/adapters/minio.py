"""Fotos propias en MinIO (S3). Convención: imagenes_inventario/{cat}_{NOMBRE}/{ItemCode}/{ItemCode}_{n}.webp (ADR 0013).

Lectura (listar, firmar URLs para mostrar) con `MINIO_ACCESS_KEY`; la subida usa otra llave, `MINIO_FOTOS_*`, con escritura
limitada al prefijo `imagenes_inventario/`.
"""

from collections.abc import Iterator
from typing import Protocol

import boto3

from ..core.config import Config

PREFIJO = "imagenes_inventario/"


class FuenteFotos(Protocol):
    bucket: str

    def listar(self, prefijo: str) -> Iterator[str]: ...


class Firmador(Protocol):
    def firmar(self, objeto: str, bucket: str | None = None, segundos: int = 3600) -> str: ...


class AlmacenFotos(Protocol):
    bucket: str

    def subir(self, objeto: str, datos: bytes, tipo: str = "image/webp") -> None: ...


def _cliente(cfg: Config, llave: str, secreto: str):
    endpoint = (cfg.minio_endpoint or "").rstrip("/")
    if "://" not in endpoint:
        endpoint = f"{'https' if cfg.minio_secure else 'http'}://{endpoint}"
    return boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=llave, aws_secret_access_key=secreto)


class FotosMinio:
    def __init__(self, cfg: Config):
        if not (cfg.minio_endpoint and cfg.minio_access_key and cfg.minio_secret_key):
            raise RuntimeError("Faltan MINIO_ENDPOINT, MINIO_ACCESS_KEY o MINIO_SECRET_KEY.")
        self.bucket = cfg.minio_bucket
        self.s3 = _cliente(cfg, cfg.minio_access_key, cfg.minio_secret_key)

    def listar(self, prefijo: str) -> Iterator[str]:
        for pagina in self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefijo):
            for obj in pagina.get("Contents", []):
                yield obj["Key"]

    def firmar(self, objeto: str, bucket: str | None = None, segundos: int = 3600) -> str:
        """URL temporal para ver un objeto (p. ej. diagramas en rlt-diagramas) sin exponer las llaves."""
        return self.s3.generate_presigned_url("get_object", Params={"Bucket": bucket or self.bucket, "Key": objeto},
                                              ExpiresIn=segundos)


class SubidaMinio:
    """Escritura de fotos propias. Solo bajo imagenes_inventario/ (la llave también lo limita del lado de MinIO)."""

    def __init__(self, cfg: Config):
        if not (cfg.minio_endpoint and cfg.minio_fotos_access_key and cfg.minio_fotos_secret_key):
            raise RuntimeError("Faltan MINIO_ENDPOINT, MINIO_FOTOS_ACCESS_KEY o MINIO_FOTOS_SECRET_KEY.")
        self.bucket = cfg.minio_bucket
        self.s3 = _cliente(cfg, cfg.minio_fotos_access_key, cfg.minio_fotos_secret_key)

    def subir(self, objeto: str, datos: bytes, tipo: str = "image/webp") -> None:
        if not objeto.startswith(PREFIJO):
            raise ValueError(f"Solo se sube bajo {PREFIJO}")
        self.s3.put_object(Bucket=self.bucket, Key=objeto, Body=datos, ContentType=tipo)
