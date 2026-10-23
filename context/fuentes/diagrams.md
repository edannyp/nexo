# Diagrams (`db_diagrams`)

## Qué es
Catálogo de diagramas técnicos (radiadores, intercoolers…) armado con catálogos impresos y scraping (JJ Radiator, NRF, CSF, TYC).
**La APP no lo usa** (ADR 0009): es insumo de la IA y referencia para diseñar Consolidación.

## Quién la mantiene
Proyecto de scraping / IA.

## Acceso
10.20.20.6, base `db_diagrams`, con las credenciales de `CONSOLIDACION_*` del `.env` (solo lectura). Explorado el 2026-10-15 y
el 2026-10-23. Consolidación ya no vive ahí (está en 10.10.60.6).
Las fotos de los diagramas están en MinIO, bucket `rlt-diagramas`; las tablas guardan URLs.

## Tablas / entidades clave
| Tabla | Filas | Contenido |
|---|---|---|
| `datos_maestros` | 7 405 | Un diagrama por `codigo` (único): `pagina`, `parte`, `dpi`, `nissens`, `oem`, `codsap`, `core_size`/`tank_size` (texto), medidas numéricas de panal y tanque, año, marca, modelo, motor, `verificado`, `codigo_equivalente` |
| `compatibilidades` | 119 | Vehículo por diagrama en texto libre (marca, modelo, años, motor, cilindrada, carrocería) |
| `oem_codigos` | 16 313 | OEM por diagrama, con `fuente` y `confianza` (`confirmado`, `revisar_manual`) |
| `proveedor_codigos` | 197* | Código del competidor por diagrama (JJ Radiator, NRF, CSF, TYC) con `url_imagen` externa |
| `proveedor_busqueda_config` | 8 | Plantillas de URL de búsqueda por proveedor |
| `jjradiator_cross_reference` | 6 953 | Diagrama ↔ artículo de JJ (1 a 1): `match_status` (`confirmado` 4 138, `revisar_manual` 2 815), `match_reason` (`oem`, `dimensiones`, `oem_no_coincide`, `sin_evidencia_para_corroborar`) |
| `jjradiator_sin_match` | 354 | Diagramas que no están en JJ, con un equivalente imputado y su confianza |
| `importaciones_pendientes` | 1 363 | Cola de trabajo del scraping |

*Las estadísticas dicen 197 filas, pero el conteo real por proveedor suma ~10 300.

## Llaves para cruzar con SAP
Ninguna: `codsap` está vacío en el 100 %. El cruce posible es por OEM, DPI o código de competidor (`SuppCatNum`).

## Calidad observada
- Vehículos en texto libre y mal clasificados (`marca = 'INTERCOOLER'`); solo 17 diagramas tienen año.
- Medidas: el texto `core_size` es inconsistente (`538X388X68`, `335x608x16/22/26`); solo 1 787 tienen medidas numéricas.
- OEM con ruido (`$55215200`, `2531022050/22070` con varios valores en un campo).
- `confianza` es texto libre; `verificado` solo en 25 diagramas.
- Las URLs de imagen apuntan a CDNs de terceros, que pueden caducar.

## Cómo la usa la APP
No la usa. Las ideas que se toman para Consolidación están en `architecture/datos/modelo-consolidacion.md`.
