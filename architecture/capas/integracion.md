# Capa de Integración (este proyecto)

## Componentes
| Componente | Responsabilidad |
|---|---|
| **Nexo** | Staging de artículos SAP, estados y bitácora, catálogo híbrido de aplicaciones (AutoCare + custom), emparejamientos con el catálogo maestro de Consolidación, usuarios, sesiones y auditoría. |
| **API** | Sesiones y roles, máquina de estados, bandejas, Master Merge, asociación de aplicaciones y diagramas, auditoría. |
| **Frontend** | Consola del operador y del administrador. |

## Integraciones de la APP
| Sistema | Dirección | Modo |
|---|---|---|
| Nexo | Lectura/escritura | Directo (SQLAlchemy) |
| AutoCare | Lectura | Directo, solo lectura |
| Consolidación | Lectura | Directo, Postgres (ADR 0011) |
| Diagrams (`db_diagrams`) | Ninguna | Es fuente de Consolidación |
| MercadoExterno | Lectura/escritura | Directo; vehículos fuera de AutoCare (ADR 0014) |
| MinIO | Lectura/escritura | S3; fotos propias (ADR 0013) |
| SAP HANA | Ninguna en producción | Solo exploración en desarrollo |

## Principios
- Los sistemas externos se acceden solo a través de **adaptadores** (`apps/api/.../adapters/`), con versiones falsas para pruebas.
- La **máquina de estados** es una sola pieza; los procesos externos que cambian estados deben hacerlo con las mismas reglas (función SQL o tabla de transiciones permitidas en Nexo).
- **Auditoría**: nada se borra físicamente; cada cambio de un operador queda registrado con antes/después.
