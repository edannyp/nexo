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
2. **Clonar** el repositorio en el servidor y crear el `.env` en la raíz (nunca se versiona) a partir de `.env.example`.
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
3. **Levantar**:
   ```bash
   docker compose up -d --build
   docker compose ps                # api y web en "healthy"
   ```
   Con `NEXO_MIGRAR_AL_ARRANCAR=true`, la API aplica las migraciones pendientes de la base `nexo` al arrancar.
4. **Catálogo de atributos PIES** (una vez, y cada vez que se actualice AutoCare), desde una máquina con el repositorio y acceso a
   AutoCare y a la base `nexo`:
   ```bash
   uv run db/ref/cargar_ref.py nexo     # usa AUTOCARE_* y NEXO_* del .env
   ```
5. **Comprobar**: `http://<servidor>/` muestra la consola; `http://<servidor>/api/v1/salud/lista` responde `{"estado":"ok","migracion":"0004"}`.
   La documentación de la API está en `http://<servidor>/api/docs`.

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
