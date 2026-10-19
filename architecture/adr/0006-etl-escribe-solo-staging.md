# 0006. El ETL de entrada escribe solo en staging; Nexo define el contrato

- **Estado:** Aceptada (amplía la 0002)
- **Fecha:** 2026-10-15

## Contexto
El ETL SAP → Nexo vive en otro proyecto (ADR 0002). Si escribe directo en las tablas de trabajo,
puede saltarse la máquina de estados, la bitácora y la regla de checksum.

## Decisión
- Nexo es dueña del contrato: el otro proyecto se adapta a `architecture/datos/contratos.md`.
- El ETL solo escribe en `staging.articulo_sap` y después invoca `app.fn_procesar_staging(lote_id)`.
- Todo cambio en `app.articulo` (alta, regreso a `PENDIENTE` por cambio de hash, inactivación) lo hace esa función,
  usando la misma función de transición que la APP y registrando el cambio en la bitácora.
- Los artículos que salen del filtro se marcan `inactivo`; nunca se borran.

## Consecuencias
- El usuario de base de datos del ETL solo tiene `INSERT/UPDATE` en `staging` y `EXECUTE` sobre la función.
- El filtro de categorías se aplica dos veces (ETL y Nexo); un cambio de alcance se actualiza en ambos lados.
- Las pruebas de la función se hacen con datos de muestra en `staging`, sin depender de SAP.
