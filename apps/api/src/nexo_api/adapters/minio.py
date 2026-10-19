"""Fotos propias en MinIO (S3). Convención: imagenes_inventario/{cat}_{NOMBRE}/{ItemCode}/{ItemCode}_{n}.webp (ADR 0013)."""

from collections.abc import Iterator
from typing import Protocol

import boto3

from ..core.config import Config

PREFIJO = "imagenes_inventario/"


class FuenteFotos(Protocol):
    bucket: str

    def listar(self, prefijo: str) -> Iterator[str]: ...


class FotosMinio:
    def __init__(self, cfg: Config):
        if not (cfg.minio_endpoint and cfg.minio_access_key and cfg.minio_secret_key):
            raise RuntimeError("Faltan MINIO_ENDPOINT, MINIO_ACCESS_KEY o MINIO_SECRET_KEY.")
        endpoint = cfg.minio_endpoint.rstrip("/")
        if "://" not in endpoint:
            endpoint = f"{'https' if cfg.minio_secure else 'http'}://{endpoint}"
        self.bucket = cfg.minio_bucket
        self.s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=cfg.minio_access_key,
                               aws_secret_access_key=cfg.minio_secret_key)

    def listar(self, prefijo: str) -> Iterator[str]:
        for pagina in self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefijo):
            for obj in pagina.get("Contents", []):
                yield obj["Key"]

    def firmar(self, objeto: str, bucket: str | None = None, segundos: int = 3600) -> str:
        """URL temporal para ver un objeto (p. ej. diagramas en rlt-diagramas) sin exponer las llaves."""
        return self.s3.generate_presigned_url("get_object", Params={"Bucket": bucket or self.bucket, "Key": objeto},
                                              ExpiresIn=segundos)
