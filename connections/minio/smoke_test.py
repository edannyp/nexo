"""Comprueba la conexión de lectura a MinIO y lista las carpetas de imágenes del bucket."""

import boto3
from botocore.config import Config

from common.config import minio, minio_bucket

PREFIJO = "imagenes_inventario/"


def main() -> None:
    params = minio()
    if params is None:
        print("[--] MinIO: sin configurar (MINIO_ENDPOINT vacío)")
        return
    bucket = minio_bucket()
    s3 = boto3.client(
        "s3",
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, connect_timeout=10, retries={"max_attempts": 1}),
        **params,
    )
    try:
        r = s3.list_objects_v2(Bucket=bucket, Prefix=PREFIJO, Delimiter="/")
        carpetas = [p["Prefix"] for p in r.get("CommonPrefixes", [])]
        print(f"[ok] MinIO {bucket}/{PREFIJO}: {len(carpetas)} carpetas")
        for c in carpetas[:20]:
            print(f"     {c}")
    except Exception as exc:  # noqa: BLE001
        print(f"[x ] MinIO: {exc}")


if __name__ == "__main__":
    main()
