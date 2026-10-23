# Contratos con procesos externos

Cada proceso de otro proyecto que lee o escribe Nexo tiene aquí su contrato. Mientras no esté acordado, es un borrador.

## ETL de entrada (SAP → Nexo)
> Acordado (2026-10-15): **Nexo define el contrato** y el ETL se adapta. Ver ADR 0006.

> Implementado en `apps/api/alembic/sql/0001_nucleo.sql`, 0010 y 0012; pruebas en `test_nucleo.py`, `test_etl_permisos.py` y
> `test_etl_foto_completa.py` (`apps/api/tests/integration/`).

- **Escribe en:** solo `staging`, **agregando filas**: una por artículo y lote, sin *upsert* (migración 0013; encaja con el modo
  append de Spark/JDBC). No toca nada del esquema `app`.
- **Usuario:** `etl_entrada` (`deploy/sql/usuario-etl.sql`): `SELECT/INSERT` en `staging` y `EXECUTE` de
  `app.fn_procesar_staging` y `app.fn_articulos_conocidos`, que corre con los permisos de su dueño (migración 0010). No puede leer ni escribir `app`.
  1. `staging.lote`: abre un lote como **foto completa** (`insert into staging.lote (completo) values (true) returning lote_id`).
  2. `staging.sap_marca` (`@IGT_MARCAS`: código, nombre) y `staging.sap_modelo` (`@IGT_LINEA`: marca, `LineId`, nombre, tamaño), **completos**
     en cada lote (Nexo valida cada artículo con las marcas y modelos **de su mismo lote**): Nexo los usa para decidir si `U_Marca` es válida (si no, es basura → `null` + hallazgo de calidad).
  3. `staging.articulo_sap`: una fila por `item_code` en el lote (solo `INSERT`).
- **Columnas:** las de la columna *Campo Nexo* de `mapeo-fuentes.md`, con nombres canónicos (ADR 0007). El ETL **solo renombra** y escribe valores crudos; las medidas van con su unidad original (`panal_alto` + `panal_alto_unidad` = `OLGT.UnitCode`, etc.); `subcategoria_nombre` = `@IGT_CAT2.Name`. Además lleva `congelado_sap` (`frozenFor`), `datos_sap` JSONB (fila cruda), `extraido_en` y `lote_id`.
- **Qué envía (foto completa, decisión 2026-10-20):** en cada corrida, **todos** los artículos de `OITM` de las 8 categorías de
  `context/categorias.md`, sin filtrar por subcategoría (Nexo decide qué está en alcance), **más** los `item_code` que Nexo ya conoce
  (`select * from app.fn_articulos_conocidos()`) aunque hoy estén en otra categoría: así Nexo sabe que salieron del alcance. Lo que
  ya no exista en SAP simplemente no se envía.
- **No calcula** `hash_control`: lo calcula Nexo sobre los valores normalizados (`mapeo-fuentes.md`).
- **Después de cargar:** llama a `app.fn_procesar_staging(lote_id)`, que:
  1. revalida el filtro (defensa en profundidad);
  2. normaliza los valores y calcula `hash_control`;
  3. crea los `app.articulo` nuevos en `PENDIENTE`;
  4. si el `hash_control` cambió y el artículo está `POR_VALIDAR`, `VALIDADO` o `SINCRONIZADO`, lo regresa a `PENDIENTE` con la función de transición (actor `PROCESO:ETL`, motivo `HASH_CAMBIO`), conservando lo ya confirmado;
  5. actualiza `activo` / `motivo_inactivo` (ADR 0008); nunca borra;
  6. en un lote completo, inactiva como `NO_EN_SAP` los activos que no vinieron (se reactivan si vuelven). **Defensa:** si faltan más
     del `etl.max_no_en_sap` (5 %) de los activos, y al menos 10, rechaza el lote entero con `LOTE_INCOMPLETO` y no aplica nada.
