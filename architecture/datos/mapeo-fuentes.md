# Mapeo de campos por fuente

Nomenclatura canónica de Nexo: ver [ADR 0007](../adr/0007-nomenclatura-canonica.md). Los nombres de SAP **no** se
propagan a Nexo ni a la APP; solo aparecen en esta tabla de mapeo.

## SAP (OITM) → `staging.articulo_sap` / `app.articulo`
Columnas en el orden en que entran al `hash_control` (**Hash = Sí**). El ETL solo renombra; Nexo normaliza valores.

| Campo SAP | Campo Nexo | Tipo Nexo | Normalización (en Nexo) | Hash |
|---|---|---|---|---|
| `ItemCode` | `item_code` | `text` | trim, mayúsculas | No (es la llave) |
| `ItemName` | `descripcion` | `text` | trim, colapsar espacios | Sí |
| `U_Categoria` | `categoria_codigo` | `text` | `@IGT_CAT.Code` (2 dígitos) | Sí |
| `U_SubCat` | `subcategoria_codigo` | `text` | `@IGT_CAT2.Code` | Sí |
| `@IGT_CAT2.Name` | `linea` | enum `IMPORTADO`/`FABRICADO` | por nombre, en singular | (derivado) |
| `U_SubSubCat` | `material_codigo` | `text` | — | Sí |
| `U_SSCatName` | `material_descripcion` | `text` | trim | Sí |
| `SuppCatNum` | `numero_parte_proveedor` | `text` | trim, mayúsculas | Sí |
| `U_CodAnterior` | `codigo_anterior` | `text[]` | separar por coma | No (solo sugiere equivalencias) |
| `U_Marca` | `marca_vehiculo_codigo` | `text` | numérico → 5 dígitos con ceros. Cualquier valor que no exista en `@IGT_MARCAS` (texto libre, `#N/A`) **o** que esté en `meta.marca_sap_invalida` (códigos `00132` Varios, `00133` NO APLICA, `00136` RLT, `00137` UNIVERSAL, que sí existen en `@IGT_MARCAS`) → `null` + hallazgo de calidad `MARCA_INVALIDA`. Es **basura**: no se interpreta | Sí |
| `@IGT_MARCAS.Name` | `marca_vehiculo` | `text` | lookup | (derivado) |
| `U_Linea` | `modelo_vehiculo_codigo` | `integer` | `LineId` en `@IGT_LINEA` de esa marca | Sí |
| `U_LineName` | `modelo_vehiculo` | `text` | trim, mayúsculas | Sí |
| `U_anio1` / `U_anio2` | `anio_desde` / `anio_hasta` | `smallint` | 0 o vacío → `null` | Sí |
| `U_Motor` | `motor` | `text` | trim | Sí |
| `U_Cyl` | `cilindrada` | `text` | trim | Sí |
| `U_transmision` | `transmision` | enum `AUTOMATICA`/`MANUAL` | `AT`→AUTOMATICA, `MT`→MANUAL | Sí |
| `SHeight1` + `SHght1Unit` | `panal_alto_mm` | `numeric(10,2)` | × `OLGT.SizeInMM`; 0 → `null`. ⚠️ ~1/3 invertido con largo | Sí |
| `SLength1` + `SLen1Unit` | `panal_largo_mm` | `numeric(10,2)` | ídem. ⚠️ ~1/3 invertido con alto | Sí |
| `SWidth1` + `SWdth1Unit` | `panal_ancho_mm` | `numeric(10,2)` | ídem (100 % consistente) | Sí |
| `U_Tamanio` | `tamano_panal` | enum `PEQUENO`/`MEDIANO`/`GRANDE` | P/M/G (`@IGT_LINEA`) o `Pequeño`/`Mediano`/`Grande` (`OITM`, cualquier mayúscula). Otro valor (`Proyecto`…) → `null` + hallazgo | Sí |
| `U_Filas` | `filas_panal` | `smallint` | — | Sí |
| `U_TipoPanal` | `tipo_panal` | `text` | trim; `0` → `null` | Sí |
| `U_CoreMaterial` | `material_panal` | `text` | trim; `0` → `null` | Sí |
| `U_TankMaterial` | `material_tanque` | `text` | trim; `0` → `null` | Sí |
| `U_TankDimension` | `dimension_tanque` | `text` | trim; `0` → `null` | Sí |
| `U_FlowType` | `tipo_flujo` | enum `HORIZONTAL`/`VERTICAL` | Cross Flow→HORIZONTAL, Down Flow→VERTICAL | Sí |
| `U_InletDiameter` | `entrada_diametro` | `text` | trim; `0` → `null` | Sí |
| `U_InletLocation` | `entrada_ubicacion` | `text` | valor de lista en español (UFD1) | Sí |
| `U_OutletDiameter` | `salida_diametro` | `text` | trim; `0` → `null` | Sí |
| `U_OutletLocation` | `salida_ubicacion` | `text` | valor de lista en español (UFD1); corregir `Top Rigth` | Sí |
| `U_CapIncluded` | `incluye_tapon` | `boolean` | S/N | Sí |
| `U_ThermostatIncluded` | `incluye_termostato` | `boolean` | S/N | Sí |
| `U_TransmissionOilCoolerIncluded` | `incluye_enfriador_transmision` | `boolean` | S/N | Sí |
| `U_Material_PRI` | `material_principal` | `text` | trim | Sí |
| `U_Material_SEC` | `material_secundario` | `text` | trim | Sí |
| `U_Material_Other` | `material_otro` | `text` | trim | Sí |
| `U_Material_Comp` | `composicion_material` | `text` | trim | Sí |
| `U_ID_Aces` | `autocare_id_sap` | `text` | trim (hoy vacío) | No |
| `frozenFor`, `ItemName` | `activo`, `motivo_inactivo` | `boolean`, enum | ver ADR 0008 | No |

