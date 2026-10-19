# 0020. El sistema se llama Nexo

- **Estado:** Aceptada
- **Fecha:** 2026-10-19

## Contexto
"BD_APP" y "APP" eran nombres de trabajo. Con la arquitectura completa quedó claro el propósito: ser el **puente de gobernanza** del
artículo entre SAP (solo lectura), AutoCare (ACES/PIES), el catálogo maestro de Consolidación y MercadoExterno.

## Decisión
- El sistema se llama **Nexo**. La base PostgreSQL es `nexo`, con los mismos esquemas (`staging`, `app`, `audit`, `meta`). "La APP" es la
  API + consola web de Nexo.
- Variables de entorno `NEXO_*` (antes `BD_APP_*`); el proyecto de la API es `nexo-api`.
- Se desarrolla en un repositorio propio (`github.com/edannyp/nexo`, ADR 0021). La consola se construye a mano sobre el stack del ADR 0004; no se usa un generador de UI (Lovable).

## Consecuencias
- Renombrados documentos, migraciones, pruebas, scripts y `.env.example`. Las migraciones no estaban aplicadas en ningún servidor.
- Cada desarrollador renombra en su `.env` las variables `BD_APP_*` → `NEXO_*`.
- El DevContainer crea la base local `nexo` en un volumen nuevo; en uno existente hay que crearla a mano.