- **Devuelve** `{nuevos, actualizados, sin_cambios, reabiertos, inactivados, activados, descartados, no_en_sap}`: el ETL lo registra.
  Un lote no se procesa dos veces (`LOTE_YA_PROCESADO`). Nexo conserva en `staging` los últimos `etl.lotes_conservados` (7) lotes
  procesados y limpia todo lo anterior, también los lotes que nunca se procesaron (migración 0015); el historial completo de SAP lo
  guarda el ETL en su propio almacenamiento (capa *bronze*).
- **Implementación libre:** el contrato es el SQL y el comportamiento, no el lenguaje ni el driver (Spark JDBC, `psycopg2`… sirven).
  Abrir el lote, escribir y procesar van en **una sola tarea**: un reintento abre un lote nuevo y da el mismo resultado
  (idempotente). Ante `LOTE_INCOMPLETO`, fallar sin reintentar y alertar. Tipos: que Postgres rechace un valor que no convierte; no
  convertirlo a `null` en silencio.
  Ante `LOTE_INCOMPLETO` no se reintenta a ciegas: se revisa la lectura de SAP.
- **Cómo lo verifica Nexo** (primera carga en producción y cada vez que cambie el ETL): justo después de la corrida, se carga la misma
  SAP en una base local con `connections/exploration/lote_sap_local.py` (referencia) y se compara con
  `connections/exploration/verificar_etl_sap.py`. Deben coincidir los artículos, la huella (`hash_control`) de cada uno y los
  hallazgos de calidad; si no, la herramienta lista los campos que difieren con ejemplos.

## Carga del catálogo maestro (scraping → Consolidación)
> Nuestro esquema gobierna (ADR 0011). Decisiones de la carga: ADR 0026. Contrato completo: `db/consolidacion/README.md`.
- **Lee:** `db_diagrams` (diagramas y `jjradiator_cross_reference`) y `db_scrapper` (JJ Radiator), en 10.20.20.6, solo lectura.
- **Escribe en:** `consolidacion_articulos` (10.10.60.6; `catalogo.*`, `carga.*`). Nunca en Nexo.
- **Por corrida y fuente:** abre `carga.corrida` con `completa = true`, hace *upsert* de **todos** los registros de la fuente
  (siempre marca `corrida_id`), y cierra con `select carga.fn_cerrar_corrida(corrida_id)` → `{no_vigentes, conflictos}`.
  Ante `CORRIDA_INCOMPLETA` (faltaría > 5 %) marca la corrida `FALLIDA`, alerta y no reintenta a ciegas.
- **Reglas de la carga:** solo nuestros tipos de parte; diagrama y JJ cruzados en una misma parte (confianza 1,0 confirmados, 0,5
  dudosos); OEM confirmados (1,0) y pendientes (0,5); vehículos homologados solo si son inequívocos, el resto a
  `aplicacion_sin_homologar`; espesor = primer número; imágenes de JJ copiadas a MinIO; prioridad diagramas > JJ.
- **No** cambia estados de artículos: Consolidación no conoce SAP.
- **La APP** lee Consolidación para que el operador empareje; lo confirmado se guarda en Nexo (`app.articulo_parte`).
  Lee `catalogo.v_parte_busqueda` (candidatos por `part_terminology_id`, medidas del panal como par sin orden ± tolerancia,
  `parte_numero.numero_norm` y `parte_aplicacion.base_vehicle_id`) y el detalle de la parte (números, atributos, aplicaciones, imágenes
  y fuentes vigentes). Al vincular, puede copiar atributos y aplicaciones como sugerencias (`origen = CONSOLIDACION`, con `parte_id`).
  Las medidas de las vistas deben venir en mm (PAdb 267 alto, 269 largo, 268 ancho).

