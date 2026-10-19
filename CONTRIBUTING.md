# Cómo colaborar en Nexo

Repositorio: `github.com/edannyp/nexo`. Ver ADR 0021.

## Ramas (Gitflow)
| Rama | Para qué | Sale de | Se integra en |
|---|---|---|---|
| `main` | Lo que corre en el servidor. Cada merge lleva etiqueta `vX.Y.Z` | — | — |
| `develop` | Integración del trabajo terminado | `main` | `main` (vía `release/*`) |
| `feature/<tema>` | Una funcionalidad o cambio acotado (`feature/catalogo-atributos`) | `develop` | `develop` |
| `release/<X.Y.Z>` | Preparar una versión: solo ajustes y documentación | `develop` | `main` y `develop` |
| `hotfix/<tema>` | Corrección urgente de lo que está en producción | `main` | `main` y `develop` |

- `main` y `develop` no reciben commits directos: todo entra por Pull Request.
- Antes de pedir el merge, pasan las pruebas: `cd apps/api && uv run pytest` y `uv run db/pruebas/probar.py --host postgres`.

## Commits
- **Granulares:** un cambio lógico por commit (una migración, un documento, un ajuste de prueba). Si el mensaje necesita "y además…", son dos.
- **Autor:** el usuario de GitHub de quien hace el commit. Los agentes (Claude) **no** hacen commits ni push: preparan los cambios y proponen
  los mensajes.
- **Mensaje** con [Conventional Commits](https://www.conventionalcommits.org/es/), en español:
  ```
  <tipo>(<ámbito>): <resumen en imperativo, ≤ 72 caracteres>

  <por qué, si no es obvio>
  ```
  Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `ci`. Ámbitos: `nexo-db`, `api`, `web`, `consolidacion`,
  `mercado-externo`, `conexiones`, `arquitectura`, `contexto`, `devcontainer`.
  Ejemplo: `feat(nexo-db): agregar catálogo configurable de atributos PIES`.

## Nunca se versiona
`.env`, datos de `data/` (salvo README), capturas con información comercial (`especificaciones.png`) ni credenciales de servidores.
