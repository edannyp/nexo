# 0018. Código equivalente de fabricados, validado con foto

- **Estado:** Aceptada
- **Fecha:** 2026-10-16

## Contexto
La regla 4 del flujo pedía, para enviar un fabricado a `POR_VALIDAR`, su importado equivalente confirmado o una justificación.
Con el lote real de SAP (2026-10-16), solo 30 de los 2 625 fabricados activos tienen en `U_CodAnterior` el `ItemCode` de un importado.
El resto apunta a otro fabricado (557, códigos viejos) o a códigos de proveedor/OEM (~2 000). La regla habría frenado casi todos los
fabricados. La estrategia de validación de fabricados se definirá más adelante (pregunta 24).

## Decisión
- La equivalencia **ya no es requisito** para `POR_VALIDAR`. Se elimina `justificacion_sin_equivalente`.
- `app.articulo.codigo_equivalente` (texto libre: `ItemCode`, OEM o proveedor). El operador lo captura en una **revisión de fabricados**
  (`app.v_revision_fabricados`), con `codigo_anterior` como sugerencia; se registra quién y cuándo.
- Un supervisor o administrador lo valida con `app.fn_validar_codigo_equivalente`, que exige al menos una **foto propia validada**
  (ADR 0013). Estados en la bandeja: `SIN_CODIGO` → `ESPERA_FOTO` → `LISTO_PARA_VALIDAR` → `VALIDADO`.
- Cambiar el código borra su validación. Si el código es el `ItemCode` de un importado de la misma categoría, se crea la
  equivalencia `SUGERIDA` en `app.articulo_equivalencia` (ADR 0005); la herencia sigue requiriendo que se confirme.
- Esta validación es independiente del estado del artículo (no lo cambia ni lo bloquea).

## Consecuencias
- Los fabricados avanzan por el flujo normal; la equivalencia se completa a su ritmo, conforme llegan las fotos.
- Cuando se defina la estrategia, se podrá volver a exigir el código validado como requisito sin cambiar el modelo.
- Migración `apps/api/alembic/sql/0003_codigo_equivalente.sql`.
