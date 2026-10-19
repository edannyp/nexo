# Nexo — puente de gobernanza del artículo

Consola y base de datos para validar y enriquecer el catálogo de artículos automotrices de SAP
(radiadores, intercoolers, condensadores…) con AutoCare (ACES/PIES), el catálogo maestro de Consolidación y MercadoExterno.

> Estado: **arquitectura planificada**; migraciones de la base `nexo` y contratos de Consolidación/MercadoExterno probados.
> La API y la consola web aún no se implementan.

## Por dónde empezar
1. [context/negocio.md](context/negocio.md) y [context/alcance.md](context/alcance.md): qué se construye y qué no (el ETL es otro proyecto).
2. [context/workflow-estados.md](context/workflow-estados.md): la máquina de estados.
3. [architecture/](architecture/): diagrama, capas, borrador del modelo de Nexo, contratos y ADRs.
4. [context/preguntas-abiertas.md](context/preguntas-abiertas.md): lo que falta definir.

## Estructura
```
.devcontainer/   Entorno: Python 3.13, Node 24, uv, pnpm + Postgres 17, Redis, ClickHouse (opcional)
context/         Negocio: objetivo, alcance, workflow, glosario, categorías, fichas de fuentes
architecture/    Técnica: diagramas, capas, modelo de datos, contratos, convenciones API, ADRs, stack
connections/     Clientes de prueba y exploración: Postgres, SAP HANA, MinIO, ClickHouse
db/              Esquemas que gobernamos fuera de Nexo: Consolidación y MercadoExterno (migraciones, contrato, pruebas)
data/            Referencias versionadas, muestras y perfiles de fuentes (no versionados)
apps/            api (FastAPI) y web (React) — se crean tras la planificación
packages/        ui (design system) y api-client (generado)
```

## Arranque
1. Abrir en VS Code → "Reopen in Container" (o Codespaces).
2. Completar `.env` (se copia desde `.env.example` al crear el contenedor).
3. Probar conexiones:
   ```bash
   cd connections
   uv run python -m postgres.smoke_test
   uv run python -m sap.hana.smoke_test
   ```
4. Abrir Claude Code (`claude` en la terminal o la extensión de VS Code) y ejecutar `/arranque` para la sesión de planificación.
5. Perfilar una tabla: `uv run python -m exploration.perfilar --conexion autocare --tabla public.vehicle`

## Claude Code en el contenedor
- Se instala solo (feature `claude-code` del DevContainer) junto con la extensión de VS Code.
- La carpeta `~/.claude` vive en el volumen Docker `claude-config`, así que **el login, la configuración y el historial de sesiones sobreviven a "Rebuild Container"**. Para retomar una conversación: `claude --continue` (la última) o `claude --resume` (elegir).
- Lo que debe compartirse con el equipo va en el repo: `CLAUDE.md`, `.claude/settings.json` y `.claude/commands/`. Lo personal, en `.claude/settings.local.json` (ignorado por git).
- El volumen se pierde solo si se borra a mano (`docker volume rm`). Las sesiones son locales a tu máquina: no viajan con el repo.

| Comando | Para qué |
|---|---|
| `/arranque` | Primera sesión: repasa el contexto y resuelve las preguntas abiertas una por una |
| `/explorar-fuente <nombre>` | Prueba la conexión, perfila tablas y completa la ficha de la fuente |
