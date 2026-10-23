# Scraping (`db_scrapper`: JJ Radiator)

## Qué es
Catálogo de JJ Radiator scrapeado de su sitio, en capas bronze (`jjradiators.*`) y silver (`jjradiators_silver.*`). Es una fuente
del catálogo maestro (ADR 0026): la APP no la lee; la carga del proceso 2 la lleva a Consolidación.

## Quién la mantiene
El proyecto de scraping / IA (mismo desarrollador del proceso 2). Usa un agente de IA (tablas `public.checkpoint_*`, LangGraph).

## Acceso
10.20.20.6, base `db_scrapper`, con las credenciales de `CONSOLIDACION_*` del `.env` (solo lectura). Explorada el 2026-10-23.

## Tablas / entidades clave
| Tabla | Filas | Contenido |
|---|---|---|
| `jjradiators_silver.articulos` | 15 513 | Un artículo por `code` de JJ: `brand`, `tipo_producto`, `image_url` (jjradiator.com), `detail_url` |
| `jjradiators_silver.articulo_detalle` | 15 513 | `vehicle_raw` (texto libre), `core_size`, `tank_size`, `dpi`; las columnas `marca`, `modelo`, años y `vehicle_id` están vacías |
| `jjradiators_silver.articulo_oem` | 14 420 | OEM por artículo con `estado_verificacion` (`pendiente`, `confirmado_*`, `inconcluso`, `descartado_manual`), `razon` y `evidencia` |
| `jjradiators_silver.articulo_relacionado` | 117 637 | Artículos relacionados de JJ (variantes), con el vehículo en texto |
| `jjradiators.*` | | Capa bronze (crudo del sitio) |
| `public.staging_radiadores` | 7 262 | Diagramas leídos por IA desde la imagen: medidas numéricas, OEM, DPI, modelos |
| `public.silver_pieza`, `silver_numero`, `silver_conflicto` | ~60–115 | Prueba de verificación por IA con evidencia web |
| `spectra.*` | 0 | Otra fuente, aún vacía |

Tipos de producto: Radiator 6 562, Thermostat & Water Flangers 2 685, Radiator Tanks 2 666, AC Condensers 1 651, Fuel & Expansion
Tank Caps 747, Truck Radiator 448, Caps & Filler Necks 339, Intercooler 321, Repair Tools 94. En alcance (ADR 0026): ~11 650.

## Llaves para cruzar
- Con los diagramas: `db_diagrams.jjradiator_cross_reference` (6 953 cruces 1 a 1; `confirmado` por OEM o dimensiones, o
  `revisar_manual`).
- Con SAP: OEM, DPI o código de JJ en `SuppCatNum` (lo hace el operador en Nexo).

## Calidad observada
- Vehículo solo en texto libre y mezclado: `ISUZU NPR 4.8 MT`, `A6/S6 1.8I20V'94-97 ADR AT`, en chino (`沃尔沃360`) o solo la marca.
- OEM: 9 063 de 11 600 en nuestros tipos están `pendiente`; ~2 500 confirmados; algunos rotos (`-`, `11061-`).
- Medidas en texto con `×` o `x` y espesor doble (`375×728×16/26`); `core_size` en 8 221 artículos.
- Imágenes en el CDN de JJ: pueden caducar (se copian a MinIO, ADR 0026).

## Cómo la usa la APP
No la usa: llega a Nexo a través de Consolidación.
