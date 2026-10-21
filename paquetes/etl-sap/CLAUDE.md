# Guía para agentes — ETL de entrada SAP → Nexo

## Qué es este repositorio
El **ETL de entrada** de Nexo: lee los artículos de SAP Business One (HANA, solo lectura) y los deja en el esquema `staging` de la
base `nexo`. Nexo (otro repositorio, otro equipo) es el "puente de gobernanza del artículo": normaliza, valida y entrega los artículos
a los operadores. **Este ETL no interpreta los datos ni detecta cambios: copia una foto de SAP con los nombres que pide el contrato, y
Nexo decide qué es nuevo, qué cambió, qué se inactiva y qué hay que corregir en SAP.** Es un proceso mecánico: no usa IA.

Lee antes de proponer o escribir código:
1. `contexto/arquitectura/contratos.md`, sección *ETL de entrada*: lo que este proceso debe hacer y lo que no.
2. `contexto/arquitectura/mapeo-fuentes.md`: cada campo de SAP y su columna en `staging.articulo_sap`.
3. `contexto/categorias.md`: las 8 categorías que se leen.
4. `referencia/lote_sap_local.py`: cómo se leyó SAP para verificar Nexo. **No es el ETL** (sin manejo de errores, escribe en una base
   local), pero muestra la consulta y el orden de escritura correctos.

## El contrato, en corto
Por cada corrida, conectado a `nexo` con el usuario `etl_entrada`:
1. `insert into staging.lote (completo) values (true) returning lote_id` → abre un lote de **foto completa**.
2. `staging.sap_marca` (`@IGT_MARCAS`: código, nombre) y `staging.sap_modelo` (`@IGT_LINEA`: marca, LineId, nombre, tamaño):
   **completos en cada lote**, con *upsert*. Nexo los usa para decidir si `U_Marca` es una marca válida.
3. `staging.articulo_sap`, con *upsert* por `item_code`, `datos_sap` (la fila cruda de SAP en JSON), `extraido_en` y `lote_id`, de:
   - **todos** los artículos de `OITM` de las 8 categorías, **sin filtrar por subcategoría** (Nexo decide qué está en alcance);
   - **más** los `item_code` que ya enviaste antes (`select item_code from staging.articulo_sap`) aunque hoy estén en otra
     categoría. Así Nexo sabe que salieron del alcance. Lo que ya no exista en SAP simplemente no se envía.
4. `select app.fn_procesar_staging(lote_id)` → devuelve `{nuevos, actualizados, sin_cambios, reabiertos, inactivados, activados,
   descartados, no_en_sap}`. **Regístralo** en el log de la corrida.

## Lo que puede pasar en SAP y lo que hace Nexo (no lo programes tú)
| En SAP pasa… | Nexo hace |
|---|---|
| Artículo nuevo en alcance | Lo crea en Pendiente |
| Artículo nuevo de otra subcategoría | Lo descarta (`descartados`) |
| Cambia un dato que importa (descripción, medidas, marca, años…) | Lo actualiza y guarda qué cambió. Si estaba Por validar, Validado o Sincronizado, **vuelve a Pendiente** (motivo `HASH_CAMBIO`) conservando el trabajo hecho |
| Cambia un dato menor (código anterior) | Lo actualiza sin reabrir |
| Se congela (`frozenFor = Y`) o se le pone «INACTIVO» en el nombre | Lo inactiva y libera su reserva; se reactiva si se revierte |
| Cambia a una categoría o subcategoría fuera de alcance | Lo inactiva (`FUERA_DE_ALCANCE`); **solo si lo sigues enviando** (regla 3) |
| Ya no está en SAP (no vino en la foto) | Lo inactiva (`NO_EN_SAP`); se reactiva si vuelve |
| Datos sucios: marca «RLT» o texto libre, años invertidos, valores no reconocidos | Hallazgo de calidad para corregir en SAP; se cierra solo cuando SAP lo corrige |

**Defensa de Nexo:** si en un lote completo faltan más del 5 % de los artículos activos (y al menos 10), Nexo **rechaza el lote
entero** con `LOTE_INCOMPLETO` y no aplica nada. Casi siempre es un error de lectura (consulta vacía, filtro equivocado, conexión
cortada). **No reintentes a ciegas:** alerta y revisa.

## Reglas que no se negocian
- **Solo `staging`.** El usuario `etl_entrada` no puede leer ni escribir `app`; si algo lo necesita, se está saliendo del contrato.
- **Valores crudos, nombres canónicos.** Se renombra (`SHeight1` → `panal_alto`) pero no se convierte ni se limpia: las medidas van con
  su unidad (`panal_alto_unidad` = `OLGT.UnitCode`), los ceros y vacíos como vienen. `''` de SAP → `NULL`.
- **No calcula `hash_control`** ni decide estados, inactivos o hallazgos: eso es de Nexo.
- **Siempre foto completa.** Un lote parcial marcado como completo inactivaría artículos por error (o sería rechazado).
- **SAP es solo lectura.** Nunca un `INSERT/UPDATE` en HANA.
- **Sin DDL.** El esquema de `nexo` lo gobiernan las migraciones de Nexo. Si hace falta una columna o un cambio, se pide al equipo
  de Nexo; no se crea aquí.
- **Idempotente.** Correr dos veces seguidas no cambia nada la segunda vez (`sin_cambios` = todo).
- **Credenciales solo en `.env`**: nunca en código, documentos ni commits. No leas `.env` (está denegado); usa los nombres de las
  variables.

## Ambientes
| | Base | Usuario | Dónde |
|---|---|---|---|
| Desarrollo | `nexo` en el contenedor `postgres` (PostgreSQL 18) | `etl_entrada` / `etl` | `base-local/levantar.sh` |
| Producción | `nexo` en `10.10.60.6` (PostgreSQL 18) | `etl_entrada` | credenciales del equipo de Nexo |

## Cómo probar
1. `bash base-local/levantar.sh` crea (o recrea) la base local con **las mismas migraciones que producción** y el usuario
   `etl_entrada` con los mismos permisos.
2. Corre el ETL contra la base local (`NEXO_*` del `.env` apuntan a `postgres` por defecto).
3. `psql "$NEXO_LOCAL_ADMIN" -f base-local/verificar.sql` muestra artículos por categoría y línea, hallazgos de calidad y el resultado
   de cada lote.

Las pruebas automáticas (`pytest`) usan solo la base local: **nunca dependen de SAP ni de servidores**. Arma filas de ejemplo con la
forma de `OITM` y cubre al menos:
- primera carga → todo `nuevos`; segunda carga igual → todo `sin_cambios`;
- un artículo que cambia de categoría sigue enviándose (y Nexo lo inactiva como fuera de alcance);
- un artículo que deja de existir en la fuente → `no_en_sap` = 1;
- una lectura que falla a medias → `LOTE_INCOMPLETO`, el ETL alerta y no reintenta.

## Pendiente de decidir con el equipo de Nexo / negocio
- Frecuencia de la corrida (la orquesta el Airflow de la empresa).
- El proceso de salida (Nexo → SAP) es otro proyecto: cuando escriba en SAP, no debe provocar que este ETL reabra los artículos
  que acaba de publicar (pregunta 25 de Nexo).

## Convenciones
- Documentación y nombres de dominio en español; código técnico en inglés cuando sea idiomático.
- Python 3.13 con `uv`. Conexiones con `psycopg` (Nexo) y `hdbcli` (SAP).
