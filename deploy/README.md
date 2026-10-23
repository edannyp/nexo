# Despliegue de Nexo

Docker Compose en un servidor interno (ADR 0016): `web` (Caddy con la consola y proxy a `/api`), `api` (FastAPI) y `redis`.
La base `nexo` vive en el servidor PostgreSQL existente, fuera de Compose.

```
navegador ──► web (Caddy :80/:443) ──/api/*──► api (FastAPI :8000) ──► PostgreSQL (base nexo)
                     └── consola React (estáticos)        └──► redis (sesiones, desde el paso 3)
```

## Primera vez
1. **Base de datos**: crear la base `nexo` en el servidor PostgreSQL (una sola vez), con un usuario para la APP (ADR 0017):
   ```sql
   create database nexo;
   ```
2. **Clonar** el repositorio en el servidor (rama `main`) y crear el `.env` en la raíz (nunca se versiona) a partir de
   `.env.example`, o copiando el `.env` de desarrollo. Si se copia, revisar estas diferencias:
   - `NEXO_*` apunta a la base `nexo` del **servidor** PostgreSQL, no al contenedor `postgres` de desarrollo.
   - `REDIS_URL` no hace falta: Compose lo fija al Redis interno.
   - `AUTOCARE_*`, `MERCADO_EXTERNO_*`, `CONSOLIDACION_*`, `CLICKHOUSE_*` y `MINIO_*` sirven tal cual si el servidor llega a las
     mismas IP (probar desde el servidor; en desarrollo pasan por la VPN). `MINIO_SECURE=false` para el MinIO interno.
   - `MINIO_FOTOS_*` (escritura de fotos) es opcional al principio: sin ella no se suben fotos.

   Lo mínimo para arrancar:
   ```bash
   NEXO_HOST=<IP del servidor PostgreSQL>   # no "postgres": ese nombre solo existe en el entorno de desarrollo
   NEXO_PORT=5432
   NEXO_DB=nexo
   NEXO_USER=<usuario>
   NEXO_PASSWORD=<contraseña>
   ```
   Opcionales: `NEXO_PUERTO` (por defecto 80), `NEXO_PUERTO_HTTPS` (443), `NEXO_SITIO` (por defecto `:80`; con un nombre interno
   como `nexo.empresa.local`, Caddy sirve HTTPS con su propia autoridad certificadora) y `NEXO_MIGRAR_AL_ARRANCAR` (por defecto `true`).
3. **MercadoExterno** (una vez por versión del esquema): aplicar sus migraciones pendientes (incluye `V003__configuraciones.sql`,
   que usa la pestaña Aplicaciones), desde una máquina con el repositorio y acceso al servidor:
   ```bash
   uv run db/aplicar.py mercado_externo --servidor     # usa MERCADO_EXTERNO_* del .env
   ```
4. **Levantar**:
   ```bash
   docker compose up -d --build
   docker compose ps                # api y web en "healthy"
   ```
   Con `NEXO_MIGRAR_AL_ARRANCAR=true`, la API aplica las migraciones pendientes de la base `nexo` al arrancar.
5. **Catálogo de atributos PIES** (una vez, y cada vez que se actualice AutoCare), desde una máquina con el repositorio y acceso a
   AutoCare y a la base `nexo`:
   ```bash
   uv run db/ref/cargar_ref.py nexo     # usa AUTOCARE_* y NEXO_* del .env
   ```
   Cada carga informa altas, cambios, bajas (quedan **obsoletas**, no se borran) e impacto, y lo guarda en
   `meta.historial_referencia` (ADR 0024). Ver *Actualizar AutoCare* en `db/README.md`.
6. **Primer administrador** (una sola vez). Imprime una contraseña temporal que se cambia al entrar:
   ```bash
   docker compose exec api python -m nexo_api.cli crear-admin <usuario> "<Nombre completo>"
   ```
   El resto de los usuarios los da de alta ese administrador desde **Administración** en la consola (no hay autorregistro).
   **Fotos existentes** (una vez, repetible): `docker compose exec api python -m nexo_api.cli importar-fotos`.
7. **Comprobar**: `http://<servidor>/` muestra la pantalla de entrada; `http://<servidor>/api/v1/salud/lista` responde
   `{"estado":"ok","migracion":"0015"}`. La documentación de la API está en `http://<servidor>/api/docs`.

