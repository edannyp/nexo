# 0004. Frontend React SPA con design system propio

- **Estado:** Propuesta
- **Fecha:** 2026-10-15

## Contexto
Consola interna con tablas densas, vistas lado a lado y mucho uso de teclado. No requiere SEO.

## Decisión
React 19 + Vite + TanStack (Router, Query, Table) + shadcn/ui + Tailwind v4, con el design system en `packages/ui` documentado en Storybook.

## Consecuencias
Sin servidor de render; despliegue como estáticos. Alternativa descartada: Next.js (SSR innecesario para una consola autenticada).
