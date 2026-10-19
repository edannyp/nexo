# 0010. Filtro global de tipo de artículo y tipo de parte AutoCare por artículo

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
Las categorías en alcance (`context/categorias.md`) son piezas distintas, con atributos PIES distintos: un radiador tiene
72 atributos en PAdb, un depósito auxiliar 24. Un operador trabaja un tipo a la vez, y la consola debe pedir los atributos
correctos.

## Decisión
- La APP tiene un **filtro global** = categoría + línea (IMPORTADO/FABRICADO), visible en el encabezado y guardado por usuario
  (`preferencia_usuario`). **Por defecto: 25 RADIADORES + IMPORTADO.**
- Todos los endpoints de listado y búsqueda (bandejas, búsqueda de artículos, candidatos de equivalencia) reciben el filtro y lo aplican.
  Los endpoints por id no lo aplican, pero respetan `activo` (ADR 0008).
- Cada artículo tiene `part_terminology_id` (PCdb). La categoría propone uno por defecto y el operador puede cambiarlo
  (p. ej. Enfriadores: aceite de motor vs. de transmisión). Ese ID decide qué atributos PAdb muestra y valida la consola.

## Consecuencias
- `architecture/api/convenciones.md` debe definir cómo viaja el filtro (parámetros `categoria` y `linea`, con valor por defecto de la preferencia).
- Las bandejas no mezclan tipos; para una vista de todo, el administrador cambia el filtro explícitamente.
- La búsqueda de equivalencias cruza líneas (un Fabricado busca Importados) pero no categorías.
