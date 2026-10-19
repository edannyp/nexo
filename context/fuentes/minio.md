# MinIO (fotos de artículos)

## Qué es
Servidor de objetos compatible con S3 donde ya viven fotos propias de **algunos** artículos.
Explorado el 2026-10-15.

## Quién la mantiene
_Por completar._

## Acceso
- API S3 en la red interna, por **HTTP** (no HTTPS). `MINIO_ENDPOINT=10.10.10.3:9000` y `MINIO_SECURE=false`.
  `minio.gruporealcaruz.com` es la **consola web** y no responde a peticiones S3.
- Bucket: **`rlt-dru`** (con guion; los nombres S3 no admiten `_`).
- Variables `MINIO_*` en `.env`. La APP **lee y sube** fotos propias (ADR 0013); necesita una llave con escritura limitada a `imagenes_inventario/`.
- Otros buckets que pueden interesar: `rlt-diagramas` (¿fuente Diagrams? ver pregunta 3), `rlt-dru-develop`, `rlt-dru-release`.

## Tablas / entidades clave
`rlt-dru` tiene en la raíz `CRM/`, `MIR/`, `configuraciones/`, `imagenes_inventario/`, `mcs/`, `mfc/`, `mov/`, `mtm/` y `usuarios/`.
Este proyecto solo usa `imagenes_inventario/`:

```
imagenes_inventario/{U_Categoria}_{NOMBRE_CATEGORIA}/{ItemCode}/{ItemCode}_{n}.webp
p. ej. imagenes_inventario/25_RADIADORES/RAD00140/RAD00140_1.webp
```
- `{U_Categoria}_{NOMBRE}` = `@IGT_CAT.Code` + `Name` con espacios → `_` (`11_ENFRIADORES_DE_ACEITE`). Hay 42 carpetas.
- `n` = 1..6 (lo normal son 3 fotos por artículo). Formato `webp`.
- Cada carpeta de categoría tiene además un `TEST.svg` de prueba, que se ignora.

## Llaves para cruzar con SAP
El nombre de la carpeta es el `ItemCode`. La categoría de la carpeta coincide con `U_Categoria` en el 100 % de los casos.

## Volumen
1 713 objetos, ~191 MB, 551 carpetas de artículo (todas las categorías).
Cobertura en alcance: **485 de 4 278 artículos (11 %)**.

| Categoría | IMPORTADOS con foto | FABRICADOS con foto |
|---|---|---|
| 25 Radiadores | 404 / 1 113 | 10 / 2 024 |
| 18 Intercooler | 41 / 88 | 0 / 38 |
| 07 Condensadores | 30 / 289 | 0 / 2 |
| 09, 11, 29, 44, 46 | 0 | 0 |

## Calidad observada
- 5 carpetas no son un `ItemCode` limpio: `RAD00617_revisión`, `RAD00734_revisión`, `INT00033_2`, `INT00040_2` (contiene fotos de `INT00032`) y `RAD001007` (no existe en SAP; ¿`RAD01007`?).
- 21 archivos fuera del patrón (`RAD00046_.webp`, `RAD000098_1.webp`, `INT00033_1_2.webp`…).
- Casi no hay fotos de Fabricados: la equivalencia con su Importado (ADR 0005) permite mostrar la foto del Importado como referencia.

## Cómo la usa la APP
Es la única que escribe en `imagenes_inventario/` (ADR 0013): el encargado de fotos sube desde la APP y cada foto genera una tarea de verificación.
Muestra las fotos propias en la consola Master Merge junto a la imagen o URL de proveedor. Se referencian por clave de objeto (no se copian) y se sirven con URL prefirmada o con un proxy del backend.

## Cobertura de fotos (verificado 2026-10-19)
- En las carpetas de las 8 categorías en alcance hay 1 513 objetos: 1 507 `.webp`, 5 `TEST.svg` y un `.ini`. Hasta 6 fotos por artículo.
- Tienen foto **475 de 1 622 importados** activos (29 %) y **10 de 2 629 fabricados**.
- Todavía no existen las carpetas `44_TOLVA_RADIADOR` ni `46_INTERCAMBIADOR`; las creará la APP al subir.
- Hay 5 carpetas que no son un `ItemCode` válido (`INT00033_2`, `RAD00617_REVISIÓN`, `RAD001007`…). La importación inicial (ADR 0013) debe reportarlas y no asociarlas.
