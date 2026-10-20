# Convenciones de la API

- REST sobre JSON, prefijo `/api/v1`. Recursos en plural y español (`/articulos`, `/vehiculos`).
- `operationId` = nombre de la función (`listar_categorias` → hook `useListarCategorias`); los errores de todos los hooks son `ProblemaError`.
- Contrato **OpenAPI** generado por FastAPI; el cliente del frontend se genera desde él (nunca tipos a mano).
- **Errores**: RFC 9457 `application/problem+json` con `type`, `title`, `status`, `detail`, `errors[]`.
- **Paginación**: por cursor opaco (`?cursor=&limit=`); respuesta `{ items, total, next_cursor }`.
- **Filtro global**: los recursos por tipo de artículo reciben `?cat=25&linea=IMPORTADO` (validado; `422` si la categoría no existe).
- **Filtros**: query params simples (`?estado=POR_VALIDAR&categoria=…`).
- **Concurrencia**: los recursos editables devuelven `version`; los `PATCH` la envían y reciben `409` si cambió.
- **Artículos** (por `ItemCode`): `GET /articulos` (filtros `q`, `estado`, `completitud`, `con_foto`, `emparejado`, `con_hallazgo`,
  `clase`, `reserva`, `orden`), `GET /articulos/{item_code}` (datos SAP, requisitos con etiqueta y pestaña, acciones posibles con la
  razón si no se pueden hacer, reserva, último motivo), `GET /articulos/{item_code}/historial`.
- **Transiciones de estado**: endpoint de acción, no PATCH del campo: `POST /articulos/{item_code}/transiciones` con
  `{ destino, motivo, version }`. `409` si otro usuario lo cambió o lo tiene reservado; `422` si falta motivo o requisitos; `403` por
  rol o doble control. Los códigos de error de la base (`DOBLE_CONTROL`, `REQUISITOS_INCOMPLETOS`…) se traducen en `core/negocio.py`.
- **Asignación**: `POST /bandejas/{operador|supervisor}/siguiente` reserva y devuelve el siguiente (30 min; prioridad: rechazados,
  luego clase de venta; el supervisor nunca recibe lo que él envió). `POST /articulos/{item_code}/asignacion` toma uno concreto,
  `PUT` renueva (latido cada 5 min), `DELETE` suelta. Expira sola.
- **Búsqueda**: `GET /busqueda?q=` (código, código anterior, número de parte, medidas `400x518x26` con ±10 mm sin importar el orden
  de alto y largo, o palabras de la descripción en cualquier orden); `todos=true` busca fuera del filtro global.
- **Vistas guardadas**: `GET/PUT /vistas`, `DELETE /vistas/{id}` (por usuario).
- **Ficha** (botón Guardar): `GET /articulos/{item_code}/ficha` (atributos habilitados con el valor de SAP, el valor en Nexo, opciones
  PIES con su traducción y si se puede editar); `PUT` con `{ version, cambios, quitar }` guarda todo junto y lo deja confirmado por el
  usuario (aceptar lo sugerido conserva el origen `SAP`). Solo quien tiene la reserva, en Pendiente o Rechazado. Las sugerencias de
  SAP se materializan al abrir la ficha (idempotente).
- **Vehículos** (selector; AutoCare + MercadoExterno vía adaptadores, `503` si la API no los tiene configurados):
  `GET /vehiculos/marcas?desde&hasta`, `GET /vehiculos/modelos?marca_id&desde&hasta` y `GET /vehiculos/configuraciones?marca_id&
  modelo_id&desde&hasta` (un renglón por submodelo + motor como se lee, con cada año, su `base_vehicle_id`, su `engine_config_id`
  y regiones; `completa` si existe en todos los años). `POST /vehiculos/externos` registra en MercadoExterno lo que no está en
  AutoCare (fuente obligatoria; ADR 0014).
