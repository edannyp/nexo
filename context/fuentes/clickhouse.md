# ClickHouse (ventas y analítica de la empresa)

## Qué es
Almacén analítico de la empresa. Para Nexo es una fuente **de apoyo** y de **solo lectura** (pregunta 8, ADR 0022): de ahí salen las
unidades vendidas por artículo para los indicadores relativos de venta. Explorado el 2026-10-19 (ClickHouse 26.6).

## Acceso
`CLICKHOUSE_HOST`, `CLICKHOUSE_PORT` (8123), `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD` en el `.env`. Prueba: `cd connections && uv run python -m clickhouse.smoke_test`.

## Tablas que usa Nexo
| Tabla | Para qué | Columnas que se leen |
|---|---|---|
| `rlt_mov.mart_ventas_articulo_mes` | Unidades vendidas por artículo, mes y sucursal (desde 2020-09; se actualiza a diario) | `id_articulo` (= `ItemCode`), `mes`, `unidades`, `ultima_venta` |
| `rlt_ml.latest_clasificacion_abcxyz` | Clasificación ABC-XYZ **global** de la empresa (por volumen), como referencia | `id_articulo`, `categoria_abcxyz`, `execution_date` |

**Nunca** se leen montos (`venta_neta`, `venta_neta_qtz`): los indicadores son relativos (ADR 0022).

## Cómo llega a Nexo
`python -m nexo_api.cli actualizar-ventas` (a diario, en el servidor de Nexo) copia a `app.venta_mensual` las unidades de los dos últimos periodos (por defecto 24 meses) de
los artículos que existen en Nexo, y a `app.venta_referencia` la clasificación ABC-XYZ de la empresa. En `app.v_indicador_venta`, la
**clase A/B/C es la de esa clasificación** (ADR 0023); el top %, la participación y la tendencia frente al periodo anterior se calculan
**dentro de cada tipo** (categoría + línea) con las unidades. `rlt_ml.latest_clasificacion_abcxyz_seg` la trae por ámbito (hoy solo
`radiadores_importados`).

## Cobertura (2026-10-19)
Con venta en los últimos 12 meses: 657 de 1 095 radiadores importados y 710 de 2 028 fabricados. En radiadores importados, 118 artículos
(clase A) suman el 80 % de las unidades.

## Otras tablas (no usadas por Nexo)
`rlt_mir` (existencias diarias, tránsito, consumo), `rlt_ml` (pronósticos, punto de reorden), `rlt_bl` (compras sugeridas), `rlt_crm`.
Pueden servir más adelante para priorizar; cualquier uso nuevo se decide con un ADR.
