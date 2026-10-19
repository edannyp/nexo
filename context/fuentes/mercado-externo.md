# MercadoExterno (`mercado_externo`)

## Qué es
Catálogo de **vehículos, marcas y equipos del mercado que no están en AutoCare**, con la misma estructura y estándar ACES (ADR 0014).
Ejemplo: modelos de Changan vendidos en Guatemala que VCdb no tiene, o equipos como plantas Perkins.
**Lo diseña y construye este proyecto.** Vacía al 2026-10-15.

## Quién la mantiene
Esquema: este proyecto. Datos: la IA con búsqueda web (otro proyecto) y la APP.

## Acceso
Postgres, variables `MERCADO_EXTERNO_*`, base `mercado_externo` (mismo servidor que AutoCare).

## Tablas / entidades clave
Ver `architecture/datos/modelo-mercado-externo.md`.

## Llaves para cruzar
Mismos IDs que VCdb (los propios ≥ 1 000 000 000). Se cruza con SAP vía la homologación de `@IGT_MARCAS` / `@IGT_LINEA`.

## Cómo la usa la APP
Lee para los buscadores de vehículos (junto con AutoCare) y escribe cuando el operador agrega un vehículo que no existe.
