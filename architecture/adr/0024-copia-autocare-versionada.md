# 0024. Copia de AutoCare acotada y versionada

- **Estado:** Aceptada. Implementada en Nexo 0014, Consolidación V003 y MercadoExterno V004 (2026-10-21).
- **Fecha:** 2026-10-21

## Contexto
`db/ref/cargar_ref.py` copiaba AutoCare completo (PCdb, PAdb, VCdb) a los esquemas `ref` con un *upsert*. Dos problemas:
- PCdb/PAdb completos son casi todo ruido: 629 344 valores y 142 739 atributos, de los que Nexo usa 1 302 y 207 (sus 8 categorías).
- Al actualizar AutoCare no se sabía qué cambió, y lo que AutoCare quitó seguía en `ref` como válido (o, si se borraba, rompía
  las partes y aplicaciones que ya lo usaban).

## Decisión
- **Solo nuestros tipos de parte:** PCdb y PAdb se copian filtrados por los tipos de parte de las 8 categorías (`TIPOS_ALCANCE`;
  `--todo` copia todo). **VCdb se copia completo**: las aplicaciones pueden ser de cualquier vehículo.
- **Cada carga se compara con la anterior**, tabla por tabla: altas, cambios, bajas y reactivados, con las versiones de AutoCare.
  El resultado y su **impacto** (lo dado de baja o cambiado que ya está en uso) quedan en `ref.historial_carga` (Consolidación,
  MercadoExterno) y `meta.historial_referencia` (Nexo). Con `--nexo` se mide también el impacto en las aplicaciones de Nexo.
- **Lo que AutoCare quita no se borra:** se marca `obsoleto_en`. Lo obsoleto **no se asigna de nuevo** (los triggers lo rechazan
  en filas nuevas o al cambiar el valor); lo que ya lo usa se conserva y se puede editar. Si AutoCare lo vuelve a publicar, se reactiva.
- **Defensa:** si una tabla quedaría con más del 20 % de sus filas obsoletas (y más de 10), la carga se detiene sin aplicar nada.
  Casi siempre es una lectura de AutoCare incompleta; `--forzar` solo después de revisarlo.

## Consecuencias
- Nexo deja de ofrecer atributos y valores obsoletos (ficha, precarga desde SAP, requisitos para validar, Panorama); los que un
  artículo ya tiene se siguen mostrando. Un atributo obsoleto nuevo da `ATRIBUTO_OBSOLETO`; un valor obsoleto, `VALOR_NO_VALIDO`.
- La carga del catálogo maestro recibe un rechazo si asigna algo obsoleto (tipo de parte, atributo, valor o vehículo): debe tomar
  lo vigente de `ref` (`obsoleto_en is null`). En MercadoExterno las funciones de registro siguen viendo lo obsoleto como "existe
  en AutoCare", para no duplicarlo.
- La primera carga filtrada depura de Consolidación lo de otros tipos de parte que ninguna parte usa (nunca lo que está en uso).
- Revisar el historial después de cada actualización de AutoCare es parte del procedimiento (`deploy/README.md`).
- Agregar una categoría a Nexo exige agregar su tipo de parte a `TIPOS_ALCANCE` y volver a cargar.
