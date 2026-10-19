# 0019. Catálogo configurable de atributos PIES por tipo de parte

- **Estado:** Aceptada e implementada en `apps/api/alembic/sql/0004_catalogo_atributos.sql` (2026-10-19).
- **Fecha:** 2026-10-19

## Contexto
La migración 0004 fija en SQL los atributos del radiador (`meta.atributo_requerido` + `meta.atributo_desde_sap`) y una bandera
`obligatorio`. Faltan los otros 7 tipos de parte, y PAdb ofrece muchos más atributos de los que el negocio usa: el radiador
admite 72. Agregar o quitar medidas no debería requerir una migración.

## Decisión
- **Un catálogo por tipo de parte** en Nexo, por ejemplo `meta.atributo_config`, que se carga desde PAdb con **todos** los atributos
  que admite cada tipo de parte en alcance (`part_attribute_assignment`), con su unidad y sus valores válidos.
- **Columnas de configuración**, editables por un administrador sin migración:
  - `habilitado`: el atributo se carga y se usa en la APP. Por defecto `false`, salvo los de la ficha actual.
  - `obligatorio`: bloquea `POR_VALIDAR` hasta que se confirma. Solo aplica si está habilitado.
  - `etiqueta`: nombre en el vocabulario del negocio ("Largo", "Ancho tanque").
  - `orden` y `grupo` para la ficha: Medidas, Materiales, Conexiones…
  - Precarga desde SAP: columna de origen, conversión (`NUMERO`, `NUMERO_EN_TEXTO`, `LISTA`, `TEXTO`, `PARTE_DE_MEDIDA`) y la parte de la
    medida. Absorbe `meta.atributo_desde_sap`.
- **Validación:** `app.articulo_atributo` solo acepta atributos **habilitados** para el tipo de parte del artículo, y valida el valor
  contra la lista y la unidad de PAdb. Es la misma regla que ya aplica Consolidación.
- **Fichas de origen:** los datos propios de la empresa van en el atributo PIES donde encajan. Ejemplos: tipo de panal → *Core Type*;
  dimensión tanques → *Inlet Header Length/Width*.
- **Actualización de AutoCare:** al cargar una versión nueva de PAdb se agregan los atributos nuevos deshabilitados y se conserva la
  configuración existente; nunca se borra un atributo ya usado.

## Consecuencias
- Los obligatorios de los otros 7 tipos de parte se definen **configurando**, sin código.
- La APP arma la ficha, las listas desplegables y las unidades a partir del catálogo.
- `fn_requisitos_por_validar` y `fn_precargar_atributos_sap` leen el catálogo en lugar de las tablas fijas.
- `uv run db/ref/cargar_ref.py nexo` alimenta el catálogo (verificado: 207 atributos y 1 302 valores válidos para los 7 tipos de
  parte con PCdb; Intercambiador aún no tiene tipo de parte).
