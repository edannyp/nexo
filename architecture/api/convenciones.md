# Convenciones de la API

- REST sobre JSON, prefijo `/api/v1`. Recursos en plural y español (`/articulos`, `/vehiculos`).
- `operationId` = nombre de la función (`listar_categorias` → hook `useListarCategorias`); los errores de todos los hooks son `ProblemaError`.
- Contrato **OpenAPI** generado por FastAPI; el cliente del frontend se genera desde él (nunca tipos a mano).
- **Errores**: RFC 9457 `application/problem+json` con `type`, `title`, `status`, `detail`, `errors[]`.
- **Paginación**: por cursor (`?cursor=&limit=`) en bandejas; respuesta `{ items, next_cursor }`.
- **Filtros**: query params simples (`?estado=POR_VALIDAR&categoria=…`).
- **Concurrencia**: los recursos editables devuelven `version`; los `PATCH` la envían y reciben `409` si cambió.
- **Transiciones de estado**: endpoint de acción, no PATCH del campo: `POST /articulos/{id}/transiciones` con `{ destino, motivo }`.
- **Asignación**: `POST /bandejas/{bandeja}/siguiente` reserva y devuelve el siguiente artículo (30 min); `PUT /articulos/{id}/asignacion` renueva (latido del frontend); `DELETE` suelta. Expira sola.
- **Autenticación** (ADR 0015, implementada en `apps/api/src/nexo_api/auth/`): `POST /sesion` (entrar), `GET /sesion` (usuario,
  roles, permisos y token CSRF), `DELETE /sesion` (salir), `POST /sesion/password` (cambiar la propia; cierra las demás sesiones).
  Sesión en Redis con cookie `nexo_sesion` `httpOnly`, `SameSite=Lax` y `Secure` bajo HTTPS; en Redis se guarda el SHA-256 del token.
  CSRF: cabecera `X-CSRF-Token` en los métodos que escriben. Vence tras 8 h sin actividad. 5 intentos fallidos → bloqueo de 15 min
  (`429` con `Retry-After`). Con la contraseña temporal, todo responde `403` salvo `/sesion` y `/sesion/password`.
- **Usuarios** (solo `ADMINISTRADOR`): `GET/POST /usuarios`, `PATCH /usuarios/{id}`, `POST /usuarios/{id}/restablecer`,
  `POST /usuarios/{id}/desbloquear`, `DELETE /usuarios/{id}/sesiones`. El alta y el restablecimiento devuelven la contraseña temporal
  una sola vez. Primer administrador por línea de comandos: `python -m nexo_api.cli crear-admin`.
- **Preferencias**: `GET/PUT /preferencias` guarda el filtro global del usuario en el servidor.
- **Autorización**: por rol (`OPERADOR`, `SUPERVISOR`, `ADMINISTRADOR`, `FOTOS`) y por permiso especial por usuario
  (`VER_ANALISIS_VENTAS`, ADR 0022); `403` problem+json si falta. La consola oculta las secciones que el rol no ve y la API
  siempre vuelve a verificar.
