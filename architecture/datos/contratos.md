# Contratos con procesos externos

Cada proceso de otro proyecto que lee o escribe Nexo tiene aquí su contrato. Mientras no esté acordado, es un borrador.

## ETL de entrada (SAP → Nexo)
> Acordado (2026-10-15): **Nexo define el contrato** y el ETL se adapta. Ver ADR 0006.

> Implementado en `apps/api/alembic/sql/0001_nucleo.sql`; pruebas en `apps/api/tests/integration/test_nucleo.py`.

- **Escribe en:** solo `staging`, con *upsert*. No toca nada del esquema `app`.
  1. `staging.lote`: abre un lote (`insert … default values returning lote_id`).
  2. `staging.sap_marca` (`@IGT_MARCAS`: código, nombre) y `staging.sap_modelo` (`@IGT_LINEA`: marca, `LineId`, nombre, tamaño), **completos**
     en cada lote: Nexo los usa para decidir si `U_Marca` es válida (si no, es basura → `null` + hallazgo de calidad).
  3. `staging.articulo_sap`: *upsert* por `item_code`.
- **Columnas:** las de la columna *Campo Nexo* de `mapeo-fuentes.md`, con nombres canónicos (ADR 0007). El ETL **solo renombra** y escribe valores crudos; las medidas van con su unidad original (`panal_alto` + `panal_alto_unidad` = `OLGT.UnitCode`, etc.); `subcategoria_nombre` = `@IGT_CAT2.Name`. Además lleva `congelado_sap` (`frozenFor`), `datos_sap` JSONB (fila cruda), `extraido_en` y `lote_id`.
- **Filtro:** categorías y subcategorías de `context/categorias.md` (solo IMPORTADOS/FABRICADOS).
- **No calcula** `hash_control`: lo calcula Nexo sobre los valores normalizados (`mapeo-fuentes.md`).
- **Después de cargar:** llama a `app.fn_procesar_staging(lote_id)`, que:
  1. revalida el filtro (defensa en profundidad);
  2. normaliza los valores y calcula `hash_control`;
  3. crea los `app.articulo` nuevos en `PENDIENTE`;
  4. si el `hash_control` cambió y el artículo está `VALIDADO`/`SINCRONIZADO`, lo regresa a `PENDIENTE` con la función de transición (actor `PROCESO:ETL`, motivo `HASH_CAMBIO`), conservando lo ya confirmado;
  5. actualiza `activo` / `motivo_inactivo` (ADR 0008); nunca borra.

## Carga del catálogo maestro (scraping → Consolidación)
> Nuestro esquema gobierna (ADR 0011): `modelo-consolidacion.md`, sección *Reglas del contrato para el proceso de carga*.
- **Escribe en:** `articulos_consolidacion` (`catalogo.*`, `carga.*`). Nunca en Nexo.
- **No** cambia estados de artículos: Consolidación no conoce SAP.
- **La APP** lee Consolidación para que el operador empareje; lo confirmado se guarda en Nexo (`app.articulo_parte`).
  Lee `catalogo.v_parte_busqueda` (candidatos por `part_terminology_id`, medidas del panal como par sin orden ± tolerancia,
  `parte_numero.numero_norm` y `parte_aplicacion.base_vehicle_id`) y el detalle de la parte (números, atributos, aplicaciones, imágenes
  y fuentes vigentes). Al vincular, puede copiar atributos y aplicaciones como sugerencias (`origen = CONSOLIDACION`, con `parte_id`).
  Las medidas de las vistas deben venir en mm (PAdb 267 alto, 269 largo, 268 ancho).

## Proceso de salida (Nexo → SAP)
- **Lee:** artículos `VALIDADO`.
- **Transición:** `VALIDADO → SINCRONIZADO` = el artículo **ya se actualizó en SAP** (2026-10-19).
- **Otro proyecto (pregunta 25):** define qué campos escribe en SAP y debe evitar que el siguiente lote del ETL reabra el artículo por
  `HASH_CAMBIO`, por ejemplo registrando el hash esperado al marcar `SINCRONIZADO`.

## IA con búsqueda web → MercadoExterno (vehículos fuera de AutoCare)
> ADR 0014; modelo en `modelo-mercado-externo.md`.
- **Escribe en:** `mercado_externo`, solo mediante `fn_registrar_vehiculo(...)`, que verifica primero en AutoCare y en MercadoExterno.
- **Debe enviar:** marca, modelo, años, submodelo, motor (litros, cilindros, combustible), región, `evidencia` (URLs) y `confianza`.
- **No requiere aprobación humana.** Nunca borra; la reconciliación con AutoCare la hace este proyecto.
