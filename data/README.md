# data/ — Datos de trabajo

| Carpeta | Contenido | ¿Se versiona? |
|---|---|---|
| `referencias/` | Archivos pequeños y estables que definen el negocio: lista de categorías SAP, catálogos de estados, ejemplos de artículos ya validados a mano | Sí |
| `muestras/` | Extractos de cada fuente (CSV/Parquet) para explorar sin conexión: `muestras/sap/`, `muestras/autocare/`, `muestras/consolidacion/`, `muestras/diagrams/` | No (pueden tener datos sensibles o pesar mucho) |
| `perfiles/` | Salida de `connections/exploration/perfilar.py` | No (se regeneran) |

Convención de nombres para muestras: `<fuente>/<tabla>__AAAA-MM-DD.csv`.
