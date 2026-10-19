# Stack

| Área | Elección | Razón |
|---|---|---|
| Repositorio | Monorepo: **uv** (Python) + **pnpm** (TS) | API, cliente y UI cambian juntos en un mismo PR. |
| Backend | **Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2** | OpenAPI automático; mejores drivers para HANA, ClickHouse y la integración con IA. |
| Base de datos | **PostgreSQL 17** con `pg_trgm`, `unaccent`, JSONB | Búsqueda difusa y metadatos variables. |
| Sesiones / caché | **Redis 7** | Revocación inmediata de sesiones; locks de asignación. |
| Frontend | **React 19, TypeScript, Vite** (SPA) | Consola interna, sin necesidad de SSR. |
| Routing y datos | **TanStack Router / Query / Table** | Rutas tipadas, caché de servidor, tablas grandes. |
| UI | **shadcn/ui (Radix) + Tailwind CSS v4 + Storybook** | Componentes accesibles y propios; tokens de diseño centralizados. |
| Formularios | **React Hook Form + Zod** | Validación tipada. |
| Cliente API | **orval** desde OpenAPI | Tipos y hooks generados. |
| Calidad Python | **ruff, mypy, pytest, testcontainers** | |
| Calidad TS | **ESLint, Prettier, Vitest, Testing Library, Playwright** | |
| Git hooks | **lefthook** + Conventional Commits | |
| CI | **GitHub Actions** + **Renovate** | |
| Despliegue | **Docker Compose** en servidor interno + **Caddy** (ADR 0016) | Usuarios internos, todo en la misma red. |
| Login | Propio, **Argon2id** (ADR 0015) | Por ahora; adaptador para SSO después. |
| Almacenamiento de fotos | **MinIO** (S3) vía `boto3` (ADR 0013) | Ya existe en la red interna. |

Fuera del stack de este repo: Celery u otro orquestador de ETL (vive en el otro proyecto).
