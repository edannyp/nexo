# IA de vehículos fuera de AutoCare (MercadoExterno)

Paquete de arranque generado desde el repositorio de Nexo. Contiene lo necesario para construir el proceso que registra en
MercadoExterno los vehículos y equipos que AutoCare no tiene, con Claude Code listo para trabajar.

## Para empezar
1. Crea un repositorio con este contenido (`git init`) y ábrelo en VS Code → **Reopen in Container**.
2. Completa `.env` (se crea solo a partir de `.env.example`) y usa **Rebuild Container**.
3. Abre Claude Code (`claude`), inicia sesión y ejecuta **`/arranque`**.

La memoria y el historial de Claude Code viven en el volumen `claude-config`: sobreviven a reconstruir el contenedor.

## Qué hay aquí
| Carpeta | Contenido |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude: contrato y reglas |
| `db/mercado_externo/` | El contrato (con ejemplos de llamadas) y las migraciones reales |
| `db/pruebas/` | Pruebas del contrato |
| `contexto/` | Documentos de gobernanza copiados de Nexo (no se editan aquí) |
| `base-local/` | Script para levantar MercadoExterno local |

## Para el administrador de PostgreSQL (producción, `10.10.60.6`)
```sql
create role ia_vehiculos login password '<contraseña larga>';
grant grp_mercado_registro to ia_vehiculos;   -- base mercado_externo: lee y registra con las funciones
```
