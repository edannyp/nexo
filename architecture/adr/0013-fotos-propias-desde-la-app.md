# 0013. Las fotos propias se suben desde la APP

- **Estado:** Aceptada. Importación inicial implementada: `python -m nexo_api.cli importar-fotos` (2026-10-19; 1 490 fotos de 485 artículos).
  Subida desde la APP implementada (2026-10-19): pantalla Fotos y pestaña Fotos; llave de escritura `MINIO_FOTOS_*`.
- **Fecha:** 2026-10-15

## Contexto
- Hay fotos propias de 485 de 4 278 artículos en alcance, en MinIO (`rlt-dru/imagenes_inventario/…`); una persona irá subiendo más.
- Subidas a mano, la estructura acumula errores: `RAD00617_revisión`, `INT00040_2` (con fotos de `INT00032`), `RAD001007` (no existe en SAP), nombres fuera de patrón.
- Cada foto nueva debe generar una tarea de verificación `NUEVA_FOTO` (ADR 0012).

## Decisión
- El **encargado de fotos** las sube **desde la APP** (pantalla "Fotos del artículo", respetando el filtro global). La APP:
  - valida que el artículo exista y esté activo;
  - convierte a `webp` y guarda con la convención exacta `imagenes_inventario/{cat}_{NOMBRE}/{ItemCode}/{ItemCode}_{n}.webp`;
  - registra en `articulo_imagen` quién subió y cuándo, y crea la tarea de verificación.
- Nadie fuera de la APP escribe en `imagenes_inventario/`. La APP usa una llave MinIO con escritura **limitada a ese prefijo**.
- Las imágenes de proveedores y de Consolidación **no se copian**: se referencian por URL (ADR 0009).
- **Importación inicial** única: la APP registra las fotos existentes en `articulo_imagen` y reporta las carpetas con errores para corregirlas a mano.

## Consecuencias
- El encargado de fotos necesita un usuario de la APP con rol `FOTOS`, no credenciales de MinIO.
- El backend necesita un adaptador de MinIO (S3) con subida, listado y URLs prefirmadas para mostrar.
- Hay que pedir una llave de MinIO de escritura acotada a `rlt-dru/imagenes_inventario/` (la actual se usa para lectura).
