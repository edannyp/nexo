# AutoCare (`autocare_global`, PostgreSQL)

## Qué es
Estándar de AutoCare cargado en Postgres, edición **Global** (multi-región), explorado el 2026-10-15:

| Base | Versión | Publicación | Esquemas |
|---|---|---|---|
| VCdb (vehículos, ACES) | 2.0 | 2026-07-30 | `vcdb_base`, `vcdb_config`, `vcdb_parts` |
| PCdb (tipos de parte) | 2.0 | 2026-07-30 | `pcdb_base`, `pcdb_config`, `pcdb_parts` |
| PAdb (atributos PIES) | 5.0 | 2026-07-30 | `padb_base`, `padb_config`, `padb_meta` |
| Qdb (calificadores) | 2.0 | 2026-07-30 | `qdb_base`, `qdb_config` |

Además hay un esquema **`rlt`** propio (no es AutoCare): búsqueda de compatibilidades de radiadores. **Es otro proyecto y no entra aquí.**

## Quién la mantiene
Carga de AutoCare: _por completar_. Esquema `rlt`: _por confirmar_ (pregunta 19).

## Acceso
Variables `AUTOCARE_*`, base `autocare_global` (mismo servidor que Consolidación y MercadoExterno). Solo lectura.
Todo está en inglés (`culture_id = en-US`): no hay traducciones al español.

## Tablas / entidades clave
**Vehículo (ACES)**
- `vcdb_base.base_vehicle` (115 616) = año + `make` (649) + `model` (23 278). Es la unidad mínima de una aplicación ACES.
- `vcdb_base.vehicle` (345 069) = `base_vehicle` + `sub_model` + **`region`**. Un mismo base vehicle tiene un `vehicle_id` por región.
- Configuraciones: `vcdb_config.vehicle_to_engine_config` → `engine_config` (`engine_base`: litros, cc, cilindros), `vehicle_to_transmission`, `vehicle_to_body_style_config`, `vehicle_to_drive_type`, etc.
- Regiones con más vehículos: USA 143 984, CAN 80 131, MEX 33 965 … **GTM 6 672**, CRI 2 710, PAN 1 090, HND 220, NIC 182, SLV 165.

**Parte (PCdb)**
- `pcdb_base.part` (40 646 *PartTerminology*), categorizados en `pcdb_config.part_category` → `category` / `sub_category`.
- Tipos de parte de nuestras categorías: ver `context/categorias.md`.

**Atributos (PAdb / PIES)**
- `padb_config.part_attribute_assignment` relaciona tipo de parte → atributo (`paid`); `valid_value_assignment` define los valores permitidos; `meta_uom_code_assignment` define las unidades.
- *Radiator* (2172) tiene 72 atributos: `Core Height/Width/Thickness`, `Core Row Quantity`, `Core Material`, `Tank Material`,
  `Down Flow Or Cross Flow Type`, `Inlet/Outlet Diameter`, `Inlet/Outlet Location`, `Radiator Cap Included`, `Thermostat Included`,
  `Transmission Oil Cooler Included`, `Overall Height/Length/Width`… Cubren casi todos los `U_*` técnicos de SAP.

**Esquema `rlt` (consolidación propia, en curso)**
| Tabla | Filas | Contenido |
|---|---|---|
| `parte` | 1 266 | Pieza de referencia (sin `item_code` ni `part_terminology_id`) |
| `parte_numero` | 2 616 | Números OEM (2 003), PROVEEDOR (Spectra 490, NRF 39), DPI, INTERCAMBIO, con `numero_norm`, `fuente_id` y `confianza` |
| `parte_atributo` | 8 743 | Atributos PAdb (`paid`, `valor_num`, `uom_code`, `valid_value_id`); todos de *Radiator* |
| `aplicacion` | ~200 000 y creciendo | `parte_id` → **`vehicle_id`** + `engine_config_id` + `transmission_id`, `vcdb_version`, `confianza`, `preliminar` |
| `fuente`, `fuente_fiabilidad`, `evidencia`, `conflicto`, `verificacion_web`, `lote`, `generacion` | | Trazabilidad, pesos por fuente, conflictos y avance por lote (make/model/años) |

Enums: `confianza` (recolectado → confirmado → verificado / en_conflicto), `tipo_numero` (OEM, DPI, INTERCAMBIO, PROVEEDOR),
`tipo_conflicto` (numero_duplicado, marca_cruzada, prefijo_ajeno, atributo_discrepa…).

### Cobertura frente a SAP (2026-10-15)
- 35 de 131 marcas SAP en alcance (456 artículos) sin equivalente exacto en `make`. Son sobre todo **equipos** (Perkins, Cummins, Generac,
  Yale, JCB, Komatsu): existen como fabricantes en `vcdb_parts.mfr` y se modelan con `equipment_base` / `equipment_model`.
- Marcas presentes pero con poca cobertura local: Changan, 68 base vehicles, solo BRA/CHL/COL/MEX.
- Lo que falte se agrega en **MercadoExterno** (ADR 0014).

## Llaves para cruzar con SAP
- No hay llave directa: `rlt` no tiene `ItemCode` (0 coincidencias).
- El cruce posible es por número de parte: `SuppCatNum` / DPI / OEM de SAP ↔ `rlt.parte_numero.numero_norm`.
- Vehículo: `U_Marca` + `U_LineName` + `U_anio1..2` de SAP ↔ `make` + `model` + `year` (requiere homologar nombres).

## Volumen
VCdb ~4 GB en relaciones `vehicle_to_*`. `rlt.aplicacion`: 49 916 vehículos y 1 091 partes cubiertos; 78 % `preliminar`; 0 verificadas.
`rlt.lote`: 7 789 pendientes, 2 en proceso, 53 recolectados.

## Calidad observada
- Muchas tablas de catálogo de VCdb están vacías (`drive_type`, `fuel_type`, `aspiration`, `class`, `brake_*`…) aunque existen
  sus relaciones `vehicle_to_*`. Las estadísticas de Postgres dicen 0 filas, pero el conteo real muestra datos (p. ej. `fuel_type` = 26):
  usar siempre `count(*)`.
- `engine_config` y `engine_config2` duplicados (la 2 agrega `engine_block` y `bore_stroke`).
- `rlt.aplicacion` sin `transmission_id` en ninguna fila; `engine_config_id` solo en el 9 %.
- Perfiles en `data/perfiles/autocare__*.md`.

## Cómo la usa la APP
- **Lectura en vivo** de VCdb/PCdb/PAdb para buscadores (año → marca → modelo → submodelo → motor) y para validar atributos.
- Nexo guarda solo los **IDs** de AutoCare más una copia desnormalizada mínima para mostrar (marca, modelo, año), con `vcdb_version`.
- `rlt` no se usa (otro proyecto).
