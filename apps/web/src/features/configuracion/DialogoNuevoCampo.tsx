import {
  useCrearCampoPropio,
  useSolicitarCampo,
  type AtributoConfig,
  type Ficha,
  type GrupoAtributo,
  type TipoPropio,
} from '@nexo/api-client';
import { useState, type FormEvent } from 'react';

import { cn } from '@/shared/cn';
import { Aviso, Boton, Campo, Dialogo } from '@/shared/ui';

import { GRUPOS, textoError } from './comun';

const TIPOS: { valor: TipoPropio; nombre: string; ayuda: string }[] = [
  { valor: 'NUMERO', nombre: 'Número', ayuda: 'Una cantidad; si es una medida se captura en mm, cm o pulgadas.' },
  { valor: 'LISTA', nombre: 'Lista de opciones', ayuda: 'Se elige una de las opciones que definas.' },
  { valor: 'TEXTO', nombre: 'Texto libre', ayuda: 'Un texto corto.' },
  { valor: 'SI_NO', nombre: 'Sí / No', ayuda: 'Se responde Sí o No.' },
];

/**
 * Un campo propio de Nexo, que AutoCare no tiene (ADR 0029). Con `pt` lo crea quien configura la ficha y queda oficial; con
 * `itemCode` lo solicita quien trabaja el artículo y queda propuesto hasta que se apruebe (ADR 0030).
 */
export function DialogoNuevoCampo({
  pt,
  itemCode,
  abierto,
  alCerrar,
  alCrear,
  alSolicitar,
}: {
  pt?: number;
  itemCode?: string;
  abierto: boolean;
  alCerrar: () => void;
  alCrear?: (a: AtributoConfig) => void;
  alSolicitar?: (f: Ficha) => void;
}) {
  const solicitando = !!itemCode;
  const [nombre, setNombre] = useState('');
  const [tipo, setTipo] = useState<TipoPropio>('NUMERO');
  const [medida, setMedida] = useState(true);
  const [opciones, setOpciones] = useState('');
  const [grupo, setGrupo] = useState<GrupoAtributo>('OTROS');
  const [obligatorio, setObligatorio] = useState(false);
  const [motivo, setMotivo] = useState('');
  const crear = useCrearCampoPropio();
  const solicitar = useSolicitarCampo();
  const accion = solicitando ? solicitar : crear;

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    const campo = {
      nombre: nombre.trim(),
      tipo,
      grupo,
      medida: tipo === 'NUMERO' && medida,
      opciones:
        tipo === 'LISTA'
          ? opciones
              .split('\n')
              .map((o) => o.trim())
              .filter(Boolean)
          : [],
    };
    if (itemCode) solicitar.mutate({ itemCode, data: { ...campo, motivo: motivo.trim() } }, { onSuccess: alSolicitar });
    else if (pt) crear.mutate({ partTerminologyId: pt, data: { ...campo, obligatorio } }, { onSuccess: alCrear });
  };

  return (
    <Dialogo abierto={abierto} alCerrar={alCerrar} titulo={solicitando ? 'Solicitar un campo' : 'Nuevo campo propio'}>
      <form onSubmit={enviar} className="space-y-4">
        <p className="text-sm text-suave">
          {solicitando
            ? 'Para un dato que falta en la ficha. Aparece enseguida como «Propuesto» en todos los artículos de este tipo; se vuelve oficial cuando lo aprueba quien configura la ficha.'
            : 'Para datos que AutoCare no tiene. Por ahora solo se usan en Nexo: no se envían a otros sistemas.'}
        </p>
        <Campo
          etiqueta="Nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          required
          minLength={2}
          maxLength={60}
          autoFocus
          placeholder="Ej.: Espesor de aleta"
        />
        <fieldset className="space-y-1.5">
          <legend className="text-sm font-medium">Tipo</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {TIPOS.map((t) => (
              <label
                key={t.valor}
                className={cn(
                  'cursor-pointer rounded-md border p-2 text-sm',
                  tipo === t.valor ? 'border-primario bg-primario/5' : 'border-borde',
                )}
              >
                <input
                  type="radio"
                  name="tipo"
                  className="sr-only"
                  checked={tipo === t.valor}
                  onChange={() => setTipo(t.valor)}
                />
                <span className="font-medium">{t.nombre}</span>
                <span className="block text-xs text-suave">{t.ayuda}</span>
              </label>
            ))}
          </div>
        </fieldset>
        {tipo === 'NUMERO' && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="size-4" checked={medida} onChange={(e) => setMedida(e.target.checked)} />
            Es una medida (se guarda en mm)
          </label>
        )}
        {tipo === 'LISTA' && (
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Opciones (una por línea)</span>
            <textarea
              value={opciones}
              onChange={(e) => setOpciones(e.target.value)}
              rows={4}
              required
              placeholder={'Recta\nOndulada'}
              className="w-full rounded-md border border-borde bg-superficie p-2 text-base sm:text-sm"
            />
          </label>
        )}
        <div className="flex flex-wrap items-end gap-4">
          <label className="space-y-1.5">
            <span className="block text-sm font-medium">Grupo</span>
            <select
              value={grupo}
              onChange={(e) => setGrupo(e.target.value as GrupoAtributo)}
              className="h-10 rounded-md border border-borde bg-superficie px-2 text-base sm:text-sm"
            >
              {GRUPOS.map((g) => (
                <option key={g.valor} value={g.valor}>
                  {g.nombre}
                </option>
              ))}
            </select>
          </label>
          {!solicitando && (
            <label className="flex h-10 items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4"
                checked={obligatorio}
                onChange={(e) => setObligatorio(e.target.checked)}
              />
              Obligatorio para enviar a revisión
            </label>
          )}
        </div>
        {solicitando && (
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">¿Para qué se necesita?</span>
            <textarea
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              rows={3}
              required
              minLength={3}
              maxLength={500}
              placeholder="Lo lee quien aprueba el campo"
              className="w-full rounded-md border border-borde bg-superficie p-2 text-base sm:text-sm"
            />
          </label>
        )}
        {accion.error && <Aviso tono="error" titulo={textoError(accion.error) ?? ''} />}
        <Boton type="submit" cargando={accion.isPending} className="w-full">
          {solicitando ? 'Solicitar campo' : 'Crear campo'}
        </Boton>
      </form>
    </Dialogo>
  );
}
