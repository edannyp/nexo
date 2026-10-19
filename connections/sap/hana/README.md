# SAP HANA (lectura)

Solo para explorar datos en desarrollo. En producción, la APP no lee SAP: los artículos llegan a Nexo por el ETL externo.

- Driver: `hdbcli` (oficial de SAP, se instala con pip, sin dependencias del sistema).
- Variables: `SAP_HANA_HOST`, `SAP_HANA_PORT` (30015 single-tenant, 3NN13/3NN41 multi-tenant), `SAP_HANA_USER`, `SAP_HANA_PASSWORD`, `SAP_HANA_SCHEMA`.
- Pedir un usuario **de solo lectura**.
- Si no hay red hacia HANA desde desarrollo, exportar `OITM`, `OITB`, `OMRC` a CSV y dejarlos en `data/muestras/sap/`.
