# SAP Business One (HANA)

## Qué es
Origen del catálogo. El ETL externo copia los artículos a Nexo. Aquí solo lo leemos para entender los datos.

## Quién la mantiene
_Por completar._

## Acceso
Acceso de red desde desarrollo confirmado (2026-10-15). Variables `SAP_HANA_*` en `.env`; esquema de la sociedad `SAP_HANA_SCHEMA`. **Solo lectura**: este proyecto nunca escribe en SAP.

## Tablas / entidades clave
| Tabla | Uso |
|---|---|
| `OITM` | Artículos. UDF relevantes: `U_Categoria`, `U_SubCat`, `U_SubSubCat`, `U_Marca`, `U_Linea`, `U_LineName`, `U_anio1`, `U_anio2`, `U_Motor`, `U_Cyl`, `U_transmision`, `U_ID_Aces`, `U_CodAnterior`, `U_Filas`, `U_TipoPanal`, `U_Tamanio`, atributos técnicos (`U_TankMaterial`, `U_CoreMaterial`, `U_Inlet*`, `U_Outlet*`, `U_FlowType`…), medidas `SWidth1`/`SHeight1`/`SLength1`, `SuppCatNum` |
| `@IGT_CAT` / `@IGT_CAT2` / `@IGT_CAT3` | Categoría / subcategoría (línea Importado/Fabricado) / material. Ver `context/categorias.md` |
| `@IGT_MARCAS` | Marca de vehículo (163) |
| `@IGT_LINEA` | Línea (modelo) de vehículo por marca, con tamaño P/M/G (1 636). `U_Linea` en `OITM` es el número de línea, **no** Importado/Fabricado |
| `ITT1` | Lista de materiales de Fabricados (no sirve para la equivalencia) |
| `@IGT_EQUIVALENCIAS`, `@IGT_ITEM_OEM(S)`, `OALI` | Existen pero están **vacías** |

## Llaves para cruzar con SAP
`ItemCode`

## Volumen
`OITM`: 24 043 artículos (2026-10-15). En alcance confirmado (5 categorías × IMP/FAB): ≈ 4 100.

## Calidad observada
- `U_Marca` mezcla códigos de `@IGT_MARCAS` (`00117`) con texto libre (`RLT` ×9 936, `CHEVROLET`, `VARIAS`, `136` sin ceros). Los valores que no son marcas (`RLT`, `UNIVERSAL`, `Varios`, `NO APLICA`) son **basura**: no se interpretan y deben corregirse en SAP (reporte `hallazgo_calidad_sap`).
- `U_Origen_Item` (FB/MD/RT) y `U_Sector` vacíos en el 100 %. `PrcrmntMtd` = `B` en todos.
- `U_ID_Aces` vacío en las categorías en alcance.
- `U_CodAnterior` apunta a otro `ItemCode` solo en ~30 Fabricados y no siempre es su equivalente.
- Hay artículos `INACTIVO` en el nombre con subcategoría inconsistente.

## Cómo la usa la APP
_Lectura en vivo, copia en Nexo, o solo referencia._
