# Modelo de Consolidación (`articulos_consolidacion`)

> **Este esquema gobierna** (ADR 0009, 0011). El proceso de scraping y consolidación (otro desarrollador) se adapta a él.
> Nomenclatura canónica y diccionario de campos (ADR 0007). Versión del documento: borrador 1 (2026-10-15).

## Propósito
Un **catálogo maestro** de piezas del mercado: la unión estandarizada de `db_diagrams` y de todos los proveedores scrapeados,
incluidas las piezas que solo existen en un proveedor. Sirve al operador de la APP para **emparejar** cada artículo SAP con su
pieza de referencia. El emparejamiento **no** vive aquí: vive en Nexo (`app.articulo_parte`).

Consolidación no sabe nada de SAP: no tiene `item_code`, estados del workflow ni datos de operadores.

## Principios
1. **Nada se pierde:** cada pieza se guarda tal como vino (`registro_fuente`) y por separado su versión consolidada (`parte`).
2. **Trazabilidad:** cada número, atributo, aplicación e imagen sabe de qué `registro_fuente` salió.
3. **Estándar AutoCare:** tipo de parte = `part_terminology_id` (PCdb); atributos = `paid` (PAdb) con unidad; vehículos = IDs de VCdb
   o de MercadoExterno (vehículos fuera de AutoCare, IDs ≥ 1 000 000 000, ADR 0014).
   Nunca texto libre donde exista un catálogo; lo que no se pudo homologar va a una tabla de pendientes, no a la principal.
4. **IDs estables:** una `parte` nunca se borra. Si dos partes resultan ser la misma, una se marca `FUSIONADA` y apunta a la otra,
   así las referencias desde Nexo siguen siendo válidas.
5. **Unidades:** longitudes en **mm** y temperaturas en °C; el valor original se conserva en `valor_original`.

## Esquemas
- `catalogo`: tablas del catálogo maestro.
- `carga`: control de corridas del proceso de carga.

## Tablas

### `catalogo.fuente`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `smallint` PK | |
| `codigo` | `text` único | `DB_DIAGRAMS`, `JJ_RADIATOR`, `NRF`, `CSF`, `TYC`, `SPECTRA`, `MANUAL`… |
| `nombre` | `text` | |
| `tipo` | enum `tipo_fuente` | `CATALOGO_PROPIO`, `SCRAPING`, `LISTA_PROVEEDOR`, `MANUAL` |
| `url_base` | `text` | |
| `prioridad` | `smallint` | 1 = más confiable; desempata conflictos |
| `activa` | `boolean` | |

### `catalogo.marca_pieza`
Fabricantes de vehículos (OEM) y de repuestos (aftermarket).
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `integer` PK | |
| `nombre` | `text` | Como se muestra (`NRF`, `Toyota`) |
| `nombre_norm` | `text` único | Mayúsculas, sin signos |
| `tipo` | enum | `OEM`, `AFTERMARKET` |
| `brand_aaiaid` | `text` | ID de marca PIES, cuando exista |

### `carga.corrida`
Una ejecución del proceso de carga por fuente.
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `fuente_id` | FK `fuente` | |
| `iniciada_en` / `terminada_en` | `timestamptz` | |
| `estado` | enum | `EN_PROCESO`, `COMPLETA`, `FALLIDA` |
| `version_proceso` | `text` | Versión del scraper o consolidador |
| `leidos`, `insertados`, `actualizados`, `sin_cambios`, `errores` | `integer` | |
| `notas` | `text` | |

### `catalogo.registro_fuente`
La pieza **tal como viene** de su fuente.
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `fuente_id` | FK `fuente` | |
| `id_en_fuente` | `text` | Código de diagrama, SKU del proveedor. **Único con `fuente_id`** |
| `url` | `text` | Página de origen |
| `descripcion_original` | `text` | |
| `datos_crudos` | `jsonb` | Todo lo capturado, sin transformar |
| `hash_contenido` | `text` | sha256 de `datos_crudos`; detecta cambios entre corridas |
| `parte_id` | FK `parte` | Parte consolidada a la que pertenece (`null` = aún sin consolidar) |
| `vinculo_metodo` | enum | `NUMERO`, `MEDIDAS_APLICACION`, `MANUAL` |
| `vinculo_confianza` | `numeric(4,3)` | 0–1 |
| `vigente` | `boolean` | `false` si la fuente ya no lo publica (nunca se borra) |
| `corrida_id` | FK `carga.corrida` | Última corrida que lo tocó |
| `capturado_en` / `actualizado_en` | `timestamptz` | |

