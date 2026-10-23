# Ejemplo de carga: de `db_diagrams` a Consolidación

Tres diagramas reales de `db_diagrams` (valores del 2026-10-15), cada uno con un problema típico. El SQL ejecutable está en
[ejemplo_carga.sql](ejemplo_carga.sql); las pruebas (`db/pruebas/probar.py`) lo corren y verifican el resultado.

## Caso A — 905096: números abreviados, medidas ambiguas, vehículo incompleto

| En `db_diagrams` | En Consolidación | Por qué |
|---|---|---|
| fila completa | `registro_fuente.datos_crudos` (JSON) | Nada se pierde |
| `dpi = '1816'` | `parte_numero` tipo `DPI` | |
| `oem = '2531022050/22070'` | **dos** filas `OEM` de Hyundai: `25310-22050` (0.8) y `25310-22070` (0.6) | El segundo abrevia el sufijo; al expandirlo baja la confianza |
| `alto_panal = 335`, `largo_panal = 608`, `ancho_panal = 16` | `parte_atributo` 267 = 335 MM, 269 = 608 MM, 268 = 16 MM | Nombres PAdb; `ancho_panal` es en realidad el espesor |
| `core_size = '335x608x16/22/26'` | 267 = 335, 269 = 608, 268 = **16** y `valor_original` en cada medida | Espesor doble o triple: el espesor es el primer número; no se adivina qué son los demás (ADR 0026) |
| `marca = 'HYUNDAI'`, sin modelo ni años | `aplicacion_sin_homologar` (`MODELO_DESCONOCIDO`) | No hay base vehicle posible con solo la marca |

## Caso B — 918255: medidas solo en texto

| En `db_diagrams` | En Consolidación |
|---|---|
| `oem = '568.770.38'` | `parte_numero` OEM Ford; la base calcula `numero_norm = '56877038'` |
| `core_size = '770x588x36'`, columnas numéricas vacías | 267 = 770, 269 = 588, 268 = 36 (MM). El formato es **alto × largo × espesor**, verificado con el caso A |

## Caso C — 915015: vehículo homologado a ACES

| En `db_diagrams.compatibilidades` | En Consolidación |
|---|---|
| `SUZUKI`, `Grand Vitara II`, 2005–2015, `JB420`, `2.0` | 11 filas `parte_aplicacion`, una por `base_vehicle_id` (Suzuki + **Grand Vitara** + año) |
| `Grand Vitara II` | Es una generación, no un modelo VCdb: se homologa al modelo `Grand Vitara` |
| `motor = 'JB420'`, `cilindrada = '2.0'` | Sin `engine_config_id` resuelto: va en `notas` (mejorable después) |

Si AutoCare no tuviera el vehículo, el bloque lo deja en `aplicacion_sin_homologar` en lugar de inventar IDs. Si se confirma
que el vehículo existe en el mercado, se registra en MercadoExterno y se usa el ID que devuelve `fn_registrar_vehiculo`.

## Lo que el ejemplo **no** cubre todavía
- **Deduplicación entre fuentes:** si NRF o CSF traen una pieza con OEM `25310-22050` de Hyundai, su `registro_fuente` debería
  apuntar a la **misma** `parte` del caso A (`vinculo_metodo = 'NUMERO'`). Las reglas exactas están pendientes de acordar.
- Imágenes (`parte_imagen`) y regiones (`parte_aplicacion_region`).

La corrida se abre con `completa = true` (foto completa de la fuente) y se cierra con `select carga.fn_cerrar_corrida(id)`:
marca no vigente lo que no vino, abre conflictos si las medidas de una parte difieren > 2 mm entre fuentes y la deja `COMPLETA`.
