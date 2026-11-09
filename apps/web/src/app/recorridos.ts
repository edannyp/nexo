/**
 * Recorridos guiados de cada pantalla (botón «?» de la barra superior). Cada paso resalta un elemento (`donde`, selector CSS);
 * si no está visible (celular, rol, estado), la tarjeta sale al centro. Para cambiar un texto basta editarlo aquí.
 */
import type { DefinicionRecorrido } from '@/shared/recorrido';

const TIPO = '[aria-label="Tipo de artículo"]';

export const RECORRIDOS: Record<string, DefinicionRecorrido> = {
  panorama: {
    titulo: 'Panorama',
    pasos: [
      {
        titulo: 'Bienvenido a Nexo',
        texto:
          'Nexo es el puente entre SAP y el catálogo estandarizado (AutoCare): aquí se revisa, completa y valida cada artículo antes de devolverlo a SAP. Este recorrido te muestra lo principal.',
      },
      {
        donde: TIPO,
        titulo: 'Tipo de artículo',
        texto:
          'Todo Nexo trabaja sobre un tipo a la vez: la categoría (Radiadores, Condensadores…) y la línea (Importados o Fabricados). Cambiarlo aquí cambia lo que ves en todas las pantallas.',
      },
      {
        donde: 'nav[aria-label="Secciones"]',
        titulo: 'Secciones',
        texto:
          'Trabajar: tomar el siguiente artículo pendiente. Explorar: buscar y filtrar todos. Validar: revisar lo que enviaron (supervisores). El resto son herramientas de apoyo.',
      },
      {
        donde: '[data-recorrido="panorama-cifras"]',
        titulo: 'Cómo vamos',
        texto:
          'Artículos activos del tipo elegido, cuántos están validados, cuántos tienen la ficha completa y cuántos tienen foto propia.',
      },
      {
        donde: '[data-recorrido="panorama-graficos"]',
        titulo: 'Avance y atención',
        texto:
          'El avance por estado, lo que necesita atención (rechazados, hallazgos de SAP), la completitud de la ficha, la cobertura de fotos y emparejamiento, las ventas y la productividad del equipo.',
      },
      {
        donde: '[data-recorrido="busqueda"]',
        titulo: 'Buscar un artículo',
        texto:
          'Ctrl+K abre la búsqueda desde cualquier pantalla: por código, número de parte, código anterior o descripción.',
      },
      {
        titulo: 'Ayuda en cada pantalla',
        texto:
          'El botón «?» de arriba abre el recorrido de la pantalla en la que estés. Puedes repetirlo cuando quieras.',
      },
    ],
  },

  trabajar: {
    titulo: 'Trabajar',
    pasos: [
      {
        titulo: 'Tu bandeja de trabajo',
        texto:
          'Aquí están los artículos Pendientes y Rechazados del tipo elegido. Nexo te da el siguiente en orden de importancia: primero los rechazados, después los que más venden.',
      },
      {
        donde: '[data-recorrido="bandeja-disponibles"]',
        titulo: 'Disponibles',
        texto: 'Cuántos artículos hay por trabajar en esta bandeja, sin contar los que otra persona tiene tomados.',
      },
      {
        donde: '[data-recorrido="bandeja-siguiente"]',
        titulo: 'Siguiente',
        texto:
          'Toma el siguiente artículo y lo reserva para ti por 30 minutos (se renueva solo mientras trabajas). Atajo: tecla N.',
      },
      {
        donde: '[data-recorrido="bandeja-mias"]',
        titulo: 'Reservados por ti',
        texto:
          'Los que ya tomaste y no terminaste. Ábrelos para seguir, o suéltalos desde el artículo para que los tome otra persona.',
      },
      {
        titulo: 'El ciclo de un artículo',
        texto:
          'Pendiente → completas ficha, vehículo principal y emparejamiento → Enviar a revisión → un supervisor lo valida o lo rechaza con un motivo → Validado → se actualiza en SAP.',
      },
    ],
  },

  validar: {
    titulo: 'Validar',
    pasos: [
      {
        titulo: 'Revisar lo enviado',
        texto:
          'Aquí están los artículos Por validar. Es el doble control: nunca te tocará uno que tú mismo enviaste a revisión.',
      },
      {
        donde: '[data-recorrido="bandeja-siguiente"]',
        titulo: 'Siguiente',
        texto: 'Toma el siguiente artículo por validar. Atajo: tecla N.',
      },
      {
        titulo: 'Validar o rechazar',
        texto:
          'En el artículo revisa el resumen: descripción, vehículo principal, medidas y fotos. Si todo está bien, «Validar»; si no, «Rechazar» con un motivo: vuelve al operador.',
      },
    ],
  },

  explorar: {
    titulo: 'Explorar',
    pasos: [
      {
        titulo: 'Todos los artículos',
        texto:
          'La lista completa del tipo elegido, con filtros, orden y columnas a tu gusto. Los filtros quedan en la dirección: puedes compartirla.',
      },
      {
        donde: '[data-recorrido="explorar-busqueda"]',
        titulo: 'Buscar',
        texto: 'Por código, número de parte, código anterior o descripción.',
      },
      {
        donde: 'aside[aria-label="Filtros"], [data-recorrido="explorar-filtros-boton"]',
        titulo: 'Filtros',
        texto:
          'Por estado, ficha completa, foto, emparejado, hallazgos de SAP, vehículo principal (o su marca y modelo), clase de venta y reserva.',
      },
      {
        donde: 'select[aria-label="Ordenar por"]',
        titulo: 'Orden',
        texto: 'Por venta (lo que más importa primero), código, estado, año, lo más reciente o lo que más le falta.',
      },
      {
        donde: '[popovertarget="menu-vistas"]',
        titulo: 'Vistas guardadas',
        texto: 'Guarda la combinación actual de filtros y orden con un nombre, para volver a ella con un clic.',
      },
      {
        donde: 'table',
        titulo: 'La tabla',
        texto: 'Clic en una fila para abrir el artículo. Con el teclado: J y K para moverte, Enter para abrir.',
      },
    ],
  },

  'articulo-resumen': {
    titulo: 'Artículo · Resumen',
    pasos: [
      {
        titulo: 'Qué es el artículo',
        texto:
          'El resumen muestra el artículo de un vistazo, sin editar nada. Para cambiar algo se entra a «Trabajar».',
      },
      {
        donde: 'section[aria-label="Fotos"]',
        titulo: 'Fotos',
        texto: 'Las fotos propias primero y luego las del catálogo maestro. Usa las flechas para pasar de una a otra.',
      },
      {
        donde: '[data-recorrido="resumen-descripcion"]',
        titulo: 'Descripción',
        texto:
          'Arriba, la descripción que arma Nexo con el patrón de SAP (tipo, marca, modelo, años, motor, transmisión). Abajo, la de SAP tal como está, para comparar.',
      },
      {
        donde: '[data-recorrido="resumen-principal"]',
        titulo: 'Vehículo principal',
        texto:
          'El vehículo ACES (AutoCare) que define al artículo. Es obligatorio para enviar a revisión y de él sale la descripción de Nexo.',
      },
      {
        donde: '[data-recorrido="resumen-atributos"]',
        titulo: 'Medidas y atributos',
        texto:
          'Las medidas del panal y los atributos ya confirmados. Lo que dice «(SAP)» todavía no lo confirmó nadie.',
      },
      {
        donde: '[data-recorrido="resumen-falta"]',
        titulo: 'Lo que falta',
        texto: 'Los requisitos pendientes para enviar a revisión. Cada uno te lleva a la pestaña donde se completa.',
      },
      {
        donde: '[data-recorrido="resumen-sap"]',
        titulo: 'Datos de SAP e historial',
        texto: 'Los datos tal como vienen de SAP (solo lectura) y, debajo, todo lo que le ha pasado al artículo.',
      },
      {
        donde: '[data-recorrido="articulo-trabajar"]',
        titulo: 'Trabajar',
        texto: 'Lo reserva para ti y abre las pestañas de trabajo: Ficha, Aplicaciones y Emparejamiento.',
      },
    ],
  },

  'articulo-ficha': {
    titulo: 'Artículo · Ficha',
    pasos: [
      {
        donde: 'section[aria-label="Lo que define al artículo"]',
        titulo: 'Siempre a la vista',
        texto:
          'Mientras trabajas, arriba quedan la foto, la descripción sugerida (con «Ajustar» si necesitas cambiarla), la de SAP y el vehículo principal.',
      },
      {
        donde: '[aria-label="Secciones de trabajo"]',
        titulo: 'Pestañas',
        texto:
          'Ficha (atributos), Aplicaciones (vehículos) y Emparejamiento (catálogo maestro). Quedan fijas al bajar.',
      },
      {
        donde: '[data-recorrido="ficha-leyenda"]',
        titulo: 'Qué se edita',
        texto:
          'Los campos con lápiz se editan en Nexo. La columna SAP, con candado, es solo lectura: si está mal, se corrige en SAP.',
      },
      {
        donde: '[data-recorrido="ficha-sugeridos"]',
        titulo: 'Sugerencias',
        texto:
          'Nexo precarga lo que dice SAP como sugerencia. Revísalo y acéptalo (uno por uno o todo junto): solo cuenta lo confirmado.',
      },
      {
        donde: '[role="tabpanel"] section',
        titulo: 'Atributos PIES',
        texto:
          'Agrupados (medidas, construcción, materiales…). El asterisco marca los obligatorios. Las medidas aceptan mm, cm o pulgadas y se guardan en mm.',
      },
      {
        titulo: 'Guardar',
        texto:
          'Al cambiar algo aparece abajo la barra de guardado. Guarda con el botón o con Ctrl+S; si sales sin guardar, Nexo te avisa.',
      },
      {
        donde: '[data-recorrido="articulo-acciones"]',
        titulo: 'Reserva y envío',
        texto:
          'El reloj muestra cuánto queda de tu reserva (se renueva sola). Cuando no falte nada, «Enviar a revisión» (Ctrl+Enter). «Soltar» lo libera para otra persona.',
      },
    ],
  },

  'articulo-aplicaciones': {
    titulo: 'Artículo · Aplicaciones',
    pasos: [
      {
        titulo: 'En qué vehículos va',
        texto:
          'Las aplicaciones son los vehículos ACES (AutoCare o MercadoExterno) donde va la pieza, por año, con submodelo y motor. Una de ellas es el vehículo principal.',
      },
      {
        donde: '[data-recorrido="aplicaciones-sap"]',
        titulo: 'Lo que dice SAP',
        texto: 'Marca, modelo y años de SAP. «Buscar en el catálogo» abre el selector ya filtrado con esos datos.',
      },
      {
        donde: 'section[aria-label="Agregar aplicaciones"]',
        titulo: 'El selector',
        texto:
          'Elige años, marca y modelo; marca uno o más submodelos con su motor y pulsa «Agregar». Deja marcada «Es el vehículo principal» si es el que define al artículo.',
      },
      {
        donde: '[data-recorrido="aplicaciones-lista"]',
        titulo: 'Aplicaciones del artículo',
        texto:
          'Agrupadas por vehículo. ★ marca el principal; «Principal» en otro grupo lo cambia. Las sugeridas (de un equivalente o del catálogo maestro) se confirman aparte.',
      },
      {
        titulo: '¿No está el vehículo?',
        texto:
          'Si no existe en AutoCare, regístralo en MercadoExterno desde el enlace del selector, con una fuente que lo demuestre. Queda disponible para todos.',
      },
    ],
  },

  'articulo-emparejamiento': {
    titulo: 'Artículo · Emparejamiento',
    pasos: [
      {
        titulo: 'Emparejar con el catálogo maestro',
        texto:
          'El catálogo maestro une los diagramas propios y los proveedores (JJ Radiator…). Emparejar es decir a qué pieza del catálogo corresponde este artículo.',
      },
      {
        donde: 'section[aria-label="Candidatos"]',
        titulo: 'Candidatos',
        texto:
          'Nexo propone piezas por medidas del panal (alto y largo en cualquier orden), números y vehículos en común, con un puntaje y el porqué.',
      },
      {
        donde: 'select[aria-label="Tolerancia de medidas"]',
        titulo: 'Tolerancia',
        texto: 'Cuántos mm de diferencia se aceptan en las medidas. Súbela si no aparecen candidatos.',
      },
      {
        donde: 'input[aria-label="Buscar manualmente en el catálogo"]',
        titulo: 'Búsqueda manual',
        texto: 'Por medidas (400x518x26), por número (OEM, DPI, proveedor) o por palabras de la descripción.',
      },
      {
        donde: 'section[aria-label="Comparación"]',
        titulo: 'Comparación',
        texto: 'El candidato elegido frente al artículo, atributo por atributo, con las diferencias marcadas.',
      },
      {
        donde: 'button[title^="Fotos del artículo"]',
        titulo: 'Comparar fotos',
        texto:
          'Abre las fotos del artículo y las del candidato lado a lado, en grande. Pasa de candidato con las flechas y vincula desde ahí.',
      },
      {
        titulo: 'Vincular',
        texto:
          '«Vincular como principal» para la pieza que corresponde; «Vincular» para otras equivalentes. Puedes traer sus atributos y aplicaciones como sugerencias para revisar.',
      },
    ],
  },

  'articulo-equivalencia': {
    titulo: 'Artículo · Equivalencia',
    pasos: [
      {
        titulo: 'Fabricado e importado',
        texto:
          'Un fabricado puede tener un importado equivalente (la misma pieza comprada hecha). Al confirmarlo, el fabricado hereda su emparejamiento y aplicaciones como sugerencias.',
      },
      {
        donde: '[aria-label="Estado del código equivalente"]',
        titulo: 'Código equivalente',
        texto:
          'El código que identifica al fabricado frente al importado pasa por: capturado → validado con foto → confirmado.',
      },
      {
        donde: 'input[aria-label="Código equivalente"]',
        titulo: 'Capturarlo',
        texto: 'Escribe el código equivalente. Después se valida con la foto del artículo antes de confirmarlo.',
      },
    ],
  },

  verificacion: {
    titulo: 'Verificación',
    pasos: [
      {
        titulo: 'Revisar lo ya validado',
        texto:
          'Tareas para volver a mirar artículos ya validados: una foto nueva, un cambio en el catálogo maestro o un muestreo al azar.',
      },
      {
        donde: '[aria-label="Origen"]',
        titulo: 'Por origen',
        texto: 'Filtra las tareas por lo que las creó.',
      },
      {
        titulo: 'Resolver',
        texto:
          '«Conforme» si todo sigue bien. «Hallazgo» con una nota si algo está mal: el artículo vuelve a Pendiente para corregirlo.',
      },
      {
        titulo: 'Nueva y muestreo',
        texto:
          '«Nueva» crea una verificación a mano. Los administradores pueden pedir un muestreo de 10 artículos validados al azar.',
      },
    ],
  },

  fabricados: {
    titulo: 'Fabricados',
    pasos: [
      {
        titulo: 'Códigos equivalentes',
        texto: 'Los artículos fabricados y el estado de su código equivalente con el importado.',
      },
      {
        donde: '[aria-label="Estado del código"]',
        titulo: 'Por estado',
        texto: 'Filtra por estado del código: sin código, capturado, validado con foto o confirmado.',
      },
      {
        donde: 'input[aria-label="Buscar fabricado"]',
        titulo: 'Buscar',
        texto: 'Por código, descripción o código anterior. Desde cada fila se captura o valida el código.',
      },
    ],
  },

  catalogo: {
    titulo: 'Catálogo maestro',
    pasos: [
      {
        titulo: 'El catálogo, al revés',
        texto:
          'Aquí se recorren las piezas del catálogo maestro y se ve qué artículos de Nexo ya están emparejados con cada una.',
      },
      {
        donde: 'input[aria-label="Buscar en el catálogo"]',
        titulo: 'Buscar',
        texto: 'Por medidas, número o descripción, dentro del tipo de artículo elegido.',
      },
      {
        donde: 'section[aria-label="Partes"]',
        titulo: 'Piezas',
        texto: 'Las piezas del catálogo con sus medidas y cuántas fuentes las respaldan.',
      },
      {
        donde: 'section[aria-label="Detalle de la parte"]',
        titulo: 'Detalle',
        texto: 'Números, atributos, aplicaciones, imágenes y los artículos de Nexo vinculados a la pieza elegida.',
      },
    ],
  },

  fotos: {
    titulo: 'Fotos',
    pasos: [
      {
        titulo: 'Fotos propias',
        texto:
          'Para el encargado de fotos: subir y ordenar las fotos propias de cada artículo. Se guardan en MinIO con el nombre correcto.',
      },
      {
        donde: 'input[aria-label="Código del artículo"]',
        titulo: 'Abrir un artículo',
        texto: 'Escribe el código y pulsa «Abrir» para ver sus fotos, subir nuevas o cambiar el orden.',
      },
      {
        titulo: 'Verificación',
        texto:
          'Si el artículo ya estaba validado, cada foto nueva crea una verificación para que un supervisor la revise.',
      },
    ],
  },

  'calidad-sap': {
    titulo: 'Calidad SAP',
    pasos: [
      {
        titulo: 'Lo que hay que corregir en SAP',
        texto:
          'Datos de SAP que no cumplen las reglas: marcas que no son marcas, años invertidos, valores no reconocidos, vehículo distinto del principal… Nexo no escribe en SAP: se corrigen allá.',
      },
      {
        donde: '[aria-label="Filtrar por tipo de hallazgo"]',
        titulo: 'Por tipo',
        texto:
          'Filtra los hallazgos por tipo. Cada uno se cierra solo cuando SAP lo corrige y el ETL trae el dato nuevo.',
      },
      {
        titulo: 'Exportar',
        texto: 'Descarga la lista para pasarla al responsable de SAP.',
      },
    ],
  },

  ventas: {
    titulo: 'Ventas',
    pasos: [
      {
        titulo: 'Análisis de ventas',
        texto:
          'Las unidades vendidas y la clase de venta (A, B, C) de la clasificación de la empresa, por tipo de artículo.',
      },
      {
        donde: '[aria-label="Filtrar por clase"]',
        titulo: 'Por clase',
        texto: 'A son los que más venden. Nexo usa la clase para ordenar la bandeja de trabajo.',
      },
    ],
  },

  usuarios: {
    titulo: 'Usuarios',
    pasos: [
      {
        titulo: 'Quién usa Nexo',
        texto: 'Los usuarios y sus roles. Solo los administradores entran aquí.',
      },
      {
        titulo: 'Roles',
        texto:
          'Operador: completa artículos. Supervisor: además valida (nunca lo que él envió). Fotos: sube fotos. Administrador: usuarios y configuración. Un usuario puede tener varios.',
      },
      {
        titulo: 'Alta y contraseñas',
        texto: '«Nuevo» crea un usuario con una contraseña temporal que debe cambiar al entrar. No hay autorregistro.',
      },
    ],
  },
};
