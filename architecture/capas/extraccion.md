# Capa de Extracción (externa)

Sistemas: SAP HANA, AutoCare (Postgres), MercadoExterno (Postgres) y el proceso ELT.

**Responsabilidad de este proyecto:** ninguna sobre el ELT. Necesitamos:
- Conocer el esquema de SAP (OITM y relacionadas) para diseñar el staging de Nexo.
- Acceso de lectura a AutoCare para que la APP busque aplicaciones vehiculares.
- Diseñar MercadoExterno: catálogo de vehículos fuera de AutoCare con estándar ACES (ADR 0014). La APP y la IA con búsqueda web escriben ahí.
