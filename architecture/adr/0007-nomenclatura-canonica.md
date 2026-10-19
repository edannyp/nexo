# 0007. Nomenclatura canónica en Nexo (no se heredan los nombres de SAP)

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
SAP usa nombres crípticos y mezclados (`U_SubSubCat`, `SHght1Unit`, `U_TransmissionOilCoolerIncluded`), valores
codificados (`S/N`, `AT/MT`, `P/M/G`) y unidades mezcladas (1 218 artículos en mm y 2 523 en cm). La APP también
cruza AutoCare (Make/Model/Year) y Consolidación, y no debe acoplarse a SAP.

## Decisión
- Nexo y la APP usan una **nomenclatura canónica en español**; el mapeo con cada fuente vive solo en
  `architecture/datos/mapeo-fuentes.md`.
- Reglas de nombres:
  - `snake_case`, sin abreviaturas ni prefijos de origen (`U_`, `S`).
  - Llaves foráneas: `<entidad>_id`. Códigos externos: `<cosa>_codigo`.
  - Medidas con unidad en el nombre y unidad única: `panal_alto_mm`, `panal_largo_mm`, `panal_ancho_mm` (el nombre dice **qué** se midió).
  - Booleanos: `es_*`, `incluye_*`, `tiene_*`. Timestamps: `*_en` (`creado_en`). Fechas sin hora: `fecha_*`.
  - Enums en MAYÚSCULAS, español y singular: `IMPORTADO`, `AUTOMATICA`, `HORIZONTAL`.
  - Vocabulario de vehículo alineado a AutoCare: `marca_vehiculo` (Make), `modelo_vehiculo` (Model), `anio_desde`/`anio_hasta`.
- El ETL escribe en `staging` **ya con los nombres canónicos**, pero con valores crudos y su unidad original. Toda
  normalización de valores (unidades, enums, S/N) ocurre en Nexo, en un solo lugar.
- El API expone los mismos nombres (ver `architecture/api/convenciones.md`).

### Diccionario de campos
- Cada columna que viene de otra fuente registra **cómo se llama en el origen**, en la tabla `meta.diccionario_campo`:
  `esquema`, `tabla`, `columna` (canónica), `fuente` (SAP, AUTOCARE, CONSOLIDACION…), `tabla_origen` (`OITM`),
  `campo_origen` (`U_SubSubCat`), `transformacion`, `en_hash` (bool), `descripcion`.
- Además, cada columna lleva `COMMENT ON COLUMN … IS 'SAP: OITM.U_SubSubCat — …'`, para que se vea en cualquier cliente SQL.
- El diccionario se genera desde `mapeo-fuentes.md` en las migraciones. `fn_procesar_staging` toma de ahí qué columnas
  entran al hash (`en_hash`), así que la lista vive en un solo lugar.

## Consecuencias
- Si SAP agrega o renombra un UDF, solo cambian el ETL y el mapeo; la APP no se entera.
- El `hash_control` se calcula sobre valores normalizados, así que los cambios cosméticos no reabren artículos.
- Cada fuente nueva debe documentar su mapeo antes de usarse.
