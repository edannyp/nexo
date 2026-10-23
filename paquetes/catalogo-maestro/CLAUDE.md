# Guía para agentes — Carga del catálogo maestro (Consolidación)

## Qué es este repositorio
El proceso que llena **Consolidación** (`consolidacion_articulos`), el catálogo maestro de piezas del mercado: une los diagramas
propios (`db_diagrams`) y JJ Radiator (`db_scrapper`), estandarizados con AutoCare (PCdb, PAdb, VCdb).
**El esquema lo gobierna Nexo** (otro repositorio): este proceso se adapta a él, no al revés.

Nexo lee Consolidación para que los operadores **emparejen** cada artículo de SAP con una parte del catálogo. Lo que cargues aquí
es lo que verán como candidatos, con un puntaje. Por eso importa tanto la calidad de las medidas, los números y las aplicaciones.

Lee antes de proponer o escribir código:
1. `db/consolidacion/README.md`: **el contrato** (14 reglas; las marcadas 🔒 las hace cumplir la base y fallan con `CONTRATO: …`).
2. `contexto/arquitectura/adr/0026-carga-catalogo-maestro.md`: las decisiones de esta carga (tipos, misma pieza, OEM, vehículos,
   medidas, imágenes, corridas, prioridad).
3. `db/consolidacion/ejemplos/ejemplo_carga.md` y `.sql`: tres diagramas reales cargados según el contrato, paso a paso.
4. `contexto/fuentes/diagrams.md` y `contexto/fuentes/scraping.md`: qué trae cada fuente y sus problemas de calidad.

## Las fuentes (10.20.20.6, solo lectura)
| Fuente (`catalogo.fuente`) | Base | Qué se lee | Prioridad |
|---|---|---|---|
| `DB_DIAGRAMS` | `db_diagrams` | `datos_maestros` (7 405 diagramas), `oem_codigos`, imágenes en MinIO `rlt-diagramas` | 1 |
| `JJ_RADIATOR` | `db_scrapper` | `jjradiators_silver.articulos`, `articulo_detalle`, `articulo_oem` | 2 |
| (cruce) | `db_diagrams` | `jjradiator_cross_reference`: qué diagrama es qué artículo de JJ | — |

Las dos fuentes ya vienen creadas en la base (migración V004). Fuentes nuevas (NRF, CSF, TYC…) se acuerdan antes con Nexo.

## Cada corrida, por fuente
1. `insert into carga.corrida (fuente_id, version_proceso, completa) values (…, …, true) returning id` → **foto completa**.
2. *Upsert* de **todos** los registros de la fuente en `catalogo.registro_fuente` por (`fuente_id`, `id_en_fuente`), con sus
   números, atributos, aplicaciones e imágenes. **Siempre** actualiza `corrida_id` y `vigente = true`, aunque nada haya cambiado:
   así la base sabe que lo viste.
3. Conteos en la corrida (`leidos`, `insertados`, `actualizados`, `sin_cambios`, `errores`).
4. `select carga.fn_cerrar_corrida(corrida_id)` → `{no_vigentes, conflictos}`: marca no vigente lo que no vino, abre conflictos de
   medidas y deja la corrida `COMPLETA`. **Regístralo** en el log.

Si `fn_cerrar_corrida` responde `CORRIDA_INCOMPLETA` (quedaría no vigente más del 5 % de la fuente, y más de 10), no aplicó
nada: marca la corrida `FALLIDA`, alerta y **no reintentes a ciegas**. Casi siempre es un scraping cortado o una consulta vacía.

## Lo que puede pasar y qué se hace
| En la fuente pasa… | Qué haces tú | Qué hace la base |
|---|---|---|
| Artículo de JJ de un tipo fuera de alcance (termostato, tapón, herramienta) | No se carga | — |
| Radiator / Truck Radiator, AC Condensers, Intercooler, Radiator Tanks | Parte con 2172, 6708, 12616 o 48305/17700/17701 | 🔒 Rechaza un tipo que no esté en PCdb o esté obsoleto |
| Diagrama y JJ con cruce `confirmado` | Los dos registros a la misma parte, `vinculo_confianza` 1,0 | — |
| Cruce `revisar_manual` | Misma parte, `vinculo_confianza` 0,5; si el OEM no coincide, conflicto `NUMERO_DUPLICADO` con los dos OEM | — |
| Diagrama o JJ sin cruce | Parte propia | — |
| OEM `confirmado*` / `pendiente` o sin dato | `parte_numero` con `confianza` 1,0 / 0,5 | 🔒 OEM exige `marca_pieza_id` |
| OEM `inconcluso` (`-`, `11061-`) o `descartado_manual` | No se publica (queda en `datos_crudos`) | — |
| `375×728×16/26` | 267/269 = 375 y 728 (el orden no importa); 268 = **16**; texto en `valor_original` | 🔒 Medidas con `uom_code` `MM` |
| Medidas del diagrama y de JJ difieren > 2 mm | Las guardas las dos, cada una con su registro | Conflicto `ATRIBUTO_DISCREPA`; Nexo ve la del diagrama |
| Vehículo inequívoco (`NISSAN VERSA 2007-2012`) | `parte_aplicacion` por año con su `base_vehicle_id` (submodelo y motor si están claros) | 🔒 El vehículo debe existir en AutoCare y no estar obsoleto |
| Vehículo ambiguo, en chino, solo la marca o fuera de AutoCare | `aplicacion_sin_homologar` con el texto y su `motivo` | — (el proceso de IA de vehículos registra después los que faltan) |
| Imagen de JJ | Copia en MinIO `rlt-diagramas/jjradiator/<archivo>` + `url` original en `parte_imagen` | — |
| Artículo que JJ ya no publica | No viene en la corrida | Al cerrar: `vigente = false` (nunca se borra) |
| Vuelve a aparecer | El *upsert* pone `vigente = true` | — |
| Dos partes resultan ser la misma | Una pasa a `FUSIONADA` con `fusionada_en_id` | 🔒 Nunca `DELETE` |

