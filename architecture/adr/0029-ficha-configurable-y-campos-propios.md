# 0029. Ficha de atributos configurable desde la consola y campos propios de Nexo

- **Estado:** Aceptada. Implementada en la migración 0019 y la consola (2026-11-17). Los operadores pueden solicitar campos
  desde la ficha: ADR 0030.
- **Fecha:** 2026-11-17

## Contexto
El catálogo de atributos por tipo de parte (ADR 0019, `meta.atributo_config`) se carga desde AutoCare (PAdb) y ya era
configurable sin migraciones, pero solo con SQL: no había pantalla. La ficha del radiador se armó en una migración, y los otros
tipos de parte no tenían ficha. Además, la empresa necesita capturar datos que AutoCare no tiene (por ejemplo, el tipo de aleta),
y el catálogo solo admitía atributos de PAdb: la carga de AutoCare marcaba como obsoleto todo lo que AutoCare no publica.

## Decisión
- **Pantalla «Ficha de atributos»** (`/configuracion-ficha`) para el tipo de parte del filtro global, solo con el **permiso especial
  `CONFIGURAR_FICHA`** por usuario (como `VER_ANALISIS_VENTAS` y `EMPAREJAR_CATALOGO`), independiente del rol. Permite:
  - agregar a la ficha cualquier atributo que AutoCare admite para el tipo de parte, o quitarlo (lo capturado se conserva);
  - marcar obligatorio (bloquea el envío a revisión), nombre en la ficha, grupo y orden;
  - **precarga desde SAP**: columna de SAP del artículo y cómo se convierte (número, número en texto, parte de una medida, lista
    homologada, texto, sí/no);
  - **homologación** de valores de SAP a opciones (muestra los valores que trae SAP en esa columna y cuántos artículos tienen cada
    uno); vale para todos los tipos de parte con ese atributo;
  - **traducción** al español de los valores de AutoCare.
- **Campos propios de Nexo**, que AutoCare no tiene, de cuatro tipos: número (o medida en mm), lista de opciones, texto libre y
  sí/no. Viven en las mismas tablas (`meta.atributo_config` con `tipo`; opciones en `meta.atributo_valor_permitido`) con códigos
  desde **1 000 000** (`meta.codigo_propio`), para no chocar nunca con PAdb. La carga de AutoCare no los toca. Se validan por tipo
  (un sí/no solo acepta `SI` o `NO`) y la ficha del artículo los muestra como «Campo propio de Nexo».
- Un campo propio se **borra** solo si ningún artículo lo usa; si no, se quita de la ficha. Las opciones propias se agregan,
  renombran (los artículos conservan la opción) o quitan si nadie las usa. Las opciones de AutoCare no se cambian, solo se traducen.
- **Por ahora los campos propios solo viven en Nexo**: el proceso de salida no los envía a SAP (`contratos.md`).
- Toda la configuración queda auditada (`audit.auditoria_evento`).

## Consecuencias
- Las fichas de los otros tipos de parte se arman desde la consola, sin código ni migraciones.
- Un atributo nuevo marcado obligatorio cuenta para los artículos que se envíen a revisión desde ese momento; lo ya validado no
  cambia de estado.
- La categoría Intercambiador no tiene tipo de parte de AutoCare, así que todavía no tiene ficha que configurar.
- Si un campo propio debe salir a SAP o a otro sistema, se decide con ese proyecto y se documenta en `contratos.md`.
