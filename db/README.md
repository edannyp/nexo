# db/ — Esquemas que gobierna este proyecto fuera de Nexo

Paquete de contrato para los procesos de otros proyectos. Nexo tendrá sus migraciones en `apps/api/alembic/`.

| Carpeta | Base | Quién escribe | Contrato |
|---|---|---|---|
| [consolidacion/](consolidacion/) | `articulos_consolidacion` | Proceso de scraping/consolidación (otro desarrollador) | [README](consolidacion/README.md) |
| [mercado_externo/](mercado_externo/) | `mercado_externo` | IA con búsqueda web y la APP, vía funciones | [README](mercado_externo/README.md) |
| [ref/](ref/) | — | Copia de referencia de AutoCare para validar en la base | `cargar_ref.py` |
| [pruebas/](pruebas/) | bases locales desechables | — | `probar.py` |

## Flujo
1. **Migraciones:** `uv run db/aplicar.py <base>` aplica en orden `migraciones/V###__*.sql`, cada una en su transacción, y
   registra versión y checksum en `public.esquema_version`. Una migración aplicada **no se edita**: se agrega otra.
   Contra un host que no sea local exige `--servidor`.
2. **Referencia AutoCare:** `uv run db/ref/cargar_ref.py <base>` copia (upsert) lo necesario de `autocare_global` al esquema `ref`.
   Con `nexo` carga el catálogo de atributos PIES de Nexo (`meta.atributo_config`, ADR 0019) sin tocar su configuración.
   Correrlo después de las migraciones y cada vez que se actualice AutoCare. Los triggers validan contra `ref`.
3. **Pruebas:** `uv run db/pruebas/probar.py` crea `*_prueba` en el Postgres local, aplica todo con una referencia mínima
   (`pruebas/ref_minimo_*.sql`, IDs de vehículo sintéticos) y verifica lo que se acepta y lo que se rechaza.

## Permisos (ADR 0017)
Las migraciones `V002__permisos.sql` crean **roles de grupo sin login**. El administrador del servidor crea los usuarios con
contraseña (nunca en el repositorio) y los asigna:

```sql
create user scraping_consolidacion password '…' in role grp_consolidacion_carga;  -- Consolidación
create user ia_vehiculos           password '…' in role grp_mercado_registro;     -- MercadoExterno
create user app_lectura            password '…' in role grp_app_lectura;          -- ambas
```
