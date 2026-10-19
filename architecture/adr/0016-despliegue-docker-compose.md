# 0016. Despliegue con Docker Compose en un servidor interno

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
Usuarios internos (9). Todo lo que consume la APP está en la red interna: Postgres (AutoCare, Consolidación, MercadoExterno),
MinIO (`10.10.10.3:9000`) y SAP HANA. El servidor Postgres **no tiene respaldos** hoy.

## Decisión
- **Docker Compose** en un servidor interno: `api` (FastAPI), `web` (estáticos de la SPA servidos por **Caddy**, que también hace de
  proxy inverso hacia `/api` y da HTTPS interno) y `redis`.
- **Nexo** es una base nueva (`nexo`) en el servidor Postgres existente, junto a las otras bases.
- Ambientes `develop` y `release`, siguiendo el patrón que ya usan (`*-develop` / `*-release`).
- CI (GitHub Actions) construye y publica las imágenes; en el servidor se actualiza con `docker compose pull && docker compose up -d`.
- Las migraciones (Alembic) corren como paso previo al arranque de `api`.
- Configuración solo por variables de entorno (`.env` del servidor, fuera del repositorio).

## Consecuencias
- **Riesgo aceptado (por ahora): sin respaldos.** Nexo guardará trabajo humano que no se puede regenerar (emparejamientos,
  validaciones, equivalencias, bitácora). Se recomienda al menos un `pg_dump` diario de `nexo` y `mercado_externo` antes de
  empezar la operación real.
- No se expone nada a internet.
