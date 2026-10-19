# 0015. Login propio de la APP (por ahora)

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
Son 9 usuarios internos (5 operadores, 3 supervisores, 1 encargado de fotos) más los administradores. No se integra por ahora
con un proveedor de identidad ni con el sistema interno (DRU).

## Decisión
- Usuario y contraseña propios de la APP, guardados en Nexo (`usuario`).
- Contraseñas con **Argon2id** (`argon2-cffi`); mínimo 12 caracteres; se valida contra una lista de contraseñas comunes.
- **Alta solo por un administrador**, con contraseña temporal y **cambio obligatorio** en el primer inicio. No hay autorregistro.
- **Bloqueo** temporal tras 5 intentos fallidos (15 minutos), registrado en auditoría.
- **Sesión** en Redis (`REDIS_URL`) con cookie `httpOnly`, `Secure`, `SameSite=Lax`, CSRF por header (`convenciones.md`).
  Expira tras 8 horas de inactividad. El administrador puede cerrar sesiones de un usuario.
- **Roles en Nexo**: `OPERADOR`, `SUPERVISOR`, `ADMINISTRADOR`, `FOTOS` (un usuario puede tener varios).
- La autenticación vive detrás de un adaptador (`modules/auth`) para poder cambiar después a SSO (Entra ID, Google o DRU) sin tocar
  roles ni permisos.

## Consecuencias
- El administrador necesita una pantalla de usuarios (alta, baja lógica, roles, restablecer contraseña, cerrar sesiones).
- Al migrar a SSO, `usuario` conserva su `id` y roles; solo cambia cómo se verifica la identidad.
