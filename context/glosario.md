# Glosario

| Término | Definición |
|---|---|
| **Artículo** | Producto del catálogo SAP (un `ItemCode`). Unidad de trabajo del workflow. |
| **Categoría** | Agrupación de artículos en SAP (radiador, intercooler, condensador…). Define qué entra al proyecto. |
| **Importado / Fabricado** | Línea del artículo: comprado a proveedor o producido internamente como equivalente. |
| **Aplicación vehicular** | Vehículo en el que se usa la pieza (año, marca, modelo, submodelo, motor). Base AutoCare (ACES). |
| **Vehículo custom** | Vehículo que no existe en AutoCare; se da de alta en **MercadoExterno** con IDs ≥ 1 000 000 000 (ADR 0014). |
| **AutoCare** | Estándar de la industria (ACES para aplicaciones, PIES para atributos de producto). |
| **Panal (core)** | Núcleo del radiador por donde pasa el refrigerante. Las medidas de SAP son del core y se nombran como en SAP y en el negocio: **alto** (`SHeight1`), **largo** (`SLength1`) y **ancho** (`SWidth1`, el grueso del core). En Nexo: `panal_alto_mm`, `panal_largo_mm`, `panal_ancho_mm`. En PIES: *Core Height*, *Core Width* y *Core Thickness*, respectivamente. |
| **Diagrama** | Dibujo técnico de la pieza con medidas, obtenido de la fuente Diagrams. |
| **Consolidación** | Catálogo maestro (`db_diagrams` + proveedores scrapeados) con esquema definido por este proyecto; lo llena otro desarrollador y el operador lo usa para emparejar (ADR 0011). |
| **Emparejamiento** | El operador liga un artículo SAP con una o más partes del catálogo maestro (`app.articulo_parte`). Ya no hay pre-match automático (ADR 0011). |
| **Ficha** | Atributos PIES habilitados para el tipo de parte, con etiqueta del negocio; algunos obligatorios (ADR 0019). |
| **hash_control** | Huella de los campos relevantes del artículo en SAP; si cambia, el artículo se revalida. |
| **Nexo** | Este sistema: el puente de gobernanza del artículo entre SAP, AutoCare y el catálogo maestro. Su base PostgreSQL es `nexo` y "la APP" es su API + consola web (ADR 0020). Antes se llamaba BD_APP. |
| **MercadoExterno** | Base PostgreSQL con los vehículos, marcas y equipos del mercado que **no** están en AutoCare, con el mismo estándar ACES (ADR 0014). |
| **Service Layer** | API REST de SAP Business One para escribir de vuelta (la usa otro proyecto). |
| **Bitácora** | Registro de transiciones de estado y motivos. |
