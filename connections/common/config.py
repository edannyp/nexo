"""Configuración de conexiones leída desde el .env de la raíz del repositorio."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

# Bases PostgreSQL conocidas: nombre lógico -> prefijo de variables de entorno.
POSTGRES = {
    "nexo": "NEXO",
    "autocare": "AUTOCARE",
    "mercado_externo": "MERCADO_EXTERNO",
    "consolidacion": "CONSOLIDACION",
}


def postgres_dsn(nombre: str) -> str | None:
    """Devuelve el DSN de una base Postgres, o None si no está configurada."""
    prefijo = POSTGRES[nombre]
    host = os.getenv(f"{prefijo}_HOST")
    if not host:
        return None
    return (
        f"host={host} port={os.getenv(f'{prefijo}_PORT', '5432')} "
        f"dbname={os.getenv(f'{prefijo}_DB')} user={os.getenv(f'{prefijo}_USER')} "
        f"password={os.getenv(f'{prefijo}_PASSWORD', '')} "
        f"sslmode={os.getenv(f'{prefijo}_SSLMODE', 'prefer')} connect_timeout=10"
    )


def hana() -> dict | None:
    if not os.getenv("SAP_HANA_HOST"):
        return None
    return {
        "address": os.environ["SAP_HANA_HOST"],
        "port": int(os.getenv("SAP_HANA_PORT", "30015")),
        "user": os.getenv("SAP_HANA_USER"),
        "password": os.getenv("SAP_HANA_PASSWORD"),
        "encrypt": os.getenv("SAP_HANA_ENCRYPT", "true").lower() == "true",
        "sslValidateCertificate": os.getenv("SAP_HANA_SSL_VALIDATE", "false").lower() == "true",
    }


def hana_schema() -> str:
    return os.getenv("SAP_HANA_SCHEMA", "")


def clickhouse() -> dict | None:
    if not os.getenv("CLICKHOUSE_HOST"):
        return None
    return {
        "host": os.environ["CLICKHOUSE_HOST"],
        "port": int(os.getenv("CLICKHOUSE_PORT", "8123")),
        "username": os.getenv("CLICKHOUSE_USER", "default"),
        "password": os.getenv("CLICKHOUSE_PASSWORD", ""),
        "database": os.getenv("CLICKHOUSE_DB", "default"),
    }


def minio() -> dict | None:
    """Parámetros S3 para MinIO. Acepta el endpoint con o sin esquema (https://host/)."""
    endpoint = os.getenv("MINIO_ENDPOINT", "").strip().rstrip("/")
    if not endpoint:
        return None
    if "://" not in endpoint:
        seguro = os.getenv("MINIO_SECURE", "true").lower() == "true"
        endpoint = f"{'https' if seguro else 'http'}://{endpoint}"
    return {
        "endpoint_url": endpoint,
        "aws_access_key_id": os.getenv("MINIO_ACCESS_KEY"),
        "aws_secret_access_key": os.getenv("MINIO_SECRET_KEY"),
    }


def minio_bucket() -> str:
    return os.getenv("MINIO_BUCKET", "")