**Medidas (pregunta 21, verificado 2026-10-15):** en 74 radiadores importados con DPI en `db_diagrams`, las medidas de SAP
coinciden con las **del panal** (mediana de la razón = 1,0). `SWidth1` es siempre el ancho (espesor del core); `SHeight1` y `SLength1` están invertidos
en ~1/3 de los artículos. Por eso, al buscar y comparar, alto y largo se tratan como **par sin orden**, y el operador fija la orientación
correcta al validar.

**Fuera del hash:** precio, existencias, costo promedio, `frozenFor`, fechas de creación y modificación de SAP.

### Cálculo del `hash_control`
- Lo calcula **Nexo** en `app.fn_procesar_staging`, no el ETL.
- `sha256` sobre los valores **ya normalizados** de las columnas con Hash = Sí, en el orden de la tabla, separados por `\x1f`,
  con `null` → cadena vacía. Así, cambios cosméticos en SAP (espacios, cm↔mm) no reabren artículos.
- Agregar o quitar una columna del hash es una decisión (ADR), porque recalcularlo puede reabrir artículos en masa.

## AutoCare → `vehiculo`, `articulo_aplicacion`, `articulo_atributo`
| Tabla.campo AutoCare | Campo Nexo | Notas |
|---|---|---|
| `vcdb_base.base_vehicle.base_vehicle_id` | `vehiculo.base_vehicle_id` | Unidad mínima de aplicación ACES |
| `vcdb_base.year.year_id` | `vehiculo.anio` | El `year_id` es el año |
| `vcdb_base.make.make_name` | `vehiculo.marca` | Copia para mostrar; se homologa con `@IGT_MARCAS` |
| `vcdb_base.model.model_name` | `vehiculo.modelo` | Copia para mostrar; se homologa con `@IGT_LINEA` |
| `vcdb_base.sub_model.sub_model_id` / `sub_model_name` | `vehiculo.sub_model_id` / `submodelo` | Opcional |
| `vcdb_parts.region.region_id` | `articulo_aplicacion_region.region_id` | Detalle opcional, varias por aplicación (pregunta 20) |
| `vcdb_config.engine_config.engine_config_id` | `articulo_aplicacion.engine_config_id` | Calificador de motor (SAP `U_Motor`, `U_Cyl`) |
| `vcdb_config.transmission.transmission_id` | `articulo_aplicacion.transmission_id` | Calificador (SAP `U_transmision`) |
| `vcdb_parts.db_version.version` | `vehiculo.vcdb_version` | Para detectar cambios de versión |
| `pcdb_base.part.part_terminology_id` | `articulo.part_terminology_id` | Defecto por categoría (`categorias.md`) |
| `padb_base.part_attribute.paid` | `articulo_atributo.paid` | Valor validado contra `valid_value_assignment` y `meta_uom_code_assignment` |

### Atributos SAP ↔ PAdb (Radiator, 2172)
| Nexo (desde SAP) | PAdb `paid` · nombre |
|---|---|
| `panal_alto_mm` / `panal_largo_mm` / `panal_ancho_mm` | 267 Core Height · 269 Core Width · 268 Core Thickness (las medidas de SAP son **del panal**; pregunta 21). Ojo: el **largo** del negocio es *Core Width* y el **ancho** es *Core Thickness* |
| `material_panal` / `material_tanque` | 302 Core Material · 305 Tank Material (lista: `meta.valor_sap_pies`, p. ej. `LATON` → Brass) |
| `tipo_flujo` | 7448 Down Flow Or Cross Flow Type (`HORIZONTAL` → Cross Flow, `VERTICAL` → Down Flow) |
| `entrada_diametro` | 570 Inlet Diameter (`35mm` → 35 MM; si trae varios diámetros no se precarga) |
| `tipo_panal` | 3664 Core Type (texto libre: el código de la empresa tal cual, `C`, `Z`, `V`, `EA`…) |
| `dimension_tanque` | 270 Inlet Header Length × 316 Inlet Header Width (`545*54.5` → 545 MM y 54.5 MM; con dos anchos, `756*33/48`, no se precarga) |

Los datos propios de la empresa se guardan en el atributo PIES donde encajan. El tamaño (`P`/`M`/`G`) no tiene atributo ni es obligatorio.
| `filas_panal` | 5061 Core Row Quantity |
| `material_panal` | 302 Core Material |
| `material_tanque` | 305 Tank Material |
| `tipo_flujo` | 7448 Down Flow Or Cross Flow Type |
| `entrada_diametro` / `salida_diametro` | 570 Inlet Diameter · 638 Outlet Diameter |
| `entrada_ubicacion` / `salida_ubicacion` | 619 Inlet Location · 304 Outlet Location |
| `incluye_tapon` | 3683 Radiator Cap Included |
| `incluye_termostato` | 9482 Thermostat Included |
| `incluye_enfriador_transmision` | 315 Transmission Oil Cooler Included |

## Consolidación → `articulo_parte` (emparejamiento en la APP)
| Campo Consolidación | Campo Nexo | Notas |
|---|---|---|
| `catalogo.parte.id` | `articulo_parte.parte_id` | Estable; si la parte se fusiona, se sigue `fusionada_en_id` |
| `catalogo.parte_aplicacion` | `articulo_aplicacion` (al confirmar) | El operador elige cuáles aplicaciones adopta |
| `catalogo.parte_atributo` | `articulo_atributo` (al confirmar) | Se copia con `origen = CONSOLIDACION` |
| `catalogo.parte_imagen` | `articulo_imagen` (al confirmar) | Solo la URL |

## Diagrams
No se lee directamente: `db_diagrams` es fuente del catálogo maestro (ADR 0011).
