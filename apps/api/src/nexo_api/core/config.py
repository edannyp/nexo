"""Configuración solo por variables de entorno (`NEXO_*`). En desarrollo se leen del `.env` de la raíz del repositorio."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


def env_local() -> Path | None:
    """`.env` de la raíz del repositorio en desarrollo; en la imagen Docker no existe y todo llega por variables de entorno."""
    return next((d / ".env" for d in Path(__file__).resolve().parents if (d / ".env").is_file()), None)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXO_", env_file=env_local(), extra="ignore")

    host: str
    port: int = 5432
    db: str = "nexo"
    user: str
    password: str = ""
    sslmode: str = "prefer"

    # Sesiones (ADR 0015). REDIS_URL no lleva el prefijo NEXO_ (lo comparte el entorno).
    redis_url: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")
    horas_sesion: int = 8               # expira tras este tiempo sin actividad
    intentos_maximos: int = 5           # intentos fallidos antes del bloqueo
    minutos_bloqueo: int = 15

    # Fuentes de apoyo de solo lectura (sin prefijo NEXO_: las comparte el entorno). Opcionales: sin ellas, las tareas
    # que las usan avisan y la APP sigue funcionando.
    clickhouse_host: str | None = Field(None, validation_alias="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(8123, validation_alias="CLICKHOUSE_PORT")
    clickhouse_user: str = Field("default", validation_alias="CLICKHOUSE_USER")
    clickhouse_password: str = Field("", validation_alias="CLICKHOUSE_PASSWORD")
    minio_endpoint: str | None = Field(None, validation_alias="MINIO_ENDPOINT")
    minio_access_key: str | None = Field(None, validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str | None = Field(None, validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field("rlt-dru", validation_alias="MINIO_BUCKET")
    minio_secure: bool = Field(True, validation_alias="MINIO_SECURE")
    # AutoCare (VCdb, solo lectura) y MercadoExterno (vehículos fuera de AutoCare): selector de vehículos de las aplicaciones
    autocare_host: str | None = Field(None, validation_alias="AUTOCARE_HOST")
    autocare_port: int = Field(5432, validation_alias="AUTOCARE_PORT")
    autocare_db: str | None = Field(None, validation_alias="AUTOCARE_DB")
    autocare_user: str | None = Field(None, validation_alias="AUTOCARE_USER")
    autocare_password: str = Field("", validation_alias="AUTOCARE_PASSWORD")
    mercado_externo_host: str | None = Field(None, validation_alias="MERCADO_EXTERNO_HOST")
    mercado_externo_port: int = Field(5432, validation_alias="MERCADO_EXTERNO_PORT")
    mercado_externo_db: str | None = Field(None, validation_alias="MERCADO_EXTERNO_DB")
    mercado_externo_user: str | None = Field(None, validation_alias="MERCADO_EXTERNO_USER")
    mercado_externo_password: str = Field("", validation_alias="MERCADO_EXTERNO_PASSWORD")
    # Consolidación (catálogo maestro, solo lectura): candidatos para el emparejamiento (ADR 0011)
    consolidacion_host: str | None = Field(None, validation_alias="CONSOLIDACION_HOST")
    consolidacion_port: int = Field(5432, validation_alias="CONSOLIDACION_PORT")
    consolidacion_db: str | None = Field(None, validation_alias="CONSOLIDACION_DB")
    consolidacion_user: str | None = Field(None, validation_alias="CONSOLIDACION_USER")
    consolidacion_password: str = Field("", validation_alias="CONSOLIDACION_PASSWORD")

    def url_externa(self, prefijo: str) -> URL | None:
        """URL de una base externa (`autocare`, `mercado_externo`, `consolidacion`), o None si no está configurada."""
        host, db, user = (getattr(self, f"{prefijo}_{k}") for k in ("host", "db", "user"))
        if not (host and db and user):
            return None
        return URL.create("postgresql+psycopg", username=user, password=getattr(self, f"{prefijo}_password"), host=host,
                          port=getattr(self, f"{prefijo}_port"), database=db)

    @property
    def url_bd(self) -> URL:
        return URL.create(
            "postgresql+psycopg", username=self.user, password=self.password, host=self.host, port=self.port,
            database=self.db, query={"sslmode": self.sslmode},
        )


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
