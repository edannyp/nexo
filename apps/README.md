# apps/

`api/` ya tiene las migraciones de Nexo (`alembic/`, DDL en `alembic/sql/`: 0001 núcleo, 0002 enriquecimiento, 0003 código equivalente, 0004 catálogo de atributos) y sus pruebas:
`cd apps/api && uv run pytest` (crea `nexo_prueba_*` en el Postgres local). El código de FastAPI viene después.

| App | Estructura prevista |
|---|---|
| `api/` | FastAPI. `src/nexo_api/{core, modules/{auth, articulos, workflow, aplicaciones, diagramas, matching, auditoria}, adapters/{autocare, consolidacion, mercado_externo, minio}}`, `alembic/`, `tests/{unit, integration}` |
| `web/` | React + Vite. `src/{app, routes, features/{bandeja-validacion, master-merge, articulo-detalle, aplicaciones-vehiculares, diagramas, auth}, shared}`, `e2e/` |