## Usuarios de los procesos externos
Una vez cada uno, como superusuario, después de que la API migró a `0011` (permisos mínimos, ADR 0017). La contraseña se pasa al
ejecutar y se entrega al equipo de cada proceso:
```bash
psql -h <servidor> -U postgres -d nexo -v clave='<contraseña larga>' -f deploy/sql/usuario-etl.sql                       # ETL de SAP
psql -h <servidor> -U postgres -d nexo -v clave='<contraseña larga>' -f deploy/sql/usuario-agente-revision-catalogo.sql  # agente
```
| Usuario | Puede |
|---|---|
| `etl_entrada` | leer e insertar en `staging` (artículos de SAP) y ejecutar `app.fn_procesar_staging` y `app.fn_articulos_conocidos` |
| `agente_revision_catalogo` | ejecutar `app.fn_partes_emparejadas`, `app.fn_datos_emparejamiento` y `app.fn_registrar_cambios_catalogo` |

Ninguno lee ni escribe las tablas de `app`: las funciones corren con los permisos de su dueño.

## Tareas programadas
**Ventas** (ADR 0022 y 0023): Nexo copia a diario de ClickHouse las unidades por artículo y la clasificación ABC-XYZ de la empresa.
Con `cron` en el servidor, desde la carpeta del repositorio:
```bash
0 6 * * *  cd /opt/nexo && docker compose exec -T api python -m nexo_api.cli actualizar-ventas
```
**Revisión del catálogo:** la hace el agente de revisión, un proceso aparte (contrato en `architecture/datos/contratos.md`); Nexo
no la implementa.

Una sola vez (repetible sin duplicar), la importación inicial de las fotos que ya están en MinIO (ADR 0013):
```bash
docker compose exec api python -m nexo_api.cli importar-fotos
```
Requieren `CLICKHOUSE_*` (ventas) y `MINIO_*` (fotos; `MINIO_SECURE=false` para el MinIO interno).

## Fotos propias (pantalla Fotos)
La subida usa una llave de MinIO **aparte**, con escritura limitada a `rlt-dru/imagenes_inventario/` (ADR 0013):
`MINIO_FOTOS_ACCESS_KEY` y `MINIO_FOTOS_SECRET_KEY` (en producción, la misma llave de lectura si ya escribe en ese prefijo; ADR 0013). Sin ella, la APP muestra las fotos pero no permite subir. El encargado de
fotos necesita un usuario con rol `FOTOS`.

## Catálogo de vehículos (pestaña Aplicaciones)
La API lee AutoCare (solo lectura) y registra en MercadoExterno: `AUTOCARE_*` y `MERCADO_EXTERNO_*` en el `.env` (10.10.60.6, base
`mercado_externo`, usuario con los permisos de `grp_mercado_registro`). MercadoExterno debe tener aplicada la migración `V003__configuraciones.sql`
(`uv run db/aplicar.py mercado_externo --servidor`). Sin estas variables, la pestaña muestra las aplicaciones pero no permite buscar.

## Catálogo maestro (pestaña Emparejamiento y diagramas)
La API lee Consolidación con `CONSOLIDACION_*` (10.10.60.6, base `consolidacion_articulos`, usuario `app_lectura` miembro de `grp_app_lectura`). Los diagramas guardados en MinIO se muestran con URLs
firmadas (requiere `MINIO_*`). Sin Consolidación, la pestaña muestra lo ya vinculado pero no busca candidatos.

## Actualizar
```bash
git pull                         # la rama que corresponda al ambiente (main en producción)
docker compose up -d --build
```

## Notas
- Sin el ETL de SAP (otro proyecto) la base no tiene artículos: el filtro global mostrará las categorías con 0 activos.
- **Respaldos**: la base `nexo` guardará trabajo humano que no se puede regenerar. Antes de operar en serio, programar al menos un
  `pg_dump` diario (riesgo aceptado en el ADR 0016).
- Registros: `docker compose logs -f api` · `docker compose logs -f web`.
- **Sesiones** en Redis (volumen `redis-datos`): reiniciar Redis no cierra sesiones; borrar el volumen sí.
- La cookie de sesión se marca `Secure` cuando el sitio se sirve por HTTPS (`NEXO_SITIO` con un nombre y `tls internal`).
