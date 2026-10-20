# 0022. Indicadores de venta relativos y análisis con permiso

- **Estado:** Aceptada. Implementada en la migración 0006, `modules/{panorama,ventas}.py` y la tarea `actualizar-ventas` (2026-10-19).
- **Fecha:** 2026-10-19

## Contexto
En ClickHouse vive el volumen de venta por artículo (pregunta 8: datos de apoyo). Ayuda a priorizar qué revisar, pero el detalle
de ventas es información sensible que no todos los usuarios deben ver.

## Decisión
- **Indicadores relativos**, visibles para todos los usuarios de Nexo, calculados por tipo de artículo (categoría + línea) y periodo
  configurable:
  - clase ABC (A = artículos que suman el 80 % de la venta del tipo, B = siguiente 15 %, C = resto);
  - percentil dentro del tipo y participación porcentual;
  - tendencia porcentual frente al periodo anterior.
  Nunca muestran montos ni precios. Se usan en el encabezado del artículo, Explorar, Panorama y el orden de "Siguiente".
- **Análisis de ventas** (series, comparaciones, estacionalidad) en una pantalla aparte, **fuera del espacio de trabajo**, solo para
  usuarios con el permiso `VER_ANALISIS_VENTAS`.
- Los permisos especiales se asignan **por usuario**, además del rol (ADR 0015): un usuario de cualquier rol puede tener o no este permiso.
- ClickHouse se lee solo mediante un adaptador de solo lectura. Si no responde, los indicadores se ocultan y la APP sigue funcionando.

## Consecuencias
- Nexo necesita una tabla de permisos por usuario (por ejemplo, `app.usuario_permiso`) y la API valida el permiso en `/ventas/*`.
- **Implementación (2026-10-19):** copia de apoyo en Nexo (`app.venta_mensual`, unidades por artículo y mes) refrescada con
  `python -m nexo_api.cli actualizar-ventas`, y una vista (`app.v_indicador_venta`) que calcula los indicadores dentro de cada tipo.
  Así se pueden ordenar bandejas y filtrar por clase sin consultar ClickHouse en cada petición. Periodo y umbrales en `meta.parametro`.
  La clasificación ABC-XYZ global de la empresa se muestra solo como referencia.
