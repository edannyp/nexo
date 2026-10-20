# Agente de revisión del catálogo (Consolidación → verificaciones de Nexo)

Paquete de arranque generado desde el repositorio de Nexo. Contiene lo necesario para construir el agente de IA que compara lo validado
en Nexo con el catálogo maestro y deja en Nexo las verificaciones de lo que cambió, con Claude Code listo para trabajar.

## Para empezar
1. Crea un repositorio con este contenido (`git init`) y ábrelo en VS Code → **Reopen in Container**.
2. Completa `.env` (se crea solo a partir de `.env.example`) y usa **Rebuild Container**.
3. Abre Claude Code (`claude`), inicia sesión y ejecuta **`/arranque`**.

La memoria y el historial de Claude Code viven en el volumen `claude-config`: sobreviven a reconstruir el contenedor.

## Qué hay aquí
| Carpeta | Contenido |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude: contrato, cómo decidir y reglas |
| `contexto/` | Documentos de gobernanza copiados de Nexo (no se editan aquí) |
| `base-local/` | Nexo y Consolidación locales, con datos de ejemplo enlazados |
| `db/` | Migraciones de Consolidación (para la base local) |

## Para los administradores de PostgreSQL (producción)
En `10.10.60.6`, base `nexo`, como superusuario:
```bash
psql -h 10.10.60.6 -U postgres -d nexo -v clave='<contraseña larga>' -f base-local/sql/usuario-agente-revision-catalogo.sql
```
En `10.20.20.6`, lectura de Consolidación:
```sql
create role agente_revision_lectura login password '<contraseña larga>';
grant grp_app_lectura to agente_revision_lectura;
```
