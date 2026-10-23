# Carga del catálogo maestro (Consolidación)

Paquete de arranque generado desde el repositorio de Nexo. Contiene lo necesario para construir el proceso que llena el catálogo
maestro de piezas (`articulos_consolidacion`) desde los diagramas y los proveedores, con Claude Code listo para trabajar.

## Para empezar
1. Crea un repositorio con este contenido (`git init`) y ábrelo en VS Code → **Reopen in Container**.
2. Completa `.env` (se crea solo a partir de `.env.example`) y usa **Rebuild Container**.
3. Abre Claude Code (`claude`), inicia sesión y ejecuta **`/arranque`**.

La memoria y el historial de Claude Code viven en el volumen `claude-config`: sobreviven a reconstruir el contenedor.

## Qué hay aquí
| Carpeta | Contenido |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude: contrato, lo que Nexo necesita y reglas |
| `db/consolidacion/` | El contrato, las migraciones reales y el ejemplo de carga |
| `db/pruebas/` | Pruebas del contrato |
| `db/mercado_externo/` | Referencia: vehículos fuera de AutoCare (IDs ≥ 1 000 000 000) que puedes usar si ya existen; no se registran desde aquí |
| `contexto/` | Documentos de gobernanza copiados de Nexo (no se editan aquí) |
| `base-local/` | Script para levantar Consolidación local |

## Para los administradores de PostgreSQL
**Consolidación (`10.10.60.6`, PostgreSQL 18)**, donde escribe el proceso:
```sql
create role consolidacion_carga login password '<contraseña larga>';
grant grp_consolidacion_carga to consolidacion_carga;   -- base consolidacion_articulos: escribe catalogo y carga
```
**Fuentes (`10.20.20.6`)**, solo lectura: un usuario con `connect` y `select` en `db_diagrams` y `db_scrapper` (las tablas que
lee el proceso) y en `autocare_global`. La contraseña se entrega por un canal seguro; nunca va en el repositorio.
