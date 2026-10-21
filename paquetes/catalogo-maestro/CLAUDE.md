# Guía para agentes — Carga del catálogo maestro (Consolidación)

## Qué es este repositorio
El proceso que llena **Consolidación** (`articulos_consolidacion`), el catálogo maestro de piezas del mercado: une el catálogo de
diagramas (`db_diagrams`) y los proveedores scrapeados (JJ Radiator, NRF, CSF, TYC…), estandarizado con AutoCare (PCdb, PAdb, VCdb).
**El esquema lo gobierna Nexo** (otro repositorio): este proceso se adapta a él, no al revés.

Nexo lee Consolidación para que los operadores **emparejen** cada artículo de SAP con una parte del catálogo. Lo que cargues aquí
es lo que verán como candidatos, con un puntaje. Por eso importa tanto la calidad de las medidas, los números y las aplicaciones.

Lee antes de proponer o escribir código:
1. `db/consolidacion/README.md`: **el contrato** (11 reglas; las marcadas 🔒 las hace cumplir la base y fallan con `CONTRATO: …`).
2. `db/consolidacion/ejemplos/ejemplo_carga.md` y `.sql`: tres diagramas reales cargados según el contrato, paso a paso.
3. `contexto/arquitectura/modelo-consolidacion.md` y `contexto/fuentes/diagrams.md` (qué trae la fuente y sus problemas de calidad).

## Lo que Nexo usa para emparejar (prioridad de calidad)
Nexo busca en `catalogo.v_parte_busqueda` por tipo de parte y calcula un puntaje con:
- **Medidas del panal en mm**: PAdb 267 (alto), 269 (largo), 268 (ancho). Alto y largo se comparan en cualquier orden, ±10 mm.
  Sin medidas numéricas, la parte casi no aparece como candidata: separa `core_size` (`538X388X68`) en sus tres valores.
- **Números** (`parte_numero`): OEM, DPI, proveedor, intercambio, con su marca. Nexo los compara normalizados (`numero_norm`)
  con el número de proveedor y el código anterior del artículo de SAP.
- **Aplicaciones** (`parte_aplicacion`): `base_vehicle_id` de AutoCare (o de MercadoExterno). Lo que no se pueda homologar va a
  `aplicacion_sin_homologar`, nunca inventado.
- **Imágenes** (`parte_imagen`): URL o bucket y objeto de MinIO (`rlt-diagramas`); los operadores las ven al comparar.

Y una regla que Nexo necesita: **los `parte.id` son estables**. Nexo los guarda al emparejar. Nunca se borran; se fusionan
(`FUSIONADA` + `fusionada_en_id`) o se descartan. Nexo revisa a diario las partes emparejadas que cambian de estado.

## Reglas que no se negocian
- **Sin DDL.** Las tablas, vistas y funciones vienen de `db/consolidacion/migraciones/` (las de Nexo). Si hace falta un cambio,
  se pide al equipo de Nexo.
- **Nunca `DELETE`** (lo impide la base).
- **Solo lo vigente de AutoCare** (ADR 0024): lo que AutoCare quitó queda en `ref` con `obsoleto_en`; la base rechaza asignarlo
  en filas nuevas (tipo de parte, atributo, valor, vehículo). Toma los valores de `ref` con `obsoleto_en is null`.
- **Fuentes de solo lectura:** `db_diagrams`, AutoCare y los sitios de los proveedores no se modifican.
- **Credenciales solo en `.env`** (no leas `.env`; usa los nombres de las variables). Nunca en código, documentos ni commits.
- **Las pruebas usan la base local**, nunca los servidores.

## Ambientes
| | Base | Usuario |
|---|---|---|
| Desarrollo | `articulos_consolidacion` en el contenedor `postgres` (PostgreSQL 18) | `postgres` |
| Producción | `consolidacion_articulos` en `10.10.60.6` (PostgreSQL 18) | uno en `grp_consolidacion_carga` (lo crea el administrador) |

## Cómo probar
1. `bash base-local/levantar.sh`: crea Consolidación local con las migraciones reales, la referencia mínima de AutoCare (o la real si
   `AUTOCARE_*` está configurado) y carga el ejemplo.
2. `uv run db/pruebas/probar.py --host postgres`: las pruebas del contrato (lo que la base acepta y lo que rechaza).
3. Corre tu carga contra la base local y revisa `catalogo.v_parte_busqueda`: es exactamente lo que verá Nexo.

## Pendiente de acordar con el equipo de Nexo
- Reglas de deduplicación: cuándo dos `registro_fuente` son la misma `parte` y con qué `vinculo_confianza`.
- Lista inicial de `fuente` y `marca_pieza`.
- Frecuencia de las corridas (lo orquesta Airflow).

## Convenciones
- Documentación y nombres de dominio en español; código técnico en inglés cuando sea idiomático.
- Python 3.13 con `uv`; `psycopg` para PostgreSQL.
