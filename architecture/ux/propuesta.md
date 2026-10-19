# Propuesta de experiencia de usuario — Nexo

> Estado: **propuesta revisada** (2026-10-19, decisiones de la sección 12 resueltas). Define cómo se ve y se usa la APP antes de construir pantallas.
> Se apoya en lo ya decidido: flujo de estados (`context/workflow-estados.md`), filtro global (ADR 0010), doble control (ADR 0012),
> fotos (ADR 0013), código equivalente (ADR 0018), ficha configurable (ADR 0019) y convenciones de API (`architecture/api/convenciones.md`).

## 1. Principios
1. **El operador trabaja, no busca.** El flujo diario es "Siguiente → completar → enviar", sin elegir artículos a mano.
2. **Teclado primero.** Todo lo frecuente tiene atajo; el ratón es opcional.
3. **Sugerido ≠ confirmado, siempre visible.** Lo que viene de SAP, de Consolidación o heredado de un equivalente se ve distinto de lo
   confirmado por una persona, y se acepta con un clic o una tecla.
4. **Explicar por qué algo está bloqueado.** El botón "Enviar a revisión" muestra exactamente qué falta (`fn_requisitos_por_validar`).
5. **El filtro global manda.** Todas las pantallas trabajan sobre Categoría + Línea (por defecto Radiadores · Importados).
6. **Nunca perder trabajo.** Botón **Guardar** explícito con aviso de cambios sin guardar, aviso de conflictos (`409`) y reserva
   visible con su tiempo restante.
7. **Mobile first y modo oscuro.** Todo se diseña primero para celular (Tailwind *mobile first*) y se enriquece en tableta y
   escritorio; claro y oscuro desde el inicio. En escritorio, pantallas densas con números alineados y sin adornos.
8. **Vocabulario del negocio.** Etiquetas como en la ficha de la empresa ("Alto", "Largo", "Ancho tanque"); el nombre PIES se ve como ayuda.

## 2. Usuarios y tareas
| Rol | Tarea más frecuente | Pantalla principal |
|---|---|---|
| Operador (5) | Completar artículos `PENDIENTE`/`RECHAZADO` y enviarlos a revisión | Trabajar (Siguiente) → Espacio de trabajo |
| Supervisor (3) | Validar o rechazar `POR_VALIDAR`; resolver verificaciones | Validar · Verificación |
| Encargado de fotos (1) | Subir fotos propias por artículo | Fotos (celular, tableta o escritorio) |
| Con permiso de ventas | Analizar ventas por artículo | Ventas |
| Administrador | Usuarios, configuración de la ficha, homologación, reaperturas | Administración |
| Todos | Consultar un artículo, ver avance | Búsqueda universal · Panorama |

