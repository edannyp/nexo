# ETL de entrada SAP → Nexo

Paquete de arranque generado desde el repositorio de Nexo. Contiene lo necesario para construir el ETL que lleva los artículos de
SAP Business One al esquema `staging` de Nexo, con Claude Code listo para trabajar.

## Para empezar
1. Crea un repositorio con este contenido (`git init`) y ábrelo en VS Code → **Reopen in Container** (requiere Docker y la extensión
   Dev Containers).
2. Completa `.env` (se crea solo a partir de `.env.example`) y usa **Rebuild Container** para cargar las variables.
3. Abre Claude Code (`claude`), inicia sesión y ejecuta **`/arranque`**: revisa el contexto, levanta la base local y propone el plan.

La memoria y el historial de Claude Code viven en un volumen de Docker (`claude-config`): sobreviven a reconstruir el contenedor.

**Empieza por `ENTREGA.md`:** qué recibes, qué pedir, las etapas y cuándo está terminado.

## Qué hay aquí
| Carpeta | Contenido |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude: alcance, contrato y reglas |
| `contexto/` | Documentos de gobernanza copiados de Nexo (no se editan aquí) |
| `base-local/` | Base `nexo` local idéntica a la de producción y consultas de verificación |
| `referencia/` | La lectura de SAP con la que se verificó Nexo (no es el ETL) |

## Para el administrador de PostgreSQL (producción)
El usuario del ETL se crea una vez en `10.10.60.6`, base `nexo`, como superusuario:
```bash
psql -h 10.10.60.6 -U postgres -d nexo -v clave='<contraseña larga>' -f base-local/sql/usuario-etl.sql
```
Queda `etl_entrada`: escribe solo en `staging` y ejecuta `app.fn_procesar_staging`.
