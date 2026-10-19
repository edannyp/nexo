# Categorías en alcance

Solo los artículos de estas categorías **y** de subcategoría `IMPORTADOS` o `FABRICADOS` entran a Nexo.

## Dónde está en SAP
- Categoría: `OITM.U_Categoria` → `@IGT_CAT` (`Code`, `Name`, `U_Prefijo`).
- Subcategoría / línea: `OITM.U_SubCat` → `@IGT_CAT2` (`Code` = categoría + sufijo, `U_Categoria`).
- Sub-subcategoría (material): `OITM.U_SubSubCat` / `U_SSCatName` → `@IGT_CAT3`.
- `OITB` (grupo de artículos) **no** sirve: el 95 % está en `102 Repuestos`.

## En alcance (confirmadas 2026-10-15)
Conteos de `OITM` al 2026-10-15.

| `U_Categoria` | Nombre | IMPORTADOS (`xx01`) | FABRICADOS (`xx02`) |
|---|---|---|---|
| 25 | RADIADORES | 1 113 | 2 024 |
| 07 | CONDENSADORES | 289 | 2 |
| 18 | INTERCOOLER | 88 | 38 |
| 11 | ENFRIADORES DE ACEITE | 20 | 115 |
| 29 | TANQUES | 124 | 318 |
| 09 | DEPOSITOS AUXILIARES | 15 | 125 |
| 46 | INTERCAMBIADOR | 0 | 1 |
| 44 | TOLVA RADIADOR | 0 | 6 |
| | **Total** | **1 649** | **2 629** |

## Tipo de parte AutoCare (PCdb) por categoría
Cada artículo debe tener su `part_terminology_id` (qué parte es según AutoCare): define qué atributos PIES aplican y cómo se publica.
La categoría da el **valor por defecto**; el operador puede cambiarlo por artículo.

| `U_Categoria` | Categoría | PartTerminology por defecto | Alternativas (el operador elige) | Atributos PAdb |
|---|---|---|---|---|
| 25 | RADIADORES | 2172 Radiator | — | 72 |
| 07 | CONDENSADORES | 6708 A/C Condenser | — | 25 |
| 18 | INTERCOOLER | 12616 Intercooler | — | 31 |
| 11 | ENFRIADORES DE ACEITE | 2084 Engine Oil Cooler | 2088 Automatic Transmission Oil Cooler, 17668 Engine Oil and ATF Cooler, 20531 Manual Transmission Oil Cooler | 36 |
| 29 | TANQUES | 48305 Radiator Tank Set | 17700 Radiator Inlet Tank, 17701 Radiator Outlet Tank | 10 |
| 09 | DEPOSITOS AUXILIARES | 10457 Engine Coolant Reservoir | 63482 Radiator Surge Tank | 24 |
| 44 | TOLVA RADIADOR | 10707 Engine Cooling Fan Shroud | — | 9 |
| 46 | INTERCAMBIADOR | _por definir_ (1 artículo) | 64918 Intercooler Heat Exchanger, 2084 | — |

## Filtro global de la APP
La APP tiene un **filtro global de tipo de artículo** = categoría + línea, que define sobre qué se trabaja en todas las pantallas
(bandejas, Master Merge, búsquedas, equivalencias). **Por defecto: 25 RADIADORES + IMPORTADO.** Se guarda por usuario. Ver ADR 0010.

## Fuera de alcance
| `U_Categoria` | Nombre | Motivo |
|---|---|---|
| 23 | PANALES | Componente de fabricación (14 146 artículos); no es pieza de vehículo |
| 28 | SOPORTES | **En duda**: fuera por ahora; revisar si son soportes de radiador |
| 32 / 40 / 06 | TUBO / PLATINA / CINTA | Materia prima |
| 36, 30, 16, 21, 13 | VENTILADOR, TAPONES, GRIFOS Y TAPONES, MANGUERAS, EVAPORADORES | No tienen subcategoría IMPORTADOS/FABRICADOS |
| Resto | Insumos, herramientas, servicios, etc. | No son piezas de vehículo |

## Filtro (para el contrato del ETL)
```sql
U_Categoria IN ('25','07','18','11','29','09','46','44')
AND U_SubCat IN (SELECT "Code" FROM "@IGT_CAT2" WHERE "Name" IN ('IMPORTADOS','FABRICADOS'))
```
