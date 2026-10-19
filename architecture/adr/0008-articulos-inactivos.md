# 0008. Artículos inactivos: bandera, fuera de la APP

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
SAP marca artículos dados de baja de forma inconsistente. En alcance (2026-10-15) hay 27 con `frozenFor = 'Y'`
y 7 con "INACTIVO" en el nombre que siguen activos en SAP. Además, un artículo puede salir del alcance
(cambio de categoría o de subcategoría).

## Decisión
- `app.articulo` tiene `activo boolean not null default true` y `motivo_inactivo` (`SAP_CONGELADO` | `NOMBRE_INACTIVO` | `FUERA_DE_ALCANCE`).
- `app.fn_procesar_staging` lo calcula en cada carga: inactivo si `frozenFor = 'Y'`, si la descripción contiene `INACTIV`
  o si el artículo ya no cumple el filtro de `context/categorias.md`. Si vuelve a cumplir, se reactiva.
- La bandera es **ortogonal al estado** del workflow: el artículo conserva su estado, pero:
  - no aparece en bandejas, búsquedas, equivalencias ni catálogos de la APP;
  - no se puede asignar ni transicionar mientras esté inactivo;
  - el proceso de salida no lo publica.
- Nunca se borra. Cada cambio de `activo` queda en la bitácora (`ACTIVADO` / `INACTIVADO`, actor `PROCESO:ETL`).
- Solo un administrador puede verlos, desde la bitácora o un filtro explícito de auditoría.

## Consecuencias
- Las vistas y consultas de la APP filtran `activo = true` por defecto (se recomienda una vista `app.v_articulo_activo`).
- Al reactivarse, si el `hash_control` cambió en el intermedio, se aplica la regla de checksum normal.
