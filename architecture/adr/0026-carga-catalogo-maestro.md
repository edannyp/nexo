# 0026. Carga del catálogo maestro: diagramas y JJ Radiator

- **Estado:** Aceptada. Contrato en Consolidación V004 (2026-10-23).
- **Fecha:** 2026-10-23

## Contexto
El proceso 2 llena Consolidación (ADR 0011) desde dos fuentes en 10.20.20.6: `db_diagrams` (7 405 diagramas propios, con OEM y
medidas en texto) y `db_scrapper` (JJ Radiator: 15 513 artículos de 9 tipos, vehículo en texto libre, OEM con estado de
verificación). `db_diagrams.jjradiator_cross_reference` ya cruza diagrama ↔ JJ (6 953 cruces 1 a 1: 4 138 confirmados por OEM o
dimensiones y 2 815 «revisar_manual»). El proceso lo construye otro desarrollador (con un agente de IA); Nexo define el contrato.

## Decisión
1. **Tipos:** solo los de las categorías de Nexo: Radiator y Truck Radiator → 2172, AC Condensers → 6708, Intercooler → 12616,
   Radiator Tanks → 48305/17700/17701. Termostatos, tapones y herramientas no entran. La copia de AutoCare incluye las
   alternativas de PCdb de cada categoría (`TIPOS_ALCANCE`).
2. **Misma pieza:** entran todos los diagramas y todos los artículos de JJ. Los cruzados se unen en una parte: los `confirmado`
   con confianza 1,0 y los `revisar_manual` también (decisión del negocio), con confianza 0,5 y, si el OEM no coincide, un
   conflicto `NUMERO_DUPLICADO`. Lo que no tiene cruce es una parte propia.
3. **OEM:** se publican confirmados (1,0) y pendientes o sin verificación (0,5); los inconclusos y descartados quedan solo en los
   datos crudos.
4. **Vehículos:** el proceso homologa a AutoCare solo lo inequívoco; el resto va a `aplicacion_sin_homologar` con el texto. Los
   vehículos que faltan en AutoCare los registra el proceso 3 (IA de vehículos, MercadoExterno), no este.
5. **Medidas:** con espesor doble (`16/26`), el espesor del panal es el primer número; el texto queda en `valor_original`.
6. **Imágenes:** las de JJ se copian a MinIO (`rlt-diagramas/jjradiator/…`) y se guarda también la URL original.
7. **Corridas de foto completa** por fuente: lo que no viene queda `vigente = false` (nunca se borra). `carga.fn_cerrar_corrida`
   lo aplica con defensa: si faltaría más del 5 % (y más de 10), `CORRIDA_INCOMPLETA` y no aplica nada.
8. **Prioridad:** diagramas 1, JJ 2. La búsqueda toma cada medida de la fuente de mayor prioridad vigente; si difieren más de 2 mm
   entre fuentes, conflicto `ATRIBUTO_DISCREPA`.

## Consecuencias
- Unir los dudosos da menos candidatos repetidos al operador, pero puede juntar piezas distintas: la confianza 0,5 y los
  conflictos lo dejan visible, y la trazabilidad por `registro_fuente_id` permite separarlas sin perder datos.
- Un registro leído sin cambios igual actualiza `corrida_id` (sin cambiar `actualizado_en`): es lo que hace posible la foto completa.
- Las fuentes nuevas (NRF, CSF, TYC…) necesitan su propia regla de cruce antes de entrar.
