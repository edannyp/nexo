# 0030. Solicitud de campos desde la ficha y campos oficiales

- **Estado:** Aceptada. Implementada en la migración 0020 y la consola (2026-11-17).
- **Fecha:** 2026-11-17

## Contexto
Con ADR 0029, solo quien tiene el permiso `CONFIGURAR_FICHA` crea campos propios. Quien trabaja los artículos es quien descubre que
falta un dato, y no tenía cómo pedirlo sin salir de Nexo. Se quiere un proceso de **campos oficiales**: lo que propone un operador
se puede usar enseguida, pero debe distinguirse de lo aprobado hasta que alguien lo revise.

## Decisión
- **Operadores y supervisores solicitan un campo** desde la pestaña Ficha del artículo («Solicitar un campo»): nombre, tipo
  (número o medida, lista con opciones, texto, sí/no), grupo y **para qué se necesita** (obligatorio).
- El campo queda **`PROPUESTO`** (`meta.atributo_config.estado`) y **aparece enseguida en la ficha de todos los artículos de ese tipo
  de parte**, marcado «Propuesto» en la ficha y en el Resumen. Se puede capturar, pero **no puede ser obligatorio** (no bloquea el envío
  a revisión).
- Quien tiene `CONFIGURAR_FICHA` lo revisa en **Ficha de atributos → Solicitudes**, con quién lo pidió, cuándo y para qué. Puede
  ajustarlo (nombre, grupo, opciones, precarga) y:
  - **aprobarlo**: queda **`OFICIAL`**, y desde entonces puede ser obligatorio;
  - **rechazarlo con motivo**: queda **`RECHAZADO`** y sale de la ficha. **Lo capturado se conserva oculto** y auditado; si alguien
    vuelve a pedir un campo con ese nombre, ve el motivo. Un rechazado se puede **reconsiderar** (aprobar) y vuelve con lo capturado.
- Los atributos de AutoCare y los campos propios creados desde la configuración son oficiales desde el inicio. Solo los campos
  propios pueden estar propuestos o rechazados.

## Consecuencias
- Se guardan quién lo pidió y cuándo (`solicitado_por`, `solicitado_en`, `motivo_solicitud`) y quién lo revisó (`revisado_por`,
  `revisado_en`, `motivo_rechazo`).
- Un campo propuesto sigue las reglas de ADR 0029: solo vive en Nexo y la carga de AutoCare no lo toca.
- Todavía no hay aviso fuera de la pantalla: las solicitudes pendientes se ven en el contador de la pestaña Solicitudes.
