# Modelo de Nexo — borrador inicial

> Nombres según la nomenclatura canónica (ADR 0007). **Implementado** en `apps/api/alembic/sql/`:
> - `0001_nucleo.sql`: staging, `articulo`, máquina de estados, bitácora, usuarios, categorías, calidad SAP, diccionario.
> - `0002_enriquecimiento.sql`: emparejamiento, aplicaciones (+ regiones), atributos, equivalencias y herencia, imágenes,
>   verificación, homologación SAP ↔ AutoCare, requisitos completos para revisión y auditoría antes/después.
> - `0003_codigo_equivalente.sql`: `articulo.codigo_equivalente` de fabricados (texto libre, validado con foto propia),
>   bandeja `v_revision_fabricados`; la equivalencia deja de ser requisito para `POR_VALIDAR` (ADR 0018).
> - `0004_catalogo_atributos.sql`: catálogo configurable de atributos PIES por tipo de parte (ADR 0019), que reemplaza
>   `meta.atributo_requerido` y `meta.atributo_desde_sap`. Siembra la ficha del radiador; `db/ref/cargar_ref.py nexo` carga el resto desde PAdb.
> - `0005_auth.sql`: permisos especiales por usuario (`app.usuario_permiso`, ADR 0022), registro de accesos (`audit.evento_acceso`)
>   y auditoría de usuarios, roles y permisos sin el hash de la contraseña (ADR 0015).
> - `0006_ventas.sql`: copia de apoyo de ventas (`app.venta_mensual`, `app.venta_referencia`), parámetros (`meta.parametro`) e
>   indicadores relativos por tipo (`app.v_indicador_venta`: clase ABC, top %, participación, tendencia; ADR 0022).
> - `0007_bandejas.sql`: "Siguiente" con prioridad y doble control, reservas (`fn_reservar`, `fn_renovar_reserva`,
>   `fn_soltar_reserva`), índices trigram para la búsqueda y vistas guardadas (`app.vista_guardada`).
> - `0008_ficha.sql`: traducción al español de los valores PIES (`meta.traduccion_valor`, auditada), decisión UX 5.
> - `0009_aplicaciones.sql`: una aplicación de vehículo confirmada debe tener submodelo y motor (`aplicacion_vehiculo_completa`);
>   las sugeridas pueden llegar incompletas y se completan en el selector (decisión UX 4).
> Pruebas: `cd apps/api && uv run pytest`. La tabla de abajo queda como referencia; el DDL es la fuente de verdad.

## Configuración sin migraciones
- `meta.atributo_config` (ADR 0019): **todos** los atributos que PAdb admite para cada tipo de parte en alcance (los carga
  `uv run db/ref/cargar_ref.py nexo`; los nuevos entran deshabilitados). Un administrador configura:
  - `habilitado`: se usa en la APP; solo se capturan atributos habilitados (trigger `validar` en `app.articulo_atributo`);
  - `obligatorio`: bloquea `POR_VALIDAR` hasta que el operador lo confirma (exige `habilitado`);
  - `etiqueta` (vocabulario del negocio), `grupo` (MEDIDAS, MATERIALES, CONSTRUCCION, CONEXIONES, INCLUYE, OTROS), `orden`, `uom_defecto`;
  - precarga desde SAP: `columna_sap` + `conversion` (`NUMERO`, `NUMERO_EN_TEXTO`, `LISTA`, `TEXTO`, `PARTE_DE_MEDIDA` con `parte`).
  Los cambios quedan en `audit.auditoria_evento`. Ficha inicial del radiador (2172), 11 habilitados y obligatorios: Alto, Largo, Ancho,
  Filas, Tipo de panal, Tipo flujo, Material panal, Material tanque, Largo tanque, Ancho tanque, Diámetro entrada.
- `meta.atributo_valor_permitido`: valores válidos de PAdb por tipo de parte y atributo (listas de la APP y validación).
- `meta.valor_sap_pies`: traducción de valores de SAP a valores de PAdb (`LATON` → Brass, `HORIZONTAL` → Cross Flow).
- Lo precargado desde SAP es **sugerencia** (sin `confirmado_por`); para enviar a revisión solo cuenta lo confirmado por el operador.
- `app.v_ficha_atributo`: la ficha que arma la APP (atributos habilitados, en orden, con el valor del artículo y si está confirmado).