### `catalogo.parte`
La pieza consolidada (*golden record*).
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | **Estable**: Nexo lo referencia |
| `part_terminology_id` | `integer` not null | PCdb (2172 Radiator, 6708 A/C Condenser…) |
| `descripcion` | `text` | Generada a partir de tipo, marca principal y medidas |
| `estado` | enum | `ACTIVA`, `FUSIONADA`, `DESCARTADA` |
| `fusionada_en_id` | FK `parte` | Obligatorio si `estado = FUSIONADA` |
| `creado_en` / `actualizado_en` | `timestamptz` | |

### `catalogo.parte_numero`
Números con los que se conoce la pieza: la llave principal para emparejar.
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `parte_id` | FK `parte` | |
| `registro_fuente_id` | FK `registro_fuente` | De dónde salió |
| `tipo` | enum `tipo_numero` | `OEM`, `DPI`, `PROVEEDOR`, `INTERCAMBIO`, `REEMPLAZADO` |
| `marca_pieza_id` | FK `marca_pieza` | De quién es el número (Toyota, NRF…); `null` en DPI |
| `numero` | `text` | Tal como viene (`16400-35150`) |
| `numero_norm` | `text` | Mayúsculas, solo `[A-Z0-9]` (`1640035150`). Índice B-tree + `pg_trgm` |
| `confianza` | `numeric(4,3)` | |

Único: (`parte_id`, `tipo`, `marca_pieza_id`, `numero_norm`, `registro_fuente_id`).

### `catalogo.parte_atributo`
Atributos PIES (PAdb).
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `parte_id` | FK `parte` | |
| `registro_fuente_id` | FK `registro_fuente` | |
| `paid` | `integer` | PAdb (`267` Core Height, `302` Core Material…), válido para el `part_terminology_id` |
| `valor_num` | `numeric` | Para atributos numéricos, ya en la unidad canónica |
| `uom_code` | `text` | Unidad PAdb (`MM`…) |
| `valid_value_id` | `integer` | Para atributos de lista PAdb |
| `valor_texto` | `text` | Para atributos libres |
| `valor_original` | `text` | Como venía (`335x608x16/22/26`, `16 in`) |

Check: al menos uno de `valor_num`, `valid_value_id`, `valor_texto`.

### `catalogo.parte_aplicacion`
En qué vehículos va la pieza (ACES). **Lo que importa es el vehículo; la región es opcional.**
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `parte_id` | FK `parte` | |
| `registro_fuente_id` | FK `registro_fuente` | |
| `base_vehicle_id` | `integer` | VCdb: año + marca + modelo. IDs ≥ 1 000 000 000 = extensión custom (ADR 0014) |
| `equipment_base_id` | `integer` | VCdb equipos (plantas, maquinaria). **Exactamente uno** de los dos |
| `sub_model_id` | `integer` | Opcional |
| `engine_config_id` | `integer` | Opcional (calificador de motor) |
| `transmission_id` | `integer` | Opcional |
| `posicion_id` | `integer` | PCdb position, si aplica |
| `cantidad` | `smallint` | Piezas por vehículo |
| `notas` | `text` | Calificadores no estructurados |
| `vcdb_version` | `text` | Versión de VCdb usada al homologar |

Las regiones van en la tabla de detalle siguiente; una aplicación sin regiones vale para el vehículo en general.

