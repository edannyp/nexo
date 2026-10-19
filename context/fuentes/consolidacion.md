# Consolidación (`articulos_consolidacion`)

## Qué es
Catálogo maestro: la unión estandarizada de `db_diagrams` y los proveedores scrapeados. **El esquema lo define este proyecto**
(ADR 0009, 0011) y lo llena el proceso de otro desarrollador. No conoce SAP.

## Quién la mantiene
Esquema: este proyecto. Datos: proyecto de IA / scraping.

## Acceso
Postgres, variables `CONSOLIDACION_*`, base `articulos_consolidacion` (vacía al 2026-10-15).
⚠️ Hoy se usa el usuario `postgres` (superusuario): pedir un usuario de solo lectura para la APP y otro de escritura para la IA.

## Tablas / entidades clave
Ver `architecture/datos/modelo-consolidacion.md` (borrador).

## Llaves para cruzar con SAP
`item_code` (obligatorio en cada candidato ligado a un artículo).

## Cómo la usa la APP
La APP la **lee** para mostrar sugerencias en la consola Master Merge. Al aprobar, lo confirmado se copia a Nexo
(`articulo_aplicacion`, `articulo_diagrama`, `articulo_imagen`, `articulo_equivalencia`).
