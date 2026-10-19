# 0017. Un usuario de base de datos por proceso, con permisos mínimos

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
Todas las conexiones usan hoy el superusuario `postgres`. La APP, el ETL de entrada, el proceso de carga de Consolidación y la IA de
vehículos escriben en bases compartidas del mismo servidor.

## Decisión
| Usuario | Base(s) | Permisos |
|---|---|---|
| `app_nexo` | `nexo` | Lectura/escritura en `app`, `audit`, `meta`; sin DDL |
| `app_lectura` | `autocare_global`, `articulos_consolidacion` | Solo `SELECT` |
| `app_mercado` | `mercado_externo` | `SELECT` + `EXECUTE fn_registrar_vehiculo` |
| `etl_entrada` | `nexo` | `INSERT/UPDATE` en `staging` + `EXECUTE fn_procesar_staging` |
| `consolidacion_carga` | `articulos_consolidacion` | Lectura/escritura en `catalogo` y `carga`; sin DDL |
| `ia_vehiculos` | `mercado_externo` | `SELECT` + `EXECUTE fn_registrar_vehiculo` |
| `exploracion` | todas | Solo `SELECT` (scripts de `connections/` en desarrollo) |
| `migrador` | `nexo`, `articulos_consolidacion`, `mercado_externo` | Dueño de los esquemas; solo lo usan las migraciones |

- Los roles y `GRANT`s se crean en las migraciones del repositorio como **roles de grupo sin login** (`grp_consolidacion_carga`,
  `grp_mercado_registro`, `grp_app_lectura`, `grp_exploracion`; ver `db/README.md`). Los usuarios con contraseña los crea el
  administrador y los asigna al grupo; **las contraseñas nunca van al repositorio**.
- Nadie escribe directo en tablas sensibles: las transiciones y altas de vehículos pasan por funciones `SECURITY DEFINER`.

## Consecuencias
- Hay que pedir al administrador del servidor Postgres que cree los usuarios y entregue las credenciales por canal seguro.
- `.env.example` y `connections/common/config.py` se ajustan a un usuario por conexión.
