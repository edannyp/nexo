# 0001. Monorepo con uv y pnpm

- **Estado:** Propuesta
- **Fecha:** 2026-10-15

## Contexto
La API, el cliente TypeScript generado y el frontend cambian juntos. Además, el contexto de negocio y la arquitectura deben estar junto al código para que personas y agentes lo encuentren.

## Decisión
Un solo repositorio: `apps/api` (Python, uv), `apps/web` y `packages/*` (TypeScript, pnpm), con `context/`, `architecture/` y `connections/` en la raíz.

## Consecuencias
Un PR puede cambiar contrato, cliente y pantalla a la vez. CI debe filtrar por rutas para no correr todo en cada cambio.
