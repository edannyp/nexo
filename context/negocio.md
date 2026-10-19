# Negocio

## Objetivo
Centralizar, limpiar, enriquecer y validar el catálogo de artículos automotrices
(radiadores, intercoolers, condensadores, etc.) que viven en **SAP Business One (HANA)**,
combinándolos con:

- **AutoCare**: estándar de la industria para aplicaciones vehiculares (año / marca / modelo / motor).
- **Catálogos de scraping enriquecidos**: JJRadiators y otras fuentes (`n_fuentes`).
- **Diagrams**: diagramas técnicos de las piezas.
- **Consolidación**: base unificada que generan los procesos de IA cruzando imágenes y descripciones.

El resultado es un catálogo validado por personas que regresa limpio a SAP. Los vehículos que AutoCare no cubre se
registran en **MercadoExterno** con el mismo estándar ACES (esto último lo hace otro proyecto, ver [alcance.md](alcance.md)).

## Qué artículos se trabajan
Solo los de las categorías listadas en [categorias.md](categorias.md).

## Importados vs Fabricados
Cada artículo en alcance pertenece a una de dos líneas:

- **Importado**: se compra a un proveedor.
- **Fabricado**: se produce internamente cuando no hay importado disponible. Debe ser
  **equivalente funcional** del importado (mismas aplicaciones vehiculares, mismas medidas),
  pero de otro material, por lo que suele ser más caro.

**En SAP** la línea es la subcategoría: `OITM.U_SubCat` → `@IGT_CAT2.Name` = `IMPORTADOS` o `FABRICADOS`
(código `<categoría>01` / `<categoría>02`, p. ej. `2501` / `2502`). SAP también tiene `MODIFICADOS`,
`REPARADOS` y `USADOS`, pero **quedan fuera de alcance**. Se normaliza por **nombre**, no por código.

**Equivalencia Fabricado ↔ Importado**: SAP no la registra de forma confiable, así que se gestiona en
**Nexo** desde la APP, siguiendo la estandarización de AutoCare (mismas aplicaciones ACES y atributos PIES).
SAP es **solo lectura** para este proyecto. Ver [ADR 0005](../architecture/adr/0005-equivalencias-en-nexo.md).

## Actores
| Actor | Qué hace en la APP |
|---|---|
| **Operador** | Trabaja la bandeja `PENDIENTE` / `RECHAZADO`: empareja el artículo con el catálogo maestro, confirma aplicaciones vehiculares, tipo de parte, atributos, equivalencias e imágenes, y lo envía a `POR_VALIDAR`. |
| **Supervisor** | Revisa la bandeja `POR_VALIDAR`: valida o rechaza con motivo (nunca su propio envío). Atiende la cola de verificación y puede reabrir. |
| **Administrador** | Gestiona usuarios y roles, reasigna trabajo, revisa la bitácora, reabre artículos y configura catálogos. |
| **Encargado de fotos** | Sube las fotos propias **desde la APP** (ADR 0013); la APP las guarda en MinIO con la convención correcta y cada foto genera una tarea de verificación. |
| **Procesos externos** | ETL (entrada desde SAP y salida), IA / Consolidación. No son usuarios de la APP; escriben o leen Nexo. |

## Equipo y volumen (2026-10-15)
| Rol | Personas |
|---|---|
| Operador | 5 |
| Supervisor | 3 |
| Encargado de fotos | 1 |

4 278 artículos en alcance; ~1 100 en la bandeja por defecto (Radiadores Importados). Con este tamaño basta la reserva con
"Siguiente" (30 minutos renovables); no hace falta reparto automático.

## Filtro global de tipo de artículo
Toda la APP trabaja sobre un **tipo de artículo** = categoría + línea, elegido en un filtro global (encabezado de la APP).
Por defecto: **Radiadores Importados**. Cada categoría tiene un tipo de parte AutoCare (PartTerminology) que define qué atributos
PIES pide la consola. Ver `context/categorias.md`.

## Pantallas principales (a detallar en la planificación)
1. **Bandejas**: operador (`PENDIENTE` / `RECHAZADO`), supervisor (`POR_VALIDAR`) y verificación (tareas abiertas). Todas respetan el filtro global (ADR 0010).
2. **Consola Master Merge**: vista lado a lado del artículo SAP vs las sugerencias de Consolidación / AutoCare / Diagrams, con nivel de confianza de la IA; el operador acepta, corrige o rechaza cada atributo.
3. **Asociación de aplicaciones vehiculares**: buscar y asignar vehículos (catálogo AutoCare + vehículos custom).
4. **Asociación de diagramas**: elegir el diagrama correcto entre los candidatos.
5. **Bitácora / auditoría** por artículo.
