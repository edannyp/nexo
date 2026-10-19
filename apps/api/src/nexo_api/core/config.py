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

    @property
    def url_bd(self) -> URL:
        return URL.create(
            "postgresql+psycopg", username=self.user, password=self.password, host=self.host, port=self.port,
            database=self.db, query={"sslmode": self.sslmode},
        )


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
