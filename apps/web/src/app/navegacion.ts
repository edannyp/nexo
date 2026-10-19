import {
  BookOpen,
  Camera,
  CheckCheck,
  Factory,
  LayoutDashboard,
  Play,
  Settings,
  ShieldCheck,
  Table2,
  TrendingUp,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react';

/** Entradas del menú (architecture/ux/propuesta.md §3). `paso` = paso de la ruta de construcción que la entrega. */
export interface Seccion {
  ruta: string;
  etiqueta: string;
  icono: LucideIcon;
  descripcion: string;
  paso: number;
  movil?: boolean; // visible en el menú inferior del celular
  restringida?: boolean; // requiere un permiso especial
}

export const SECCIONES: Seccion[] = [
  {
    ruta: '/',
    etiqueta: 'Panorama',
    icono: LayoutDashboard,
    paso: 4,
    movil: true,
    descripcion: 'Avance por estado, completitud de la ficha, cobertura y pendientes.',
  },
  {
    ruta: '/trabajar',
    etiqueta: 'Trabajar',
    icono: Play,
    paso: 5,
    movil: true,
    descripcion: 'Toma el siguiente artículo de tu bandeja y ábrelo en el espacio de trabajo.',
  },
  {
    ruta: '/articulos',
    etiqueta: 'Explorar',
    icono: Table2,
    paso: 5,
    movil: true,
    descripcion: 'Tabla de artículos con filtros, columnas configurables y vistas guardadas.',
  },
  {
    ruta: '/validar',
    etiqueta: 'Validar',
    icono: CheckCheck,
    paso: 5,
    movil: true,
    descripcion: 'Bandeja del supervisor: validar o rechazar lo que enviaron los operadores.',
  },
  {
    ruta: '/verificacion',
    etiqueta: 'Verificación',
    icono: ShieldCheck,
    paso: 8,
    descripcion: 'Tareas abiertas por fotos nuevas y muestreo de control de calidad.',
  },
  {
    ruta: '/fabricados',
    etiqueta: 'Fabricados',
    icono: Factory,
    paso: 6,
    descripcion: 'Código equivalente de los fabricados y su validación con foto.',
  },
  {
    ruta: '/catalogo',
    etiqueta: 'Catálogo',
    icono: BookOpen,
    paso: 7,
    descripcion: 'Catálogo maestro y diagramas: qué partes tienen artículo y cuáles no.',
  },
  {
    ruta: '/fotos',
    etiqueta: 'Fotos',
    icono: Camera,
    paso: 8,
    descripcion: 'Subir fotos propias desde el celular, la tableta o el escritorio.',
  },
  {
    ruta: '/calidad-sap',
    etiqueta: 'Calidad SAP',
    icono: TriangleAlert,
    paso: 4,
    descripcion: 'Hallazgos de datos que deben corregirse en SAP.',
  },
  {
    ruta: '/ventas',
    etiqueta: 'Ventas',
    icono: TrendingUp,
    paso: 4,
    restringida: true,
    descripcion: 'Análisis de ventas por artículo y tipo (requiere permiso).',
  },
  {
    ruta: '/admin',
    etiqueta: 'Administración',
    icono: Settings,
    paso: 3,
    descripcion: 'Usuarios, ficha de atributos, traducciones y homologación.',
  },
];
