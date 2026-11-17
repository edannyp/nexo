import { ProblemaError, type AtributoConfig, type ConversionSap, type GrupoAtributo } from '@nexo/api-client';

export const GRUPOS: { valor: GrupoAtributo; nombre: string }[] = [
  { valor: 'MEDIDAS', nombre: 'Medidas' },
  { valor: 'CONSTRUCCION', nombre: 'Construcción' },
  { valor: 'MATERIALES', nombre: 'Materiales' },
  { valor: 'CONEXIONES', nombre: 'Conexiones' },
  { valor: 'INCLUYE', nombre: 'Incluye' },
  { valor: 'OTROS', nombre: 'Otros' },
];
export const nombreGrupo = (g: string) => GRUPOS.find((x) => x.valor === g)?.nombre ?? g;

export const TIPOS: Record<string, string> = {
  NUMERO: 'Número',
  LISTA: 'Lista',
  TEXTO: 'Texto',
  SI_NO: 'Sí / No',
};
export const nombreTipo = (a: Pick<AtributoConfig, 'tipo' | 'requiere_uom'>) =>
  a.tipo === 'NUMERO' && a.requiere_uom ? 'Medida (mm)' : (TIPOS[a.tipo] ?? a.tipo);

/** Cómo se convierte el dato de SAP, y para qué tipo de campo sirve cada conversión (la API vuelve a validarlo). */
export const CONVERSIONES: { valor: ConversionSap; nombre: string; tipo: string }[] = [
  { valor: 'NUMERO', nombre: 'Número tal cual', tipo: 'NUMERO' },
  { valor: 'NUMERO_EN_TEXTO', nombre: 'Número dentro de un texto («35 mm»)', tipo: 'NUMERO' },
  { valor: 'PARTE_DE_MEDIDA', nombre: 'Parte de una medida («545*54.5»)', tipo: 'NUMERO' },
  { valor: 'LISTA', nombre: 'Homologar a una opción', tipo: 'LISTA' },
  { valor: 'TEXTO', nombre: 'Texto tal cual', tipo: 'TEXTO' },
  { valor: 'SI_NO', nombre: 'Sí / No (S, N, Y, 1, 0…)', tipo: 'SI_NO' },
];

export const etiquetaDe = (a: Pick<AtributoConfig, 'etiqueta' | 'nombre'>) => a.etiqueta ?? a.nombre;

/** Mensaje legible de un error de la API (título y detalle problem+json). */
export function textoError(e: unknown): string | undefined {
  if (!e) return undefined;
  if (e instanceof ProblemaError) return [e.problema.title, e.problema.detail].filter(Boolean).join(': ');
  return 'No se pudo guardar. Intenta de nuevo.';
}
