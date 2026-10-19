# 0009. Este proyecto define los esquemas de Consolidación y MercadoExterno (estándar ACES/PIES)

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
- `articulos_consolidacion` (Consolidación) y `mercado_externo` existen en el servidor Postgres, pero están **vacías**.
- `db_diagrams` (7 405 diagramas) es el antecedente que hoy alimentan el scraping y la IA. Es útil, pero:
  - no se liga con SAP (`codsap` vacío en el 100 %);
  - guarda vehículos como texto libre (`marca = 'INTERCOOLER'`) sin IDs de AutoCare;
  - guarda medidas como texto (`335x608x16/22/26`) y solo 24 % numéricas;
  - tiene OEM con ruido (`$55215200`) y confianza como texto libre.

## Decisión
- **Consolidación**: este proyecto es dueño del **esquema** (es el contrato). Los procesos de IA y scraping (otro
  proyecto) lo llenan; la APP lo lee. Se diseña con lo aprendido en `db_diagrams`, pero sin heredar sus defectos.
- **MercadoExterno**: este proyecto diseña y construye su esquema. Es el catálogo de **vehículos y marcas fuera de AutoCare**, con estándar ACES (ADR 0014).
- **`db_diagrams`**: la APP no lo lee ni lo escribe. Es insumo histórico para la IA, que lo migra a Consolidación.
- Las tres bases (Nexo, Consolidación, MercadoExterno) siguen los mismos estándares:
  - **ACES** para aplicaciones vehiculares: referencias a `BaseVehicle`, `EngineConfig`, `Transmission` y otros IDs
    de AutoCare, nunca texto libre. Los vehículos que no existen en AutoCare se crean como custom con la misma forma.
  - **PIES** para el producto: atributos con nombre estándar, medidas numéricas con unidad e
    *interchange* (OEM / competidor) con marca y número de parte normalizados.
  - **Nomenclatura canónica** (ADR 0007) y diccionario de campos.
- Las imágenes se referencian por **URL** (proveedor o MinIO `rlt-diagramas` / `rlt-dru`); no se copian a la base.

## Consecuencias
- La exploración del esquema de AutoCare (pregunta 10) pasa a ser bloqueante para los tres modelos.
- Modelos en `architecture/datos/modelo-consolidacion.md` y `modelo-mercado-externo.md`, versionados con migraciones.
- `alcance.md` se actualiza: este proyecto diseña esos esquemas, pero no implementa ETL, IA ni scraping.
