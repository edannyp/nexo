# Guía para agentes — Agente de revisión del catálogo (Consolidación → verificaciones de Nexo)

## Qué es este repositorio
Un **agente de IA independiente** que vigila el catálogo maestro (Consolidación) por debajo de lo que **Nexo** (el puente de gobernanza
del artículo, otro repositorio) ya validó.

En Nexo, un operador empareja cada artículo de SAP con una parte del catálogo, completa su ficha y aplicaciones, y un supervisor lo
valida. Después, el catálogo puede cambiar: una parte se fusiona con otra, se descarta, desaparece, o una fuente corrige sus medidas,
números o vehículos. Este agente detecta esos cambios, **explica** cada uno en una nota y se lo entrega a Nexo. **Nexo no implementa esta revisión**: solo expone el contrato y muestra las verificaciones. Nexo crea una
verificación `CAMBIO_CATALOGO` para que un supervisor la revise: si es conforme, queda; si hay hallazgo, el artículo vuelve a
Pendiente, un operador lo corrige y se valida de nuevo. Así el ciclo se repite (ADR 0012).

Lee antes de proponer o escribir código:
1. `contexto/arquitectura/contratos.md`, sección *Agente de revisión del catálogo*: el contrato.
2. `contexto/workflow-estados.md`, sección *Verificación*.
3. `contexto/arquitectura/modelo-consolidacion.md`: `catalogo.parte` (estado, `fusionada_en_id`), `parte_numero`, `parte_atributo`
   (medidas del panal en mm: PAdb 267 alto, 269 largo, 268 ancho), `parte_aplicacion`.

## El contrato, en corto
Con el usuario `agente_revision_catalogo` en `nexo` (solo puede ejecutar estas tres funciones):
1. `select parte_id, articulos from app.fn_partes_emparejadas()` → las partes a revisar.
2. `select * from app.fn_datos_emparejamiento(array[…]::bigint[])` → por parte y artículo, **lo que se validó**: `item_code`,
   `descripcion`, `linea`, `es_principal`, `validado_en`, `numero_parte_proveedor`, `codigo_anterior`, `atributos` (JSON por `paid`
   con `valor_num`/`uom_code`/`valid_value_id`/`valor_texto`) y `aplicaciones` (JSON con `base_vehicle_id`, `sub_model_id`,
   `engine_config_id`).
3. Leer la parte en Consolidación (solo lectura) y comparar.
4. `select app.fn_registrar_cambios_catalogo('<lista JSON>')` con los cambios. Devuelve `{recibidos, tareas, repetidos}`:
   - `{"parte_id": 5003, "estado": "FUSIONADA", "fusionada_en_id": 9001}`, `{"parte_id": 5004, "estado": "DESCARTADA"}`,
     `{"parte_id": 5005, "estado": "NO_EXISTE"}`: afectan a todos los artículos validados de esa parte.
   - `{"parte_id": 5006, "estado": "DATOS_CAMBIARON", "item_code": "RAD00188", "huella": "…", "nota": "…", "campos": ["267"]}`:
     un cambio de datos que importa para ese artículo.

## Cómo decidir y cómo escribir
- **Qué es un cambio que importa:** una medida del panal que ya no coincide con la validada (más de ±10 mm, la tolerancia de Nexo),
  un número OEM o de proveedor que se quitó o cambió de dueño, aplicaciones validadas que la parte ya no tiene. Una fuente nueva que
  solo confirma lo mismo **no** es un cambio.
- **La `nota` la lee un supervisor**, en español claro: qué decía antes, qué dice ahora y de qué fuente. Por ejemplo:
  «El catálogo ahora da alto 410 mm (JJ Radiator 945); el artículo se validó con 400 mm». Entre 10 y 2 000 caracteres.
- **La `huella` cierra el ciclo:** debe ser **determinista**, derivada de los datos de la parte que comparaste (por ejemplo, sha256 del
  JSON ordenado de esos datos). Nexo no vuelve a crear una verificación con la misma huella para el mismo artículo, aunque el
  supervisor ya la haya resuelto. Si los datos vuelven a cambiar, la huella será otra y se informará de nuevo.
- **No decide** si el artículo está mal ni lo corrige: solo informa. La decisión es del supervisor en Nexo.

## Reglas que no se negocian
- **El usuario de Nexo solo ejecuta esas tres funciones**; no lee ni escribe tablas de Nexo.
- **Consolidación es solo lectura** para este agente (la escribe la carga del catálogo maestro, otro proceso).
- **Sin DDL** en ninguna base; los cambios de contrato se piden al equipo de Nexo.
- **Credenciales y llaves de API solo en `.env`** o en el orquestador (no leas `.env`). Nunca en código, documentos ni commits.
- **Las pruebas usan las bases locales**, nunca los servidores.

## Ambientes
| | Nexo | Consolidación |
|---|---|---|
| Desarrollo | `nexo` local, `agente_revision_catalogo` / `agente` | `articulos_consolidacion` local, `postgres` |
| Producción | `nexo` en `10.10.60.6`, `agente_revision_catalogo` | `consolidacion_articulos` en `10.10.60.6`, usuario de `grp_app_lectura` |

## Cómo probar
1. `bash base-local/levantar.sh`: Consolidación local con tres partes (1, 2, 3) y Nexo local con tres artículos validados emparejados
   con ellas y el usuario del agente.
2. Simula cambios en la Consolidación local:
   - `update catalogo.parte set estado = 'DESCARTADA' where id = 3;`
   - o cambia una medida en `catalogo.parte_atributo` de la parte 1.
3. Corre el agente.
4. `psql "$NEXO_LOCAL_ADMIN" -f base-local/verificar.sql` muestra las verificaciones creadas con su nota.
5. Córrelo otra vez: no debe crear nada nuevo (`repetidos`).

## Pendiente de acordar
- Cuándo corre: después de cada carga del catálogo maestro o a hora fija.
- Qué modelo y qué orquestación usa el agente.
- A quién se avisa si falla.

## Convenciones
- Documentación y nombres de dominio en español; código técnico en inglés cuando sea idiomático.
- Python 3.13 con `uv`; `psycopg` para las dos bases.
