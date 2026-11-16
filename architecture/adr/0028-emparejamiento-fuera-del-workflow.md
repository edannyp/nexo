# 0028. Emparejamiento fuera del workflow, con permiso propio

- **Estado:** Aceptada. Implementada en la migración 0018 y la consola (2026-11-16).
- **Fecha:** 2026-11-16

## Contexto
Emparejar un artículo con el catálogo maestro (decir a qué pieza o diagrama corresponde, ADR 0011) era una pestaña del modo
Trabajar, «Emparejamiento y diagramas», con la misma regla que la ficha: solo quien tenía el artículo reservado y en Pendiente o
Rechazado. Desde ADR 0025 dejó de ser requisito para enviar a revisión (lo es el vehículo principal), pero seguía pareciendo un paso
del proceso del operador (pestaña de trabajo, diagrama del proceso, recorridos, plantilla de rechazo «Emparejamiento incorrecto»).
Se decidió que emparejar es una tarea aparte, de pocas personas, que no debe mezclarse con completar y validar el artículo.

## Decisión
- **En el artículo, solo «Diagramas»** (solo lectura, para todos): a qué partes del catálogo maestro está enlazado, con la ★
  principal, imagen, medidas, números y avisos si la parte se fusionó o se descartó. Si no tiene ninguna: «Artículo sin enlace a
  diagramas». Aparece en el Resumen y como pestaña en Trabajar. Endpoint `GET /articulos/{id}/diagramas`.
- **Sección propia «Emparejamiento»** (`/emparejamiento`), solo con el **permiso especial `EMPAREJAR_CATALOGO`** por usuario (como
  `VER_ANALISIS_VENTAS`, ADR 0022), independiente del rol. Lista los artículos del tipo elegido, primero los **sin emparejar** (también
  emparejados o todos, con búsqueda y orden por venta), y abre el emparejador (`/emparejamiento/{id}`): candidatos con puntaje,
  búsqueda manual, comparación, comparar fotos, vincular, principal y desvincular.
- **Regla de edición propia:** se empareja **cualquier artículo activo, en cualquier estado y sin reservarlo**; el estado no cambia.
  Se conserva el control optimista (versión del artículo). Al vincular, los atributos y aplicaciones de la parte se traen como
  sugerencias **solo si el artículo está en Pendiente o Rechazado**; en los demás estados solo se vincula, para no ensuciar la ficha
  de un artículo ya revisado.
- La API exige el permiso en `GET /articulos/{id}/emparejamiento` (y la comparación), `GET /catalogo/partes` y los `POST` de
  `/articulos/{id}/partes`; `403` si falta. Desde Catálogo maestro, «Emparejar» lleva a la sección (solo con el permiso).

## Consecuencias
- El operador ya no ve el emparejamiento como parte de su trabajo; el supervisor tampoco lo revisa al validar (se quitó la plantilla
  de rechazo «Emparejamiento incorrecto»). La verificación `CAMBIO_CATALOGO` sigue igual.
- Emparejar sube la versión del artículo: si alguien lo está trabajando a la vez, su siguiente guardado pide recargar.
- El administrador asigna el permiso en Administración → Usuarios.
- Los enlaces antiguos `?pestana=emparejamiento` del artículo abren el Resumen.
