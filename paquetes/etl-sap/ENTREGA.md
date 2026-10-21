# Entrega: ETL de entrada SAP → Nexo

Este paquete es todo lo que necesitas para construir el ETL. Las reglas están en `CLAUDE.md`, que Claude Code lee solo; este
documento es para ti: qué recibes, qué pedir, cómo avanzar y cuándo está terminado.

## Qué recibes
- Un repositorio inicial con devcontainer (Python 3.13, `uv`, PostgreSQL 18 local) y Claude Code con memoria persistente.
- El contrato con Nexo y el contexto de gobernanza (`contexto/`), copiados del repositorio de Nexo.
- Una base `nexo` local idéntica a la de producción (`base-local/`), con el usuario `etl_entrada` y sus mismos permisos.
- Una lectura de referencia de SAP (`referencia/lote_sap_local.py`): muestra la consulta y el orden correctos. **No es el ETL.**
- Cómo encaja con tu arquitectura medallion (Airflow, Spark, HDFS): sección *Cómo encaja…* de `CLAUDE.md`.

## Qué necesitas pedir
| Qué | A quién | Cuándo |
|---|---|---|
| Docker, VS Code con Dev Containers y una cuenta de Claude Code | TI | Antes de empezar |
| Usuario de **solo lectura** de SAP HANA (esquema de la sociedad) y red hacia SAP | TI / SAP | Etapa 1 |
| Usuario `etl_entrada` de producción (`10.10.60.6`, base `nexo`) y red hacia ese servidor | Equipo de Nexo | Etapa 2 |
| Conexiones en Airflow | Equipo de Airflow | Etapa 3 |

## Etapas
1. **Desarrollo local.** El ETL lee SAP y escribe en la base local. Termina cuando pasan las pruebas de la sección *Cómo probar*
   de `CLAUDE.md` y una corrida con SAP real da, en la base local, dos resultados:
   - la primera vez, todos `nuevos`;
   - la segunda, todos `sin_cambios`.
2. **Primera carga en producción, coordinada con el equipo de Nexo.** Avisa antes de correrla: Nexo hace una carga de referencia de
   la misma SAP y compara las dos, artículo por artículo. Si algo no coincide, se corrige antes de seguir.
3. **Programación en Airflow**, con la frecuencia acordada y alertas si falla o si Nexo responde `LOTE_INCOMPLETO`.

## Cuándo está terminado
- [ ] Las pruebas automáticas cubren los escenarios de `CLAUDE.md` y corren sin SAP ni servidores.
- [ ] Cada corrida abre un lote de foto completa y registra el resultado de `app.fn_procesar_staging`.
- [ ] Ante `LOTE_INCOMPLETO` u otro error, alerta y no reintenta a ciegas.
- [ ] Ninguna credencial en el repositorio (`.env` y conexiones de Airflow).
- [ ] El `README` explica cómo correrlo a mano y cómo se programa.
- [ ] **La verificación de Nexo de la primera carga sale sin diferencias**: mismos artículos, misma huella (`hash_control`) por
      artículo y mismos hallazgos de calidad que la carga de referencia.

## Si algo del contrato no alcanza
No cambies tablas ni funciones de Nexo: pide el cambio al equipo de Nexo, que lo agrega con una migración y te entrega el paquete
actualizado.
