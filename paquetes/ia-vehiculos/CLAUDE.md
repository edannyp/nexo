# Guía para agentes — IA de vehículos fuera de AutoCare (MercadoExterno)

## Qué es este repositorio
El proceso que busca en la web **vehículos, marcas y equipos que no están en AutoCare** (por ejemplo, modelos de Changan o Great
Wall vendidos en Guatemala, o plantas Generac) y los registra en **MercadoExterno** (`mercado_externo`), una extensión de VCdb con
la misma estructura y estándar ACES (ADR 0014). **El esquema lo gobierna Nexo** (otro repositorio).

Nexo usa MercadoExterno junto con AutoCare en su selector de vehículos: lo que registres aparecerá a los operadores al asignar
aplicaciones a los artículos. Por eso cada registro necesita **evidencia** y datos que un operador pueda reconocer.

Lee antes de proponer o escribir código:
1. `db/mercado_externo/README.md`: **el contrato** (cómo se registra, qué rechaza la base).
2. `contexto/arquitectura/modelo-mercado-externo.md` y `contexto/fuentes/mercado-externo.md`.
3. `db/pruebas/probar.py`, función `probar_mercado`: ejemplos de lo que la base acepta y lo que rechaza.

## La regla principal
**Nadie inserta directo.** Todo pasa por las funciones de la base, que primero buscan en AutoCare y en MercadoExterno y solo
insertan lo que falta:
- `vcdb.fn_registrar_vehiculo(marca, modelo, año_desde, año_hasta, 'IA_WEB', creado_por, evidencia, confianza, regiones, nombre_mercado)`
  → un `base_vehicle_id` por año. Si ya existe en AutoCare, devuelve **su** ID (`catalogo = 'AUTOCARE'`) y no inserta nada.
- `vcdb.fn_registrar_configuracion(base_vehicle_id, submodelo, litros, cilindros, combustible, 'IA_WEB', creado_por, aspiracion,
  designacion, evidencia)` → submodelo + motor del vehículo (lo que Nexo exige para confirmar una aplicación).
- `vcdb.fn_registrar_equipo(fabricante, modelo, 'IA_WEB', creado_por, evidencia, confianza)` → plantas, montacargas, maquinaria.

Son seguras ante llamadas repetidas o simultáneas: registrar dos veces lo mismo devuelve el mismo ID.

## Reglas que no se negocian
- **Evidencia obligatoria:** URLs o fichas técnicas en `evidencia` (JSON). Sin evidencia, la base rechaza el registro.
- **`confianza` honesta (0–1).** No requiere aprobación humana, así que la confianza es lo único que distingue lo seguro de lo dudoso.
- **Regiones VCdb** (`GTM`, `SLV`, `HND`…): solo las que existen en `ref.region`.
- **Motor identificable:** litros o código de motor; el submodelo es «Base» si no tiene otro nombre.
- **Nunca `DELETE`** (lo impide la base). Lo que AutoCare incluya después lo reconcilia el equipo de Nexo.
- **Sin DDL:** las tablas y funciones vienen de `db/mercado_externo/migraciones/`. Si falta algo, se pide al equipo de Nexo.
- **Credenciales solo en `.env`** (no leas `.env`). Nunca en código, documentos ni commits.
- **Las pruebas usan la base local**, nunca el servidor.

## Ambientes
| | Base | Usuario |
|---|---|---|
| Desarrollo | `mercado_externo` en el contenedor `postgres` (PostgreSQL 16) | `postgres` |
| Producción | `mercado_externo` en `10.20.20.6` (PostgreSQL 16) | uno en `grp_mercado_registro` (lo crea el administrador) |

## Cómo probar
1. `bash base-local/levantar.sh`: MercadoExterno local con las migraciones reales y la referencia de AutoCare (mínima o real).
2. `uv run db/pruebas/probar.py --host postgres`: las pruebas del contrato.
3. Corre tu proceso contra la base local y revisa `vcdb.v_base_vehicle` (AutoCare + MercadoExterno, como lo ve Nexo).

## Pendiente de acordar con el equipo de Nexo
- Qué dispara una búsqueda (lista de marcas/modelos de SAP sin homologar, aplicaciones sin homologar de Consolidación, pedidos).
- Umbral de `confianza` a partir del cual Nexo muestra el vehículo sin advertencia.
- Frecuencia (lo orquesta Airflow).

## Convenciones
- Documentación y nombres de dominio en español; código técnico en inglés cuando sea idiomático.
- Python 3.13 con `uv`; `psycopg` para PostgreSQL.
