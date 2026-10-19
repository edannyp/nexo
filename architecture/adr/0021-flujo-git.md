# 0021. Gitflow, commits granulares y autoría humana

- **Estado:** Aceptada
- **Fecha:** 2026-10-19

## Contexto
Nexo vive en un repositorio propio (`github.com/edannyp/nexo`) y se despliega en un servidor interno con Docker Compose (ADR 0016),
clonando el repositorio. Trabajan personas y agentes de IA.

## Decisión
- **Gitflow:** `main` (servidor, con etiquetas de versión), `develop` (integración), `feature/*`, `release/*`, `hotfix/*`. Todo entra por
  Pull Request.
- **Commits granulares** con Conventional Commits en español (`CONTRIBUTING.md`).
- **Autoría humana:** los commits y los push los hace el responsable con su usuario de GitHub. Los agentes preparan los cambios y
  proponen la división en commits y sus mensajes, pero no ejecutan `git commit` ni `git push`.
- Las credenciales del servidor no se comparten con los agentes ni se versionan.

## Consecuencias
- El historial refleja quién decidió cada cambio y se puede revisar por partes.
- El despliegue es reproducible: el servidor solo hace `git pull` de `main` y `docker compose up`.
