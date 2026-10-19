# Modelo de MercadoExterno (`mercado_externo`) — borrador

> Extensión de VCdb con vehículos, marcas y equipos que **no** están en AutoCare (ADR 0014). Estructura espejo de `autocare_global`
> (`vcdb_base`, `vcdb_config`, `vcdb_parts`) con nombres de columna iguales a AutoCare para que las consultas sean intercambiables.

## Reglas
- IDs ≥ **1 000 000 000** en todas las tablas (secuencias que arrancan ahí).
- Las FK pueden apuntar a IDs de AutoCare (< 1e9) o a IDs propios (≥ 1e9). Por ejemplo, un `model` propio con `make_id` de Changan oficial.
- Columnas comunes en cada tabla: `origen` (`IA_WEB`/`APP`), `creado_por`, `creado_en`, `evidencia` JSONB (URLs, fichas), `confianza` (0–1),
  `estado` (`ACTIVO`, `REEMPLAZADO`, `DESCARTADO`), `reemplazado_por_id`.
- Llave normalizada única por nivel (p. ej. `model`: `make_id` + `model_name_norm`; `base_vehicle`: `year_id` + `make_id` + `model_id`).
  Antes de insertar se busca en AutoCare **y** aquí.
- Nunca se borra.

## Tablas
> Fuente de verdad: `db/mercado_externo/migraciones/`. Contrato y ejemplos: `db/mercado_externo/README.md`.

| Tabla (`vcdb.`) | Equivalente AutoCare | Notas |
|---|---|---|
| `make` | `vcdb_base.make` | Solo marcas que no existen en AutoCare (p. ej. Great Wall) |
| `model` | `vcdb_base.model` | `make_id` propio o de AutoCare |
| `base_vehicle` | `vcdb_base.base_vehicle` | `year_id` + `make_id` + `model_id` |
| `sub_model` | `vcdb_base.sub_model` | |
| `base_vehicle_region` | (detalle) | Localización: regiones y `nombre_mercado`; acepta base vehicles de AutoCare o propios |
| `engine_config` / `base_vehicle_engine` | `vcdb_config.engine_config` / `vehicle_to_engine_config` | Simplificado: litros, cc, cilindros, combustible, aspiración, designación |
| `transmission` / `base_vehicle_transmission` | `vcdb_config.transmission` / `vehicle_to_transmission` | Tipo y velocidades |
| `mfr`, `equipment_model`, `equipment_base` | `vcdb_parts.mfr`, `vcdb_base.equipment_*` | Plantas, montacargas, maquinaria |
| `v_base_vehicle` (vista) | — | AutoCare + propio, para buscadores |

## Cómo se consulta junto con AutoCare
Las dos bases están en el mismo servidor. Opciones (decidir en la implementación):
1. **Adaptador en la APP** que consulta ambas y une resultados (simple, sin dependencias en la BD).
2. **`postgres_fdw`** en Nexo/Consolidación con vistas `v_base_vehicle`, `v_make`… que unen AutoCare + MercadoExterno.

## Escritores
| Escritor | Cómo |
|---|---|
| IA con búsqueda web (otro proyecto) | `vcdb.fn_registrar_vehiculo(...)` / `vcdb.fn_registrar_equipo(...)`: verifican en AutoCare (`ref`) y aquí, y devuelven el ID existente o el nuevo |
| APP | Las mismas funciones, con `origen = APP` y el usuario |
