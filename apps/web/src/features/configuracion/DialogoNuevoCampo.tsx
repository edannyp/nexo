import { useCrearCampoPropio, type AtributoConfig, type GrupoAtributo, type TipoPropio } from '@nexo/api-client';
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

/** Crear un campo propio de Nexo, que AutoCare no tiene (ADR 0029). Queda habilitado al final de la ficha. */
export function DialogoNuevoCampo({
  pt,
  abierto,
  alCerrar,
  alCrear,
}: {
  pt: number;
  abierto: boolean;
  alCerrar: () => void;
  alCrear: (a: AtributoConfig) => void;
}) {
  const [nombre, setNombre] = useState('');
  const [tipo, setTipo] = useState<TipoPropio>('NUMERO');
  const [medida, setMedida] = useState(true);
  const [opciones, setOpciones] = useState('');
  const [grupo, setGrupo] = useState<GrupoAtributo>('OTROS');
  const [obligatorio, setObligatorio] = useState(false);
  const crear = useCrearCampoPropio();

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    crear.mutate(
      {
        partTerminologyId: pt,
        data: {
          nombre: nombre.trim(),
          tipo,
          grupo,
          obligatorio,
          medida: tipo === 'NUMERO' && medida,
          opciones:
            tipo === 'LISTA'
              ? opciones
                  .split('\n')
                  .map((o) => o.trim())
                  .filter(Boolean)
              : [],
        },
      },
      { onSuccess: alCrear },
    );
  };

  return (
    <Dialogo abierto={abierto} alCerrar={alCerrar} titulo="Nuevo campo propio">
      <form onSubmit={enviar} className="space-y-4">
        <p className="text-sm text-suave">
          Para datos que AutoCare no tiene. Por ahora solo se usan en Nexo: no se envían a otros sistemas.
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
          <label className="flex h-10 items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="size-4"
              checked={obligatorio}
              onChange={(e) => setObligatorio(e.target.checked)}
            />
            Obligatorio para enviar a revisión
          </label>
        </div>
        {crear.error && <Aviso tono="error" titulo={textoError(crear.error) ?? ''} />}
        <Boton type="submit" cargando={crear.isPending} className="w-full">
          Crear campo
        </Boton>
      </form>
    </Dialogo>
  );
}