## Lo que Nexo usa para emparejar (prioridad de calidad)
Nexo busca en `catalogo.v_parte_busqueda` por tipo de parte y calcula un puntaje con:
- **Medidas del panal en mm**: PAdb 267 (alto), 269 (largo), 268 (ancho). Alto y largo se comparan en cualquier orden, ±10 mm.
  Sin medidas numéricas, la parte casi no aparece como candidata: separa `core_size` en sus tres valores.
- **Números** (`parte_numero`): OEM, DPI, proveedor, intercambio, con su marca. Nexo los compara normalizados (`numero_norm`)
  con el número de proveedor y el código anterior del artículo de SAP. Incluye el **código de JJ** como `PROVEEDOR`.
- **Aplicaciones** (`parte_aplicacion`): `base_vehicle_id` de AutoCare (o de MercadoExterno). Lo que no se pueda homologar va a
  `aplicacion_sin_homologar`, nunca inventado.
- **Imágenes** (`parte_imagen`): bucket y objeto de MinIO; los operadores las ven al comparar.

Y una regla que Nexo necesita: **los `parte.id` son estables**. Nexo los guarda al emparejar. Nunca se borran; se fusionan
(`FUSIONADA` + `fusionada_en_id`) o se descartan. Nexo revisa a diario las partes emparejadas que cambian de estado.

## Reglas que no se negocian
- **Sin DDL.** Las tablas, vistas y funciones vienen de `db/consolidacion/migraciones/` (las de Nexo). Si hace falta un cambio,
  se pide al equipo de Nexo.
- **Nunca `DELETE`** (lo impide la base). Lo que desaparece queda `vigente = false`.
- **Siempre foto completa** por fuente y cierre con `carga.fn_cerrar_corrida`. Una corrida parcial marcada como completa dejaría
  piezas no vigentes por error (o sería rechazada).
- **Solo lo vigente de AutoCare** (ADR 0024): toma los valores de `ref` con `obsoleto_en is null`.
- **No se inventa:** lo que no se pueda estandarizar va a `aplicacion_sin_homologar`, `datos_crudos` o `conflicto`.
- **Fuentes de solo lectura:** `db_diagrams`, `db_scrapper`, AutoCare y los sitios de los proveedores no se modifican.
- **No registres vehículos en MercadoExterno:** lo hace el proceso de IA de vehículos a partir de `aplicacion_sin_homologar`.
- **Credenciales solo en `.env`** (no leas `.env`; usa los nombres de las variables). Nunca en código, documentos ni commits.
- **Las pruebas usan la base local**, nunca los servidores.

## Ambientes
| | Consolidación | Fuentes |
|---|---|---|
| Desarrollo | `articulos_consolidacion` en el contenedor `postgres` (PostgreSQL 18), `postgres` | Copias o muestras locales |
| Producción | `consolidacion_articulos` en `10.10.60.6` (PostgreSQL 18), usuario en `grp_consolidacion_carga` | `db_diagrams` y `db_scrapper` en `10.20.20.6`, solo lectura |

## Cómo probar
1. `bash base-local/levantar.sh`: crea Consolidación local con las migraciones reales, la referencia mínima de AutoCare (o la real si
   `AUTOCARE_*` está configurado) y carga el ejemplo.
2. `uv run db/pruebas/probar.py --host postgres`: las pruebas del contrato (lo que la base acepta y lo que rechaza).
3. Corre tu carga contra la base local y revisa `catalogo.v_parte_busqueda`: es exactamente lo que verá Nexo.

Tus pruebas automáticas cubren al menos, sin servidores:
- primera corrida → todo `insertados`; segunda igual → todo `sin_cambios` y `no_vigentes` = 0;
- un diagrama y su JJ cruzado quedan en **una** parte; un dudoso con OEM distinto deja el conflicto;
- un OEM `inconcluso` no llega a `parte_numero`;
- `16/26` → espesor 16;
- un artículo que deja de venir → `no_vigentes` = 1; una corrida casi vacía → `CORRIDA_INCOMPLETA`, alerta y sin reintento.

## Pendiente de acordar con el equipo de Nexo
- La regla de cruce para fuentes nuevas (NRF, CSF, TYC…).
- Frecuencia de las corridas (la orquesta Airflow): al terminar cada scraping de la fuente.

## Convenciones
- Documentación y nombres de dominio en español; código técnico en inglés cuando sea idiomático.
- El devcontainer trae Python 3.13 con `uv` y `psycopg`; el proceso puede usar el stack de tu proyecto: el contrato es el SQL.