### `catalogo.parte_aplicacion_region`
Regiones (mercados) en las que una fuente confirma la aplicación. Es **opcional**: puede haber 0, 1 o varias por aplicación.
| Columna | Tipo | Notas |
|---|---|---|
| `parte_aplicacion_id` | FK `parte_aplicacion` | PK compuesta con `region_id` y `registro_fuente_id` |
| `region_id` | `integer` | VCdb `region` (GTM, SLV, USA…) |
| `registro_fuente_id` | FK `registro_fuente` | Qué fuente lo confirma |

En qué regiones **existe** el vehículo no se copia: se consulta en VCdb (`vcdb_base.vehicle` por `base_vehicle_id`).

### `catalogo.aplicacion_sin_homologar`
Vehículos que trae la fuente pero que no se pudieron llevar a un `base_vehicle_id`.
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `parte_id`, `registro_fuente_id` | FK | |
| `marca_texto`, `modelo_texto`, `anio_desde`, `anio_hasta`, `motor_texto`, `otros_texto` | | Como vino |
| `motivo` | enum | `MARCA_DESCONOCIDA`, `MODELO_DESCONOCIDO`, `ANIOS_FALTANTES`, `AMBIGUO` |

### `catalogo.parte_imagen`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `parte_id`, `registro_fuente_id` | FK | |
| `tipo` | enum | `FOTO`, `DIAGRAMA`, `DIBUJO_TECNICO` |
| `url` | `text` | URL externa o de MinIO |
| `minio_bucket` / `minio_objeto` | `text` | Si está en MinIO (`rlt-diagramas`) |
| `orden` | `smallint` | |

### `catalogo.conflicto`
Discrepancias entre fuentes que el proceso detecta y no resuelve solo.
| Columna | Tipo | Notas |
|---|---|---|
| `id` | `bigint` PK | |
| `parte_id` | FK `parte` | |
| `tipo` | enum | `NUMERO_DUPLICADO`, `ATRIBUTO_DISCREPA`, `APLICACION_DISCREPA`, `POSIBLE_FUSION` |
| `detalle` | `jsonb` | Valores en conflicto y sus `registro_fuente_id` |
| `estado` | enum | `ABIERTO`, `RESUELTO`, `DESCARTADO` |
| `resuelto_en`, `resolucion` | | |

## Vistas para la APP
- `catalogo.v_parte_busqueda`: una fila por parte `ACTIVA`, con números concatenados, medidas principales (alto, largo y ancho del panal),
  conteo de aplicaciones y fuentes, e imagen principal. Es la base del buscador de emparejamiento.
- La APP busca por: `numero_norm` (exacto y trigram), rango de medidas (± tolerancia en mm), `base_vehicle_id`
  y `part_terminology_id` (el del filtro global, ADR 0010).

## Reglas del contrato para el proceso de carga
1. *Upsert* por (`fuente_id`, `id_en_fuente`); si `hash_contenido` no cambió, no se toca nada.
2. Nunca `DELETE`: lo que desaparece de la fuente queda `vigente = false`; las partes se `FUSIONAN` o `DESCARTAN`.
3. Toda corrida abre y cierra un `carga.corrida`.
4. Los valores se validan contra AutoCare: `part_terminology_id` existe, `paid` está asignado a ese tipo de parte, `valid_value_id` es válido, `base_vehicle_id` existe.
5. Lo que no se puede estandarizar va a `datos_crudos` o a `aplicacion_sin_homologar`, nunca a las columnas estándar.

## Permisos
- `consolidacion_carga`: escritura en `catalogo` y `carga` (el proceso del otro desarrollador).
- `app_lectura`: solo `SELECT` en las vistas y tablas de `catalogo`.
- DDL solo vía migraciones de este repositorio.

## Implementación
El DDL versionado es la **fuente de verdad**: `db/consolidacion/migraciones/`. Contrato operativo, diagrama y ejemplo real:
`db/consolidacion/README.md`. Además del diseño de arriba, el DDL agrega el esquema `ref` (copia de AutoCare para validar en la base)
y triggers que hacen cumplir las reglas.

## Pendiente
- Reglas de deduplicación (cuándo dos `registro_fuente` son la misma `parte`): acordarlas con el desarrollador del flujo.
