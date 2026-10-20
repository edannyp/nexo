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
| `db/mercado_externo/` | Para registrar vehículos que no están en AutoCare (regla 10 del contrato) |
| `contexto/` | Documentos de gobernanza copiados de Nexo (no se editan aquí) |
| `base-local/` | Script para levantar Consolidación local |

## Para el administrador de PostgreSQL (producción, `10.20.20.6`)
```sql
create role consolidacion_carga login password '<contraseña larga>';
grant grp_consolidacion_carga to consolidacion_carga;   -- base articulos_consolidacion: escribe catalogo y carga
-- Lectura de las fuentes:
grant connect on database db_diagrams to consolidacion_carga;
grant connect on database autocare_global to consolidacion_carga;
```
Más el `SELECT` en las tablas de `db_diagrams` y `autocare_global` que use el proceso. Para la regla 10, en `mercado_externo`:
`grant grp_mercado_registro to consolidacion_carga;`.
