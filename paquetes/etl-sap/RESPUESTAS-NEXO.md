# Respuestas del equipo de Nexo al plan del ETL (2026-10-21)

Respuestas a `PREGUNTAS-NEXO.md` y observaciones a `PLAN.md`. Lo que cambió en el contrato ya está en `CLAUDE.md` y en
`contexto/arquitectura/` (`contratos.md`, `mapeo-fuentes.md`).

## Preguntas
1. **Qué lleva `datos_sap`.** Los **42 campos** de `OITM` del diccionario `MAPEO` de la referencia (no 34), con los **nombres de
   SAP** como llaves y los valores **tal como vienen** (`''` incluido; el cambio de `''` a `NULL` es solo para las columnas de
   `staging`). Sin `@IGT_CAT2.Name`, que ya va en `subcategoria_nombre`. **No entra en el `hash_control`**: se muestra en la ficha.
   Arma `datos_sap` desde **bronze**, no desde silver.
2. **`@IGT_LINEA.Code` = `@IGT_MARCAS.Code`.** Sí: `@IGT_LINEA` es la tabla hija de `@IGT_MARCAS` y su `Code` es el código de la
   marca padre. Verificado con SAP real: los 1 636 modelos tienen su marca. Documentado en `mapeo-fuentes.md`.
3. **Lote abierto que nunca se procesa.** Lo maneja Nexo (migración 0015): al procesar un lote, limpia todo lo anterior al más
   antiguo de los 7 lotes procesados que conserva, también los lotes sin procesar. Un fallo reciente se conserva para
   diagnosticarlo. El ETL no tiene que hacer nada.
4. **`LOTE_YA_PROCESADO`.** De acuerdo: es un error del ETL y no hace falta reportarlo. Con la publicación en una sola tarea (abajo)
   no puede ocurrir.
5. **Lenguaje y driver.** El contrato es el SQL y el comportamiento: Spark JDBC para HANA y `psycopg2` para Nexo sirven. Las columnas
   de `staging` tienen tipo y Nexo calcula la huella sobre los valores normalizados, así que el driver no la cambia. Una condición:
   si un valor no convierte, que lo rechace Postgres; no lo conviertas a `null` en silencio en Spark.
6. **Verificación de la primera carga.** Es independiente de cómo se generó el lote: compara lo que quedó en Nexo con una carga de
   referencia de la misma SAP. Solo avísanos **antes** de correrla, para leer SAP en el mismo momento.
7. **Frecuencia.** El proceso de salida a SAP aún no existe, así que hoy no hay reaperturas en falso: una corrida diaria está bien.
   Cuando exista, la solución va de su lado; les avisamos si cambia algo.

## Sobre el plan
- **§3.8 reintentos:** abrir lote, escribir y procesar en **una sola tarea**. Un reintento abre un lote nuevo y da el mismo
  resultado (`sin_cambios`), así que `retries: 1` por fallas de red no hace daño. Ante `LOTE_INCOMPLETO`, `AirflowFailException`
  (falla sin reintentar) y alerta.
- **§3.1 duplicados:** no hace falta deduplicar. La referencia pide a SAP solo los conocidos que **faltan** en la consulta de las 8
  categorías, así que no se solapan; además, la llave `(lote_id, item_code)` rechazaría un duplicado.
- **§3.5 transacciones:** correcto, como la referencia.
- **§7 esquema de SAP:** producción es **`SBO_LIVE_RLT`**. Si `rlt_sap_main` ya lee `OITM`, `@IGT_CAT2`, `@IGT_MARCAS` y
  `@IGT_LINEA`, no hace falta otro usuario.
- **§5 PostgreSQL 18 local:** no hace falta cambiar el devcontainer compartido. Basta un contenedor aparte:
  `docker run -d --name nexo-pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:18` y
  `NEXO_LOCAL_HOST=localhost bash base-local/levantar.sh`. Si dentro del devcontainer no hay Docker, se levanta en la máquina y se
  usa `NEXO_LOCAL_HOST=host.docker.internal`.
- Taxonomía y nombre del DAG: decisión de su equipo.
