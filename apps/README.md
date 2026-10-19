# apps/

| App | Qué es | Estructura |
|---|---|---|
| `api/` | API FastAPI y migraciones de la base `nexo` | `src/nexo_api/{core (config, bd, errores), auth (sesiones, contraseñas, usuarios), modules/{salud, catalogos, preferencias, …}, cli}`, `alembic/` (DDL en `alembic/sql/`), `tests/{unit, integration}` |
| `web/` | Consola React + Vite (SPA) | `src/{app (armazón, router, sesión, filtro global, navegación), features/{auth, admin, panorama, pendiente, …}, shared (ui, tema)}` |

Hacia dónde crecen (architecture/ux/propuesta.md): `modules/{auth, articulos, workflow, aplicaciones, diagramas, matching, auditoria}`,
`adapters/{autocare, consolidacion, mercado_externo, minio, clickhouse}` en la API; `features/{auth, busqueda, explorar, trabajo,
articulo (ficha, aplicaciones, emparejamiento, equivalencia, fotos, historial), validacion, verificacion, fabricados, catalogo, fotos,
calidad-sap, ventas, admin}` en la consola.

## Desarrollo
```bash
# API (lee NEXO_* del .env de la raíz) — http://localhost:8000/api/docs
cd apps/api && uv run uvicorn nexo_api.main:app --reload

# Consola — http://localhost:5173 (redirige /api a la API local)
pnpm install && pnpm dev

# Pruebas
cd apps/api && uv run pytest        # crea bases nexo_prueba_* en el Postgres local
pnpm test                           # consola (Vitest)
pnpm lint                           # ESLint + Prettier

# Tras cambiar la API: regenerar el contrato OpenAPI y el cliente TypeScript (packages/api-client)
pnpm api-client
```

Migraciones: 0001 núcleo, 0002 enriquecimiento, 0003 código equivalente, 0004 catálogo de atributos, 0005 autenticación, 0006 ventas, 0007 bandejas, 0008 ficha, 0009 aplicaciones.
Tareas: `uv run python -m nexo_api.cli actualizar-ventas` (ClickHouse) · `importar-fotos` (MinIO).
Primer administrador local: `cd apps/api && uv run python -m nexo_api.cli crear-admin <usuario> "<Nombre>"`.
Despliegue: [deploy/README.md](../deploy/README.md).

> TypeScript queda en 6.x: `typescript-eslint` aún no soporta TypeScript 7.
