# Alcance

## Este proyecto construye
| Componente | Descripción |
|---|---|
| **Nexo** (PostgreSQL) | Staging de artículos, estados del workflow, catálogos híbridos (AutoCare + custom), tablas de cruce con fuentes externas, bitácora y auditoría. |
| **APP – Backend** | API con sesiones de usuario, roles, seguridad, control de concurrencia y la máquina de estados. |
| **APP – Frontend** | Consola Master Merge, bandejas de validación, asociación de aplicaciones vehiculares y diagramas. |
| **Lectura de fuentes** | La APP **lee** Consolidación, AutoCare y las fotos de MinIO para mostrarlas al operador. SAP HANA es **solo lectura** y solo se usa para explorar. |
| **Esquema de Consolidación** | Diseño del modelo de `articulos_consolidacion` (contrato que llena la IA). ADR 0009. |
| **MercadoExterno** | Diseño y construcción de `mercado_externo`: vehículos y marcas fuera de AutoCare con estándar ACES. La APP agrega los que falten (ADR 0014). |

## Fuera de alcance (otros proyectos)
| Componente | Dónde vive | Cómo nos afecta |
|---|---|---|
| **ETL SAP → Nexo** | Otro proyecto | Escribe solo en `staging.articulo_sap` según `contratos.md` (ADR 0006). |
| **ELT SAP ↔ AutoCare** | Otro proyecto (capa de Extracción) | — |
| **IA con búsqueda web de vehículos** | Otro proyecto | Agrega en MercadoExterno los vehículos que no están en AutoCare, según nuestro contrato (ADR 0014). |
| **Regreso a SAP (Service Layer / ETL)** | Otro proyecto | Lee artículos `VALIDADO` y los marca `SINCRONIZADO`. Contrato a acordar. |
| **Carga a `staging`** | Otro proyecto (ETL) | El ETL carga y llama a `app.fn_procesar_staging`; el `hash_control` y la vuelta a `PENDIENTE` los resuelve **Nexo** (ADR 0006, pregunta 6). |
| **Web scraping** (JJRadiators, n_fuentes) | Otro proyecto | Solo consumimos su resultado vía Consolidación / Diagrams. |
| **Scraping + catálogo maestro** | Otro proyecto (otro desarrollador) | Une `db_diagrams` y los proveedores scrapeados en Consolidación, adaptándose a nuestro esquema (ADR 0011). |
| **`rlt`** (búsqueda de compatibilidades) | Otro proyecto | No entra en este proyecto. |
| **`db_diagrams`** | Otro proyecto | Es **fuente** del catálogo maestro. La APP no lo lee ni lo escribe. |

## Regla práctica
Si una tarea implica **mover datos entre sistemas en lote**, no es de este proyecto: se documenta
aquí como contrato y se pasa al proyecto de ETL. Este proyecto define **el modelo de Nexo y las
reglas** que esos procesos deben respetar.