- **Aplicaciones**: `GET /articulos/{item_code}/aplicaciones` (agrupadas por vehículo, con lo que dice SAP traducido al catálogo:
  marca por homologación confirmada o por nombre, modelos candidatos por parecido); `POST` `{ version, items }` agrega desde el
  selector ya confirmadas (si estaba sugerida, la confirma); `POST …/confirmar` y `POST …/quitar` con `{ version, ids }`. Misma
  regla de edición que la ficha. Confirmar una sugerida sin submodelo o motor → `422`.
- **Emparejamiento** (catálogo maestro de Consolidación vía adaptador; ADR 0011): `GET /articulos/{item_code}/emparejamiento?tolerancia=`
  (partes vinculadas y hasta 20 candidatos con `puntaje` 0–100 y `razones`: alto y largo 40, o 35 si están invertidos; ancho 15;
  número 35; vehículos en común 10), `GET /articulos/{item_code}/emparejamiento/{parte_id}` (comparación por atributo, números,
  vehículos, imágenes y fuentes) y `GET /catalogo/partes?q=` (búsqueda manual: `400x518x26`, número o descripción).
  `POST /articulos/{item_code}/partes` `{ version, parte_id, principal, traer_sugerencias }` vincula (la primera queda principal; trae
  atributos y aplicaciones como sugerencias sin pisar lo que ya hay); `POST …/partes/principal` y `POST …/partes/quitar`
  `{ version, parte_id }` (quitar borra sus sugerencias sin confirmar). Parte fusionada, descartada o de otro tipo → `422`.
- **Fotos** (ADR 0013): `GET /articulos/{item_code}/fotos` (propias con URL firmada y estado de validación, y las del catálogo
  maestro por URL); `POST` multipart `archivos` (rol `FOTOS` o `ADMINISTRADOR`; JPG/PNG/WebP → WebP, lado mayor ≤ 2400 px, con la
  orientación de la cámara; numeración `{ItemCode}_{n}` que continúa; todo se valida antes de subir nada); `PUT …/fotos/orden`
  `{ ids }`; `GET /fotos/pendientes` (activos sin foto propia, primero clase de venta A). No requiere reservar el artículo.
- **Verificación** (supervisor o administrador; ADR 0012): `GET /verificaciones?origen=` (abiertas del filtro global, con la foto
  nueva firmada y conteo por origen), `POST /verificaciones/{id}/resolucion` `{ resultado: CONFORME | CON_HALLAZGO, nota }` (`204`;
  la nota es obligatoria con hallazgo), `POST /verificaciones` `{ item_code, nota }` (manual, solo validados) y
  `POST /verificaciones/muestreo` `{ cantidad }` (administrador).
- **Equivalencia** (fabricados; ADR 0018 y 0005): `GET /articulos/{item_code}/equivalencia` (código, sugerencias de
  `codigo_anterior`, estado `SIN_CODIGO → ESPERA_FOTO → LISTO_PARA_VALIDAR → VALIDADO` y tarjeta del importado equivalente);
  `PUT` `{ codigo }` lo captura (operador, supervisor o administrador; no requiere reserva ni cambia el estado, pero no si otro lo
  tiene reservado); `POST …/validar` (supervisor o administrador; exige foto propia validada); `POST …/confirmar`
  `{ version, heredar }` confirma la equivalencia y hereda parte y aplicaciones como sugerencias (misma regla de edición que la
  ficha). `GET /fabricados?cat=&estado_codigo=&q=&limite=&desde=` es la revisión de fabricados con conteo por estado.
- **Catálogo (vista inversa)**: `GET /catalogo?cat=&q=&sin_articulo=&tolerancia=` (partes del tipo con cuántos artículos las
  usan) y `GET /catalogo/{parte_id}/articulos` (vinculados y candidatos de Nexo con el mismo puntaje del emparejamiento). Vincular
  se hace en el artículo: la consola abre `/articulos/{item_code}?pestana=emparejamiento&parte={parte_id}`.
- **Bases externas** (AutoCare, MercadoExterno, Consolidación): si no están configuradas o no responden, `503`; las pestañas siguen
  mostrando lo que vive en Nexo.
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