## 3. Estructura y navegación
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ NEXO  │ Radiadores ▾ · Importados ▾ (1 095) │  🔍 Buscar… (Ctrl+K)            │ ⏱ RAD00188 24:10 │ AP ▾ │
├───────┴─────────────────────────────────────────────────────────────────────────────────────────┤
│ Panorama        │                                                                               │
│ ▶ Trabajar      │                         (contenido de la pantalla)                            │
│ Explorar        │                                                                               │
│ Validar     12  │                                                                               │
│ Verificación 4  │                                                                               │
│ Fabricados      │                                                                               │
│ Catálogo        │                                                                               │
│ Fotos           │                                                                               │
│ Calidad SAP     │                                                                               │
│ Ventas 🔒        │                                                                               │
│ Administración  │                                                                               │
└─────────────────┴───────────────────────────────────────────────────────────────────────────────┘
```
- **Barra superior fija:** filtro global con el conteo de artículos activos; búsqueda universal; **indicador de reserva** (artículo
  y tiempo restante; clic para volver a él); menú de usuario (cambiar contraseña, salir).
- **Navegación lateral por rol:** cada rol ve solo sus entradas. Los contadores (Validar, Verificación) respetan el filtro global.
  En celular, la navegación pasa a un menú inferior con las 4 entradas del rol y un botón "Más".
- **Rutas con estado en la URL** (TanStack Router): filtro, búsqueda, orden y pestaña. Una vista se comparte copiando la URL.

| Ruta | Pantalla | Roles |
|---|---|---|
| `/` | Panorama | Todos |
| `/trabajar` | Toma el siguiente y abre el espacio de trabajo | Operador, Supervisor |
| `/articulos` · `/articulos/:itemCode/:pestaña` | Explorar · Espacio de trabajo | Todos (editar según estado y rol) |
| `/validar` | Bandeja `POR_VALIDAR` | Supervisor, Administrador |
| `/verificacion` | Tareas abiertas (foto nueva, muestreo) | Supervisor, Administrador |
| `/fabricados` | Revisión de código equivalente | Operador, Supervisor |
| `/catalogo` | Catálogo maestro y diagramas (vista inversa) | Todos |
| `/fotos` | Subida y estado de fotos | Fotos, Administrador |
| `/calidad-sap` | Hallazgos para corregir en SAP | Supervisor, Administrador |
| `/ventas` | Análisis de ventas por artículo y tipo | Con permiso `VER_ANALISIS_VENTAS` (ADR 0022) |
| `/admin/*` | Usuarios, ficha de atributos, homologación | Administrador |

## 4. Filtro global
- Dos selectores: **Categoría** (8 en alcance) y **Línea** (Importados / Fabricados). Por defecto Radiadores · Importados.
- Se guarda por usuario (`app.preferencia_usuario`) y viaja en la URL (`?cat=25&linea=IMPORTADO`). La URL gana sobre la preferencia.
- Al cambiarlo, todas las pantallas recargan; si el usuario tiene una reserva de otro tipo, se le avisa y la conserva.
- Muestra el conteo de activos del tipo elegido. Los inactivos (ADR 0008) nunca aparecen.

## 5. Búsqueda universal (Ctrl+K)
Un solo cuadro que entiende lo que se escribe y agrupa resultados:

| Si escribes | Busca en | Ejemplo |
|---|---|---|
| Código de artículo | `item_code`, `codigo_anterior`, `codigo_equivalente` | `RAD00188`, `945RLT` |
| Número de parte | proveedor (`SuppCatNum`), OEM, DPI del catálogo maestro | `ZC-IS011`, `568.770.38`, `2380` |
| Vehículo | marca, modelo y años de SAP y de las aplicaciones confirmadas | `toyota 22r 1990` |
| Medidas | alto × largo × ancho del core, como par sin orden y con tolerancia | `400x518x26`, `400 518` |
| Texto libre | descripción | `radiador hilux plast` |

- Tolerante a mayúsculas, acentos, puntos y guiones (`pg_trgm` + `unaccent`; números normalizados como en `parte_numero.numero_norm`).
- Resultados agrupados (Artículos · Catálogo maestro · Vehículos), con el filtro global aplicado y la opción "buscar en todos los tipos".
- `Enter` abre el primero; flechas para moverse; `Esc` cierra.

## 6. Pantallas

> Las cifras de los bocetos son ilustrativas, salvo las de cobertura de fotos (medidas el 2026-10-19).

### 6.1 Panorama
```
┌ Avance (Radiadores · Importados) ──────────────────────────────────────────────────────────────┐
│ PENDIENTE 1 020 ▕████████████████████▏ POR_VALIDAR 40 ▕█▏ RECHAZADO 5 ▏ VALIDADO 30 ▕▏ SINC. 0 │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Completitud de la ficha ──────┐ ┌ Cobertura ─────────────────┐ ┌ Atención ─────────────────────┐
│ Alto      45 % SAP · 3 % conf.│ │ Con foto        475 (29 %) │ │ Verificaciones abiertas    4  │
│ Largo     45 % …              │ │ Emparejados      30  (3 %) │ │ Hallazgos SAP abiertos   177  │
│ Material  45 % …              │ │ Con aplicación   28  (3 %) │ │ Reservas por vencer        1  │
└───────────────────────────────┘ └────────────────────────────┘ └───────────────────────────────┘
┌ Productividad (7 días) ─────────────────────────┐ ┌ Prioridad por venta ──────────────────────┐
│ Operador   Enviados  Rechazados  Promedio/art.  │ │ Clase A sin validar: 112 (38 % de la venta)│
│                                                 │ │ Top 20 sin validar por participación      │
└─────────────────────────────────────────────────┘ └───────────────────────────────────────────┘
```
- Cada número es un enlace a **Explorar** con ese filtro aplicado.
- La prioridad por venta usa **indicadores relativos**, nunca montos (sección 6.12). Si ClickHouse no está disponible, el bloque no se muestra.

### 6.2 Explorar
Tabla para supervisores y consultas; el operador la usa poco.
- **Columnas configurables** (las elige cada usuario): código, descripción, estado, marca/modelo/años de SAP, medidas, completitud de la
  ficha (barra), foto (sí/no), emparejado, asignado a, último cambio, **clase de venta (A/B/C)** y **tendencia**.
- **Filtros por faceta** en el panel izquierdo, con conteos: estado, completitud (completa / con faltantes), con foto, emparejado,
  con aplicación, con hallazgo SAP, marca, rango de años, asignado a mí.
- **Vistas guardadas** por usuario ("Mis rechazados", "Sin foto con venta alta").
- Paginación en el servidor, filas virtualizadas, orden por cualquier columna.
- `J`/`K` para moverse, `Enter` abre el espacio de trabajo en el mismo artículo; desde ahí `[`/`]` avanzan por la lista filtrada.

### 6.3 Trabajar ("Siguiente")
1. El operador pulsa **Siguiente** (`N`): `POST /bandejas/operador/siguiente` reserva el próximo `PENDIENTE`/`RECHAZADO` del tipo global
   (primero los rechazados, que traen motivo; luego por clase de venta) y abre el espacio de trabajo.
2. Mientras trabaja, el frontend renueva la reserva (latido cada 5 min). Si la reserva vence o la toma otro, se avisa sin perder lo guardado.
3. Al **enviar a revisión**, la reserva se libera y se abre el siguiente automáticamente (opción "seguir trabajando", activa por defecto).
4. **Soltar** (`Esc` dos veces) devuelve el artículo a la bandeja sin cambiar su estado.

### 6.4 Espacio de trabajo del artículo
Pantalla central del sistema. Encabezado fijo + pestañas.
```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [foto] RAD00188 · RADIADOR TOYOTA 22R PLAST M 86/94 MT            PENDIENTE · v7 · ⏱ 24:10      │
│        Importado · Radiadores · Toyota / 22 R · 1986–1994 · MT     Venta: A · top 8 % · ↑ 12 %      │
│        Rechazado: "Falta confirmar años"                                                        │
│        Requisitos: ✓ Tipo de parte  ✗ Aplicación o emparejamiento  ✗ 3 atributos   [Enviar ▸] ⌘↵ │
├──────────┬──────────────┬──────────────────────────┬──────────────┬───────┬───────────────────┤
│ Ficha 8/11│ Aplicaciones 0│ Emparejamiento y diagramas│ Equivalencia │ Fotos │ Historial         │
└──────────┴──────────────┴──────────────────────────┴──────────────┴───────┴───────────────────┘
```
- El encabezado muestra el motivo del último rechazo o reapertura, los **indicadores de venta** (clase, percentil y tendencia, sin
  montos) y la lista de requisitos con enlaces a la pestaña que los resuelve.
- **Pestañas** (decisión 2): cada una con su propio contenido para no saturar la pantalla; el encabezado queda fijo. En celular las
  pestañas se desplazan horizontalmente y el encabezado se compacta a código, estado y requisitos.
- **Enviar a revisión** solo se habilita cuando no falta nada; si falta, el botón dice qué.
- Los datos de SAP son **solo lectura** (SAP no se modifica); lo que el operador corrige vive en Nexo. Si SAP tiene un error, el operador
  puede marcar "Reportar a SAP", que crea un hallazgo de calidad.

#### Pestaña Ficha
```
MEDIDAS                       SAP (sugerido)       Confirmado                      PIES
Alto              *           400 mm   [✓ Enter]   400 mm  ✔ ana · 10:42           Core Height
Largo             *           518 mm   [✓]         [ 518      ] mm                 Core Width
Ancho             *           26 mm    [✓]         [          ] mm                 Core Thickness
Largo tanque      *           545 mm   [✓]         [          ] mm                 Inlet Header Length
CONSTRUCCIÓN
Filas             *           3        [✓]         [          ]
Tipo de panal     *           C        [✓]         [          ]
Tipo flujo        *           Down Flow [✓]        [ Down Flow ▾]
MATERIALES
Material tanque   *           Plastic  [✓]         [ Plastic (Plástico) ▾]
                                    ● 3 cambios sin guardar   [Aceptar todo lo sugerido]  [Guardar  Ctrl+S]
```
- Una fila por atributo **habilitado** del catálogo (ADR 0019), agrupado y ordenado como lo configuró el administrador; `*` = obligatorio.
- Columna **SAP (sugerido)** en gris; `Enter` o clic acepta. "Aceptar todo lo sugerido" confirma de una vez lo que coincide.
- **Campos inteligentes:**
  - medidas con unidad: se acepta `37.5 cm`, `375`, `14.8"`; se guarda en la unidad del atributo y se muestra la conversión;
  - listas PIES con búsqueda en inglés o español, mostrando la **traducción al español** junto al valor PIES (decisión 5;
    requiere una tabla de traducciones de valores, configurable por el administrador);
  - texto libre (tipo de panal) con sugerencias de valores ya usados.
- Si alto y largo de SAP están invertidos respecto al catálogo emparejado, se muestra un aviso con un botón "intercambiar".
- **Botón Guardar** (decisión 1): los cambios de la pestaña se envían juntos (`PUT` con `version`). Aceptar una sugerencia también
  queda pendiente hasta guardar. Si hay cambios sin guardar, se avisa al cambiar de pestaña, de artículo o al cerrar.
  Los requisitos del encabezado se recalculan después de guardar.
- En celular, cada atributo es una tarjeta: etiqueta, valor sugerido con botón de aceptar y el campo debajo.

#### Pestaña Aplicaciones
- **Sugerencias desde SAP:** marca/modelo/años de SAP, homologados con AutoCare (`homologacion_marca/modelo`), proponen los vehículos
  base; el operador marca los correctos y confirma.
- **Selector de vehículo** en cascada con búsqueda en cada paso: Año (o rango) → Marca → Modelo → **Submodelo → Motor**.
  Submodelo y motor son **obligatorios** para confirmar una aplicación de vehículo (decisión 4); las de equipo (maquinaria) no los piden.
  Escribir `toyota pickup 86-94 2.4` llena los pasos de una vez.
- Rango de años como una sola acción ("1986–1994" crea las aplicaciones de cada año); si el motor o submodelo no existe en todos los
  años, se muestra qué años quedan incompletos.
- Si el vehículo no existe en AutoCare: **"Agregar a MercadoExterno"** con el mismo formulario (marca, modelo, años, submodelo, motor,
  región opcional),
  que valida que no exista antes (`fn_registrar_vehiculo`).
- Tabla de aplicaciones agrupada por marca/modelo con años colapsados ("Toyota Pickup 1986–1994 · 22R 2.4L"), región opcional como etiqueta.
- Las aplicaciones heredadas de un equivalente aparecen como sugeridas hasta confirmarlas.

#### Pestaña Emparejamiento y diagramas
```
┌ Candidatos del catálogo maestro ─────────────────────────┐ ┌ Comparación ─────────────────────────────┐
│ Criterios: medidas ±10 mm ▾  OEM ✓  DPI ✓  marca ✓       │ │            RAD00188     Parte 7001       │
│                                                          │ │ Alto        400          400   ✓          │
│ ★ 95  DPI 945 · JJ Radiator · 400×518×26 · Toyota 86-94  │ │ Largo       518          518   ✓          │
│   88  CSF 2380 · 398×520×26 · Toyota 87-95               │ │ Ancho        26           32   ✗ +6       │
│   61  NRF 50123 · 518×400×32 (alto/largo invertidos)     │ │ Filas         3            3   ✓          │
│                                                          │ │ OEM         —      16400-35090            │
│ [Buscar manualmente…]                                    │ │ [diagrama con zoom]   [foto del proveedor]│
└──────────────────────────────────────────────────────────┘ │ [Vincular como principal]  [Vincular]     │
                                                             └──────────────────────────────────────────┘
```
- Candidatos ordenados por **puntaje** (medidas como par sin orden con tolerancia de **±10 mm** por defecto, ajustable en la pantalla;
  OEM, DPI, código de proveedor, marca y años).
  Cada candidato muestra **por qué** coincide.
- Comparación lado a lado con diferencias resaltadas; visor de diagrama e imágenes con zoom (las imágenes son URL, no se copian).
- **Vincular** guarda en `app.articulo_parte` (una principal). Al vincular se ofrece traer los atributos y aplicaciones del catálogo como
  **sugerencias** a las otras pestañas.
- Búsqueda manual con los mismos criterios que la búsqueda universal.

#### Pestaña Equivalencia (solo Fabricados)
- Código equivalente (ADR 0018): campo con sugerencia desde `codigo_anterior`; si es el código de un importado, muestra su tarjeta
  (foto, medidas, aplicaciones) y ofrece **confirmar equivalencia y heredar** (parte y aplicaciones como sugerencias).
- Estado del código: Sin código · Espera foto · Listo para validar · Validado.

#### Pestaña Fotos
- Fotos propias (MinIO) y de proveedor (URL), ordenables, con estado "validada". Subir arrastrando (rol Fotos o Administrador).

#### Pestaña Historial
- Línea de tiempo: transiciones con motivo, cambios de datos de SAP (qué campo cambió, antes/después), ediciones de usuarios
  (`audit.auditoria_evento`) y verificaciones.

### 6.5 Validar (supervisor)
- Bandeja `POR_VALIDAR` con "Siguiente" igual que el operador; excluye lo que el propio supervisor envió (doble control).
- El espacio de trabajo abre en modo **revisión**: cada pestaña marca qué confirmó el operador y qué difiere de SAP o del catálogo.
- Acciones: **Validar** (`V`) o **Rechazar** (`R`), que pide motivo con plantillas frecuentes ("Años no coinciden", "Falta aplicación…")
  y texto libre. Tras decidir, abre el siguiente.

### 6.6 Verificación
- Cola de tareas abiertas (foto nueva, muestreo) con el filtro global. Cada tarea muestra la foto nueva junto a la ficha validada.
- **Conforme** (valida la foto) o **Con hallazgo** (nota obligatoria; el artículo vuelve a `PENDIENTE` con motivo `VERIFICACION`).
- El administrador puede generar un muestreo ("10 artículos validados al azar").

### 6.7 Fabricados
- Lista de fabricados con el estado del código equivalente, filtrable ("Espera foto", "Listo para validar").
- Captura rápida en línea del código equivalente; el supervisor valida los que ya tienen foto.

### 6.8 Catálogo (vista inversa)
- Navegar el catálogo maestro (partes de Consolidación) con los mismos filtros de medidas, OEM y marca.
- Columnas clave: ¿tiene artículo vinculado? ¿cuántos? Filtro **"sin artículo"** para encontrar huecos del catálogo propio.
- Desde una parte se puede buscar el artículo y vincularlo; el resultado es el mismo `articulo_parte` que desde la pestaña.

### 6.9 Fotos (encargado)
- Pantalla pensada también para **celular o tableta**: buscar o escanear el código del artículo, tomar o elegir fotos, subir.
- La APP aplica la convención de MinIO (`imagenes_inventario/{cat}_{NOMBRE}/{ItemCode}/{ItemCode}_{n}.webp`) y crea la tarea de verificación.
- Lista de artículos sin foto, priorizada por venta si está disponible.

### 6.10 Calidad SAP
- Hallazgos abiertos agrupados por tipo (marca inválida, valor no reconocido, años invertidos, inactivo sin congelar) con el valor de SAP.
- Exportar a Excel para quien corrige en SAP; se cierran solos cuando el siguiente lote trae el dato corregido.

### 6.11 Administración
- **Usuarios y roles:** alta con contraseña temporal, bloqueo/desbloqueo, roles.
- **Ficha de atributos** (ADR 0019): por tipo de parte, la lista de PIES con interruptores *habilitado* / *obligatorio*, etiqueta, grupo,
  orden y origen SAP; vista previa de la ficha resultante.
- **Homologación:** marcas y modelos de SAP ↔ AutoCare, con sugerencias por similitud de nombre.
- **Reapertura** de artículos con motivo y **reasignación** de reservas.
- **Traducciones** de valores PIES al español.
- **Permisos especiales** por usuario, como `VER_ANALISIS_VENTAS`.

### 6.12 Ventas (indicadores y análisis)
Datos de apoyo de ClickHouse (volumen de venta), leídos por adaptador. Dos niveles (ADR 0022):

| Nivel | Qué muestra | Quién lo ve | Dónde |
|---|---|---|---|
| **Indicadores** | Clase ABC (A = artículos que suman el 80 % de la venta del tipo), percentil dentro del tipo, participación %, tendencia % frente al periodo anterior (↑ ↓) | Todos | Encabezado del artículo, Explorar, Panorama, orden de "Siguiente" |
| **Análisis** | Series de unidades vendidas, comparación entre artículos y tipos, estacionalidad | Solo con permiso `VER_ANALISIS_VENTAS` | Pantalla **Ventas** (fuera del espacio de trabajo) |

- Nunca se muestran montos ni precios en los indicadores; solo posiciones relativas y porcentajes.
- El periodo de cálculo (por ejemplo, últimos 12 meses) es configurable por el administrador.

## 7. Patrones de interacción
| Patrón | Regla |
|---|---|
| Sugerido vs confirmado | Sugerido: texto gris, ícono de origen (SAP, catálogo, equivalente). Confirmado: texto normal, ✔ con quién y cuándo |
| Guardado | Botón **Guardar** por pestaña (`Ctrl+S`); `PUT` con `version`. Indicador de cambios sin guardar y aviso al salir |
| Conflicto (`409`) | "Otro usuario cambió este artículo": muestra qué cambió y deja elegir recargar o reaplicar lo suyo |
| Reserva | Contador visible; aviso a los 5 min de vencer; al vencer, modo solo lectura hasta volver a tomarla |
| Errores | `problem+json` mostrado en lenguaje del negocio cerca del campo; nunca códigos técnicos sueltos |
| Estados vacíos | Explican qué hacer ("No hay pendientes en Radiadores · Importados. Cambia el filtro o revisa Rechazados") |
| Carga | Esqueletos en tablas y fichas; nada de pantallas en blanco |
| Confirmaciones | Solo para lo irreversible o con motivo (rechazar, reabrir, desvincular la parte principal) |

**Atajos principales:** `Ctrl+K` buscar · `N` siguiente · `1`–`6` pestañas · `Enter` aceptar sugerencia · `Shift+A` aceptar todo ·
`Ctrl+S` guardar · `Ctrl+Enter` enviar a revisión · `V`/`R` validar/rechazar · `J`/`K` y `[`/`]` navegar · `?` ayuda de atajos.

## 8. Diseño visual
- Design system propio sobre shadcn/ui + Tailwind (ADR 0004), con tokens centralizados.
- **Mobile first** (decisión 6): cada componente se diseña primero para celular y se amplía con los breakpoints de Tailwind
  (`sm`, `md`, `lg`, `xl`). Tablas → tarjetas en celular; espacio de trabajo en una columna en celular y con panel lateral en escritorio.
- **Modo claro y oscuro** desde el inicio, con el del sistema por defecto y selector en el menú de usuario. Los colores de estado y
  las diferencias resaltadas se validan en ambos modos con contraste AA.
- **Estados** con color + ícono + texto (nunca solo color): Pendiente (gris), Por validar (azul), Rechazado (rojo), Validado (verde),
  Sincronizado (verde oscuro).
- Números tabulares y alineados a la derecha; unidades en gris.
- Todas las pantallas funcionan en celular, tableta y escritorio; el trabajo intensivo (ficha, emparejamiento) rinde más en tableta y escritorio.

## 9. Calidad
- **Accesibilidad:** WCAG 2.2 AA, foco visible, todo operable con teclado, componentes Radix.
- **Rendimiento:** búsqueda y listas < 300 ms (p95) en el servidor; primera carga de la consola < 2 s en la red interna;
  tablas virtualizadas.
- **Medición:** tiempo por artículo y tasa de rechazo por operador, para mejorar el flujo con datos.

## 10. Lo que necesita la API (para el esqueleto)
| Pantalla | Endpoints principales (`/api/v1`) |
|---|---|
| Barra y filtro | `GET /sesion`, `GET/PUT /preferencias`, `GET /categorias` |
| Búsqueda | `GET /busqueda?q=&cat=&linea=` |
| Panorama | `GET /panorama?cat=&linea=` |
| Explorar | `GET /articulos?filtros…&cursor=` · `GET/PUT /vistas` |
| Trabajar / Validar | `POST /bandejas/{operador|supervisor}/siguiente` · `PUT/DELETE /articulos/{id}/asignacion` |
| Espacio de trabajo | `GET /articulos/{id}` · `GET /articulos/{id}/requisitos` · `POST /articulos/{id}/transiciones` |
| Ficha | `GET /articulos/{id}/ficha` · `PUT /articulos/{id}/ficha` (cambios de la pestaña juntos, con `version`) |
| Aplicaciones | `GET/POST/DELETE /articulos/{id}/aplicaciones` · `GET /vehiculos?anio=&marca=&modelo=` · `POST /vehiculos-externos` |
| Emparejamiento | `GET /articulos/{id}/emparejamiento` (vinculadas + candidatos) · `GET /articulos/{id}/emparejamiento/{parte}` (comparación) · `GET /catalogo/partes` · `POST /articulos/{id}/partes` (+ `/principal`, `/quitar`) |
| Equivalencia | `PUT /articulos/{id}/codigo-equivalente` · `POST /articulos/{id}/equivalencias` · `POST /articulos/{id}/heredar` |
| Fotos | `POST /articulos/{id}/fotos` · `GET /fotos/pendientes` |
| Verificación | `GET /verificaciones` · `POST /verificaciones/{id}/resolucion` · `POST /verificaciones/muestreo` |
| Calidad SAP | `GET /hallazgos-sap` · `GET /hallazgos-sap.xlsx` |
| Ventas | `GET /articulos/{id}/indicadores-venta` · `GET /ventas/analisis` (permiso `VER_ANALISIS_VENTAS`) |
| Administración | `/usuarios`, `/admin/atributos`, `/admin/homologacion` |

## 11. Fuera de esta versión
Edición masiva de atributos, comparación entre dos artículos cualesquiera, notificaciones por correo, modo sin conexión,
traducción completa de valores PIES.

## 12. Decisiones (resueltas 2026-10-19)
| # | Tema | Decisión |
|---|---|---|
| 1 | Guardado | Botón **Guardar** por pestaña, con aviso de cambios sin guardar |
| 2 | Organización del espacio de trabajo | **Pestañas**, para no saturar una sola página |
| 3 | Tolerancia de medidas contra el catálogo | **±10 mm** por defecto, ajustable en la pantalla |
| 4 | Submodelo y motor en aplicaciones de vehículo | **Obligatorios** para confirmar (pendiente de llevar a la base: `fn_requisitos_por_validar` y validación de `articulo_aplicacion`) |
| 5 | Valores PIES | Se muestra la **traducción al español** junto al valor (tabla de traducciones configurable) |
| 6 | Dispositivos | Celular, tableta y escritorio: **mobile first** con Tailwind y **modo oscuro** |
| 7 | Ventas | **Indicadores relativos** (clase ABC, percentil, participación, tendencia) para todos; **análisis** en pantalla aparte con permiso (ADR 0022) |
