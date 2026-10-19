# 0011. Consolidación es un catálogo maestro; el emparejamiento vive en Nexo

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
- El propósito de Consolidación es **juntar** `db_diagrams` con todos los proveedores scrapeados en un catálogo completo y estandarizado,
  incluidas las piezas que solo existen en un proveedor. Otro desarrollador mantiene ese flujo.
- `rlt` (en `autocare_global`) es un proyecto aparte de búsqueda de compatibilidades. **No entra en este proyecto.**
- Prueba de cruce por número (2026-10-15, radiadores activos): el 50 % de los Importados coincide con `db_diagrams` por DPI/OEM;
  los Fabricados casi no coinciden (6 de 2 021).

## Decisión
- `articulos_consolidacion` es un **catálogo maestro**: `registro_fuente` (lo que trae cada fuente) → `parte` (pieza consolidada),
  con números, atributos PAdb, aplicaciones ACES e imágenes. Esquema en `architecture/datos/modelo-consolidacion.md`.
- **Nuestro esquema gobierna**: el proceso del otro desarrollador se adapta a él.
- Consolidación no conoce SAP. El **emparejamiento** artículo SAP ↔ `parte` lo hace el **operador en la APP**
  y se guarda en Nexo (`app.articulo_parte`).
- Aplicaciones por **vehículo** (`base_vehicle_id` + calificadores). Las regiones son opcionales y van en una tabla de detalle
  (`parte_aplicacion_region` / `articulo_aplicacion_region`), una fila por región. Las regiones en que existe el vehículo se consultan en VCdb.
- Los Fabricados se emparejan sobre todo a través de su Importado equivalente (ADR 0005).

## Consecuencias
- La APP necesita un buscador sobre Consolidación (por número, medidas y vehículo) dentro de la consola Master Merge.
- `db_diagrams` pasa a ser una fuente más del catálogo maestro.
- El paso `PENDIENTE → POR_VALIDAR` lo hace el operador al terminar de emparejar (ADR 0012).
