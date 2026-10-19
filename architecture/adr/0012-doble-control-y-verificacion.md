# 0012. Workflow con doble control y cola de verificación

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
- Sin pre-match automático (ADR 0011), el operador empareja en la APP. Los primeros miles de emparejamientos fijan el criterio
  y un error se propaga de regreso a SAP.
- Las fotos propias se irán cargando de forma progresiva (una persona las sube a MinIO), así que un artículo ya validado
  recibirá fotos después.
- Se planea un mantenimiento periódico de verificación de la calidad.

## Decisión
- **Doble control**: `PENDIENTE` → (operador) → `POR_VALIDAR` → (supervisor) → `VALIDADO` | `RECHAZADO`. Quien valida no puede
  ser quien envió el artículo.
- Toda vuelta atrás (cambio de hash, reapertura, verificación con hallazgo) regresa a **`PENDIENTE`** con motivo, conservando lo ya hecho.
- **Verificación** como cola de tareas separada del estado (`tarea_verificacion`): `NUEVA_FOTO`, `MUESTREO`, `CAMBIO_CATALOGO`, `MANUAL`.
  Solo cambia el estado si encuentra un problema.
- Roles: `OPERADOR`, `SUPERVISOR`, `ADMINISTRADOR`. Un supervisor también puede operar, pero nunca validar su propio envío.

## Consecuencias
- `context/workflow-estados.md` se reescribe; `transicion_permitida` incluye el rol requerido.
- Hay que detectar fotos nuevas en MinIO para crear tareas `NUEVA_FOTO` (pregunta 16).
- Más adelante se puede habilitar validación directa para operadores con experiencia (nueva decisión).
