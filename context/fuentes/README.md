# Fichas de fuentes

Una ficha por sistema. Completa cada sección al explorar la fuente con los scripts de `connections/`.

| Fuente | Tipo | Rol en este proyecto | Ficha |
|---|---|---|---|
| SAP Business One (HANA) | HANA | Origen de artículos (vía ETL externo); lectura directa solo para exploración | [sap-hana.md](sap-hana.md) |
| AutoCare | PostgreSQL | Catálogo de aplicaciones vehiculares que lee la APP | [autocare.md](autocare.md) |
| Consolidación | Por confirmar | Pre-match de la IA que lee la APP | [consolidacion.md](consolidacion.md) |
| Diagrams | Por confirmar | Diagramas candidatos que lee la APP | [diagrams.md](diagrams.md) |
| JJRadiators / n_fuentes | Scraping | Indirecto: llega vía Consolidación y Diagrams | [scraping.md](scraping.md) |
| MercadoExterno | PostgreSQL | Vehículos y marcas fuera de AutoCare (estándar ACES) | [mercado-externo.md](mercado-externo.md) |
| MinIO | Object storage (S3) | Fotos propias de artículos (parcial) | [minio.md](minio.md) |
| ClickHouse | ClickHouse | Volumen de venta y parque vehicular (uso por definir) | _pendiente_ |

Plantilla de cada ficha: **Qué es · Quién la mantiene · Acceso · Tablas/entidades clave · Llaves para cruzar con SAP · Volumen · Calidad observada · Cómo la usa la APP**.