## Entidades candidatas
| Entidad | Propósito | Campos clave (tentativos) |
|---|---|---|
| `articulo` | Copia de trabajo del artículo SAP (solo categorías en alcance y línea IMPORTADO/FABRICADO) | `id`, `item_code` (único), `descripcion`, `categoria_id`, `part_terminology_id` (PCdb), `subcategoria_codigo` (`U_SubCat` tal cual), `linea` (IMPORTADO/FABRICADO, normalizada desde `@IGT_CAT2.Name`), `hash_control`, `estado`, `version`, `activo`, `motivo_inactivo` (ADR 0008), `asignado_a`, `asignado_hasta`, atributos canónicos de `mapeo-fuentes.md` (`panal_alto_mm`, `marca_vehiculo`…), `datos_sap` JSONB (copia cruda), timestamps |
| `categoria` | Categorías en alcance | `id`, `codigo_sap` (`@IGT_CAT.Code`), `nombre`, `prefijo`, `part_terminology_id_defecto` (PCdb), `activa` |
| `preferencia_usuario` | Filtro global y preferencias | `usuario_id`, `categoria_id` (defecto 25), `linea` (defecto IMPORTADO) |
| `articulo_equivalencia` | Equivalencia Fabricado ↔ Importado (N:M), gestionada en la APP — ADR 0005 | `fabricado_id`, `importado_id`, `origen` (MANUAL/IA/SAP_COD_ANTERIOR), `estado` (SUGERIDA/CONFIRMADA/DESCARTADA), `criterio` JSONB (aplicaciones ACES y atributos PIES comparados), `confirmado_por`, `confirmado_en` |
| `transicion_estado` | Bitácora del workflow | `articulo_id`, `estado_origen`, `estado_destino`, `actor_tipo` (USUARIO/PROCESO), `actor`, `motivo`, `creado_en` |
| `transicion_permitida` | Reglas de la máquina de estados (ADR 0012) | `origen`, `destino`, `actor_tipo`, `rol_requerido`, `requiere_motivo`, `prohibe_mismo_usuario` |
| `tarea_verificacion` | Cola de verificación (ADR 0012) | `articulo_id`, `origen` (NUEVA_FOTO/MUESTREO/CAMBIO_CATALOGO/MANUAL), `detalle` JSONB, `estado` (ABIERTA/CONFORME/CON_HALLAZGO), `asignado_a`, `resuelto_por`, `nota` |
| `vehiculo` | Catálogo híbrido alineado a ACES; lo que importa es el vehículo (región opcional) | `id`, `origen` (AUTOCARE/CUSTOM), `base_vehicle_id`, `sub_model_id`, `vehicle_id` (si aplica), `anio`, `marca`, `modelo`, `submodelo` (copia para mostrar), `vcdb_version` |
| `articulo_aplicacion_region` | Detalle opcional: regiones donde se confirma la aplicación | `articulo_aplicacion_id`, `region_id` (VCdb), `confirmado_por` |
| `articulo_aplicacion` → calificadores | Motor y transmisión de la aplicación | `engine_config_id`, `transmission_id`, `qualifier_id`s (Qdb), `notas` |
| `articulo_aplicacion` | Aplicaciones confirmadas | `articulo_id`, `vehiculo_id`, `origen_sugerencia`, `confirmado_por`, `notas` |
| `diagrama` | Referencia a Diagrams | `id`, `id_externo`, `url_imagen`, `medidas` JSONB |
| `articulo_diagrama` | Diagrama elegido / candidatos | `articulo_id`, `diagrama_id`, `es_seleccionado`, `score` |
| `articulo_parte` | Emparejamiento confirmado con el catálogo maestro (ADR 0011) | `articulo_id`, `parte_id` (Consolidación), `es_principal`, `origen` (BUSQUEDA/HEREDADO_EQUIVALENTE), `confirmado_por`, `confirmado_en` |
| `homologacion_marca` / `homologacion_modelo` | SAP ↔ AutoCare para precargar búsquedas por vehículo | `@IGT_MARCAS.Code` ↔ `make_id`; marca + `@IGT_LINEA` ↔ `model_id`; `confirmado_por` |
| `articulo_atributo` | Atributos PIES validados | `articulo_id`, `paid` (PAdb), `valor`, `valor_num`, `uom_code`, `valid_value_id`, `origen`, `validado_por` |
| `articulo_imagen` | Foto propia (MinIO) o URL de proveedor/Consolidación (ADR 0013) | `articulo_id`, `origen` (PROPIA/PROVEEDOR/CONSOLIDACION), `url` o `minio_objeto`, `orden`, `subida_por`, `subida_en`, `validada`, `validada_por` |
| `usuario` | Login propio (ADR 0015) | `id`, `usuario` (citext único), `nombre`, `correo`, `password_hash` (Argon2id), `debe_cambiar_password`, `intentos_fallidos`, `bloqueado_hasta`, `activo`, `ultimo_acceso_en` |
| `usuario_rol` | Roles por usuario | `usuario_id`, `rol` (OPERADOR/SUPERVISOR/ADMINISTRADOR/FOTOS) |
| `diccionario_campo` (esquema `meta`) | Nombre en el origen de cada columna (ADR 0007) | `esquema`, `tabla`, `columna`, `fuente`, `tabla_origen`, `campo_origen`, `transformacion`, `en_hash`, `descripcion` |
| `hallazgo_calidad_sap` | Datos de SAP que deben corregirse **en SAP** (la APP no escribe en SAP) | `articulo_id`, `campo_sap`, `valor`, `tipo` (MARCA_INVALIDA, VALOR_NO_RECONOCIDO —valor de lista, S/N, unidad o modelo que no se reconoce; queda en `null`—, ANIOS_INVERTIDOS, NOMBRE_INACTIVO_SIN_CONGELAR, MEDIDAS_INVERTIDAS, SUBCATEGORIA_INCONSISTENTE), `detectado_en`, `corregido_en` |
| `auditoria_evento` | Cambios de datos | `entidad`, `entidad_id`, `actor`, `antes` JSONB, `despues` JSONB, `creado_en` |

## Extensiones PostgreSQL
`pg_trgm` (búsqueda difusa de descripciones y números de parte), `unaccent`, `citext`.

## Esquemas sugeridos
- `staging`: lo que escribe el ETL externo (contrato).
- `app`: modelo de trabajo de la APP.
- `audit`: bitácora y auditoría.
- `meta`: diccionario de campos y catálogos de configuración.
- Vehículos fuera de AutoCare: **no** viven aquí, sino en `mercado_externo` (ADR 0014); Nexo guarda solo sus IDs (≥ 1 000 000 000).
