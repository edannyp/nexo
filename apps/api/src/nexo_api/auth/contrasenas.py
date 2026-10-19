"""Contraseñas: Argon2id, política mínima y contraseñas temporales (ADR 0015)."""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id con los parámetros recomendados por argon2-cffi

# Hash de una contraseña que nadie tiene: se verifica contra él cuando el usuario no existe, para que el tiempo de respuesta
# no revele qué usuarios existen.
_HASH_SENUELO = _hasher.hash(secrets.token_urlsafe(32))

LONGITUD_MINIMA = 12

# Las más comunes (y sus variantes obvias en español). La política también rechaza las que contienen el usuario.
COMUNES = {
    "123456789012", "1234567890123", "qwertyuiopas", "qwerty123456", "password1234", "contraseña123", "contrasena123",
    "administrador", "admin1234567", "123456123456", "111111111111", "000000000000", "abcdefghijkl", "abc123abc123",
    "iloveyou1234", "bienvenido123", "bienvenido2024", "bienvenido2025", "bienvenido2026", "guatemala123", "guatemala2026",
    "radiadores123", "nexo12345678", "cambiar12345", "temporal1234", "password123!", "passw0rd1234",
}

# Sin caracteres que se confunden al dictarlos o copiarlos a mano (0/O, 1/l/I)
_ALFABETO = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def hashear(password: str) -> str:
    return _hasher.hash(password)


def verificar(hash_guardado: str | None, password: str) -> bool:
    try:
        return _hasher.verify(hash_guardado or _HASH_SENUELO, password) and hash_guardado is not None
    except (VerificationError, InvalidHashError):
        return False


def requiere_rehash(hash_guardado: str) -> bool:
    return _hasher.check_needs_rehash(hash_guardado)


def problemas_politica(password: str, usuario: str) -> list[str]:
    """Qué incumple la contraseña (vacío si es aceptable). Mensajes para mostrar al usuario."""
    problemas = []
    if len(password) < LONGITUD_MINIMA:
        problemas.append(f"Debe tener al menos {LONGITUD_MINIMA} caracteres.")
    if password.lower() in COMUNES or len(set(password)) <= 2:
        problemas.append("Es demasiado común o fácil de adivinar.")
    if usuario and usuario.lower() in password.lower():
        problemas.append("No debe contener tu nombre de usuario.")
    return problemas


def temporal() -> str:
    """Contraseña temporal legible, p. ej. `Hk7m-2xQp-Rt9w-Zc4n` (19 caracteres). Se cambia en el primer inicio."""
    return "-".join("".join(secrets.choice(_ALFABETO) for _ in range(4)) for _ in range(4))
