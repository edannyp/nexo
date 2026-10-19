# Convenciones de la API

- REST sobre JSON, prefijo `/api/v1`. Recursos en plural y español (`/articulos`, `/vehiculos`).
- Contrato **OpenAPI** generado por FastAPI; el cliente del frontend se genera desde él (nunca tipos a mano).
- **Errores**: RFC 9457 `application/problem+json` con `type`, `title`, `status`, `detail`, `errors[]`.
- **Paginación**: por cursor (`?cursor=&limit=`) en bandejas; respuesta `{ items, next_cursor }`.
- **Filtros**: query params simples (`?estado=POR_VALIDAR&categoria=…`).
- **Concurrencia**: los recursos editables devuelven `version`; los `PATCH` la envían y reciben `409` si cambió.
- **Transiciones de estado**: endpoint de acción, no PATCH del campo: `POST /articulos/{id}/transiciones` con `{ destino, motivo }`.
- **Asignación**: `POST /bandejas/{bandeja}/siguiente` reserva y devuelve el siguiente artículo (30 min); `PUT /articulos/{id}/asignacion` renueva (latido del frontend); `DELETE` suelta. Expira sola.
- **Autenticación** (ADR 0015): login propio (`POST /sesion`, `DELETE /sesion`, `POST /sesion/password`); sesión en Redis con cookie `httpOnly`, `Secure`, `SameSite=Lax`; CSRF por header en métodos de escritura; 8 h de inactividad.
- **Autorización**: por rol (`OPERADOR`, `SUPERVISOR`, `ADMINISTRADOR`, `FOTOS`); `403` problem+json si falta el rol.
