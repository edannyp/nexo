"""Contraseñas y almacén de sesiones, sin base de datos. Redis real solo si está disponible (REDIS_URL)."""

import os
import time

import pytest
import redis

from nexo_api.auth import contrasenas
from nexo_api.auth.sesiones import SesionesMemoria, SesionesRedis


def test_hash_argon2id_y_verificacion():
    h = contrasenas.hashear("Radiador-Azul-Hilux-86")
    assert h.startswith("$argon2id$")
    assert contrasenas.verificar(h, "Radiador-Azul-Hilux-86")
    assert not contrasenas.verificar(h, "otra")
    assert not contrasenas.verificar(None, "cualquiera")          # usuario inexistente: mismo costo, siempre falso


def test_politica():
    assert contrasenas.problemas_politica("corta", "ana") == ["Debe tener al menos 12 caracteres."]
    assert "Es demasiado común o fácil de adivinar." in contrasenas.problemas_politica("Bienvenido2026", "ana")
    assert "Es demasiado común o fácil de adivinar." in contrasenas.problemas_politica("aaaaaaaaaaaaaa", "ana")
    assert contrasenas.problemas_politica("Radiador-Azul-Hilux-86", "ana") == []


def test_temporal_legible():
    t = contrasenas.temporal()
    assert len(t) == 19 and t.count("-") == 3 and not set(t) & set("0O1lI")


def _almacenes():
    yield pytest.param(SesionesMemoria(2), id="memoria")
    url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        cliente = redis.Redis.from_url(url, socket_connect_timeout=0.5)
        cliente.ping()
        yield pytest.param(SesionesRedis(cliente, 2), id="redis")
    except redis.RedisError:
        yield pytest.param(None, id="redis", marks=pytest.mark.skip(reason=f"Redis no disponible en {url}"))


@pytest.mark.parametrize("almacen", _almacenes())
def test_sesiones(almacen):
    token, sesion = almacen.crear(999_001)
    assert almacen.obtener(token) == sesion and len(sesion.csrf) > 20
    assert almacen.obtener("token-inventado") is None
    otro, _ = almacen.crear(999_001)
    assert almacen.eliminar_de_usuario(999_001) == 2
    assert almacen.obtener(token) is None and almacen.obtener(otro) is None

    t2, _ = almacen.crear(999_002)
    almacen.eliminar(t2)
    assert almacen.obtener(t2) is None

    t3, _ = almacen.crear(999_003)                               # expira sin actividad (2 s en la prueba)
    time.sleep(2.2)
    assert almacen.obtener(t3) is None
