# 0023. La clase de venta viene de la clasificación de ClickHouse

- **Estado:** Aceptada. Implementada en la migración 0011 (2026-10-20).
- **Fecha:** 2026-10-20

## Contexto
El ADR 0022 hacía que Nexo calculara la clase A/B/C de cada artículo con sus unidades vendidas, dentro de su tipo. Pero ClickHouse
ya calcula y mantiene la clasificación ABC-XYZ de la empresa (`rlt_ml.latest_clasificacion_abcxyz`, una fila por artículo,
actualizada en cada corrida del modelo), y tener dos clasificaciones distintas para el mismo artículo confunde. Se evaluó también un
ETL externo para llevar las ventas a Nexo y se descartó: no aporta valor, porque el dato ya está calculado.

## Decisión
- La **clase de venta** que usa Nexo (orden de "Siguiente", filtros de Explorar, Panorama) es la **letra ABC de
  `rlt_ml.latest_clasificacion_abcxyz`** (`categoria_abc`; se guarda completa, p. ej. `AX`, en `app.venta_referencia.abcxyz_empresa`).
  Un artículo sin clasificación cuenta como "sin venta".
- **Participación, top % y tendencia** siguen calculándose en Nexo con las unidades, dentro de cada tipo (lo que ClickHouse no da).
- **Sin ETL externo:** Nexo mismo copia a diario las unidades y la clasificación (`python -m nexo_api.cli actualizar-ventas`), porque
  necesita la clase dentro de PostgreSQL para ordenar y filtrar. ClickHouse sigue siendo solo lectura.
- Reemplaza la parte de la clase del ADR 0022; lo demás de ese ADR (indicadores relativos, análisis con permiso) sigue vigente.

## Consecuencias
- Los umbrales 80 % / 95 % de Nexo (`meta.parametro`) desaparecen: los aplica ClickHouse.
- La clase es global de la empresa, no por tipo. `rlt_ml.latest_clasificacion_abcxyz_seg` la calcula por ámbito (hoy solo
  `radiadores_importados`); si ClickHouse agrega los demás ámbitos, se puede pasar a esa tabla con una migración.
- La copia diaria se programa en el servidor de Nexo (no es un proceso de otro equipo).