## Agente de revisión del catálogo (Consolidación → verificaciones de Nexo)
> Implementado en la migración 0011; pruebas en `apps/api/tests/integration/test_agente_revision.py`. ADR 0012.
Un agente de IA independiente compara lo que Nexo validó con lo que hoy dice el catálogo maestro y le informa a Nexo los cambios.
Nexo crea una verificación `CAMBIO_CATALOGO` por artículo afectado; un supervisor la resuelve y el ciclo vuelve a empezar.
- **Usuario:** `agente_revision_catalogo` (`deploy/sql/usuario-agente-revision-catalogo.sql`). Solo ejecuta tres funciones; no lee ni
  escribe tablas de Nexo. En Consolidación, un usuario de solo lectura (`grp_app_lectura`).
- **Por corrida:**
  1. `select parte_id, articulos from app.fn_partes_emparejadas()` → partes emparejadas con artículos validados.
  2. `select * from app.fn_datos_emparejamiento(array[…])` → por parte y artículo: lo validado (atributos y aplicaciones
     confirmados, número de proveedor, código anterior, fecha de validación).
  3. Comparar con Consolidación (`catalogo.parte`, `parte_numero`, `parte_atributo`, `parte_aplicacion`).
  4. `select app.fn_registrar_cambios_catalogo('<lista JSON>')` con los cambios:
     - `{"parte_id", "estado": "FUSIONADA", "fusionada_en_id"}`, `{"parte_id", "estado": "DESCARTADA"}`,
       `{"parte_id", "estado": "NO_EXISTE"}`: para todos los artículos validados de esa parte;
     - `{"parte_id", "estado": "DATOS_CAMBIARON", "item_code", "huella", "nota", "campos"}`: el agente explica en `nota` (10 a 2 000
       caracteres, la ve el supervisor) qué cambió; `huella` identifica los datos revisados; `item_code` y `campos` son opcionales.
     Devuelve `{recibidos, tareas, repetidos}`.
- **El ciclo cierra:** cada cambio tiene una clave (estado + `fusionada_en_id` o `huella`). El mismo cambio no vuelve a crear una
  verificación para el mismo artículo, aunque el supervisor ya la haya resuelto. Si los datos vuelven a cambiar, la `huella` es otra.
- **Error:** `CAMBIOS_INVALIDOS` si la lista no tiene esa forma.
- **Nexo no implementa la revisión:** solo expone estas funciones y muestra las verificaciones en la cola.

## Proceso de salida (Nexo → SAP)
- **Lee:** artículos `VALIDADO`.
- **Vehículo principal (ADR 0025):** `app.v_vehiculo_principal`, una fila por artículo con principal confirmado: `make_id`/`marca`,
  `model_id`/`modelo`, `sub_model_id`, `engine_config_id` o `equipment_base_id`, `anio_desde`, `anio_hasta`, y los códigos de SAP
  `marca_codigo_sap` (`U_Marca`) y `modelo_codigo_sap` (`U_Linea`) según las homologaciones confirmadas (`null` si falta). Con eso
  actualiza `U_Marca`, `U_Linea`, `U_anio1` y `U_anio2`; un código `null` no se escribe.
- **Transición:** `VALIDADO → SINCRONIZADO` = el artículo **ya se actualizó en SAP** (2026-10-19).
- **Otro proyecto (pregunta 25):** define qué campos escribe en SAP y debe evitar que el siguiente lote del ETL reabra el artículo por
  `HASH_CAMBIO`, por ejemplo registrando el hash esperado al marcar `SINCRONIZADO`.

## IA con búsqueda web → MercadoExterno (vehículos fuera de AutoCare)
> ADR 0014; modelo en `modelo-mercado-externo.md`.
- **Escribe en:** `mercado_externo`, solo mediante `fn_registrar_vehiculo(...)`, que verifica primero en AutoCare y en MercadoExterno.
- **Debe enviar:** marca, modelo, años, submodelo, motor (litros, cilindros, combustible), región, `evidencia` (URLs) y `confianza`.
- **No requiere aprobación humana.** Nunca borra; la reconciliación con AutoCare la hace este proyecto.
