import { useBuscar, type Resultado } from '@nexo/api-client';
import { useNavigate } from '@tanstack/react-router';
import { Ruler, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { EtiquetaEstado } from '@/shared/estados';
import { numero } from '@/shared/formato';

import { useFiltro } from './contexto-filtro';

const COINCIDE: Record<Resultado['coincide'], string> = {
  codigo: 'Código',
  codigo_anterior: 'Código anterior',
  numero_parte: 'Número de parte',
  medidas: 'Medidas',
  descripcion: 'Descripción',
};

/** Búsqueda universal (Ctrl+K, propuesta UX §5): código, número de parte, código anterior, medidas o descripción. */
export function Busqueda() {
  const dialogo = useRef<HTMLDialogElement>(null);
  const { filtro } = useFiltro();
  const navegar = useNavigate();
  const [texto, setTexto] = useState('');
  const [consulta, setConsulta] = useState('');
  const [todos, setTodos] = useState(false);
  const [activo, setActivo] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setConsulta(texto.trim()), 200);
    return () => clearTimeout(t);
  }, [texto]);
  useEffect(() => {
    const atajo = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        dialogo.current?.showModal();
      }
    };
    window.addEventListener('keydown', atajo);
    return () => window.removeEventListener('keydown', atajo);
  }, []);

  const q = useBuscar(
    { q: consulta, ...filtro, todos },
    { query: { enabled: consulta.length >= 2, placeholderData: (p) => p } },
  );
  const resultados = consulta.length >= 2 ? (q.data?.articulos ?? []) : [];

  const abrir = (r: Resultado) => {
    dialogo.current?.close();
    setTexto('');
    void navegar({ to: '/articulos/$itemCode', params: { itemCode: r.item_code } });
  };

  return (
    <>
      <button
        type="button"
        onClick={() => dialogo.current?.showModal()}
        className="flex h-9 items-center gap-2 rounded-md border border-borde bg-superficie px-2 text-sm text-suave hover:text-texto md:w-64"
        aria-label="Buscar (Ctrl+K)"
      >
        <Search className="size-4" aria-hidden />
        <span className="hidden md:inline">Buscar…</span>
        <kbd className="ml-auto hidden rounded border border-borde px-1.5 text-xs md:inline">Ctrl K</kbd>
      </button>
      <dialog
        ref={dialogo}
        aria-label="Búsqueda universal"
        className="mx-auto mt-[10vh] w-[min(40rem,calc(100vw-1.5rem))] rounded-lg border border-borde bg-superficie p-0 text-texto backdrop:bg-black/40"
        onClick={(e) => e.target === dialogo.current && dialogo.current?.close()}
      >
        <div className="flex items-center gap-2 border-b border-borde p-3">
          <Search className="size-5 text-suave" aria-hidden />
          <input
            autoFocus
            value={texto}
            onChange={(e) => {
              setTexto(e.target.value);
              setActivo(0);
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setActivo((i) => Math.min(i + 1, resultados.length - 1));
              }
              if (e.key === 'ArrowUp') {
                e.preventDefault();
                setActivo((i) => Math.max(i - 1, 0));
              }
              if (e.key === 'Enter' && resultados[activo]) abrir(resultados[activo]);
            }}
            role="combobox"
            aria-label="Buscar en Nexo"
            aria-expanded={resultados.length > 0}
            aria-controls="resultados-busqueda"
            aria-activedescendant={resultados[activo] ? `resultado-${activo}` : undefined}
            className="w-full bg-transparent text-base outline-none placeholder:text-suave"
            placeholder="Código, número de parte, medidas (400x518x26) o descripción"
          />
        </div>
        <div className="flex items-center justify-between border-b border-borde px-3 py-1.5 text-xs text-suave">
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={todos}
              onChange={(e) => {
                setTodos(e.target.checked);
                setActivo(0);
              }}
            />{' '}
            Buscar en todos los tipos
          </label>
          {q.data?.medidas && (
            <span className="flex items-center gap-1">
              <Ruler className="size-3.5" aria-hidden /> Medidas {q.data.medidas.map((m) => numero(m)).join(' × ')} mm
              (±10)
            </span>
          )}
        </div>
        <ul id="resultados-busqueda" role="listbox" className="max-h-[50vh] overflow-y-auto p-1">
          {consulta.length >= 2 && q.data && resultados.length === 0 && (
            <li className="p-4 text-sm text-suave">
              Sin resultados{todos ? '' : ' en este tipo de artículo. Prueba «Buscar en todos los tipos».'}
            </li>
          )}
          {resultados.map((r, i) => (
            <li
              key={r.item_code}
              id={`resultado-${i}`}
              role="option"
              aria-selected={i === activo}
              onMouseEnter={() => setActivo(i)}
              onClick={() => abrir(r)}
              className="flex cursor-pointer items-center justify-between gap-3 rounded-md px-3 py-2 text-sm aria-selected:bg-superficie-2"
            >
              <span className="min-w-0">
                <span className="font-medium">{r.item_code}</span>
                <span className="ml-2 text-xs text-suave">{COINCIDE[r.coincide]}</span>
                <span className="block truncate text-suave">{r.descripcion}</span>
              </span>
              <EtiquetaEstado estado={r.estado} />
            </li>
          ))}
        </ul>
        {consulta.length < 2 && (
          <p className="p-4 text-sm text-suave">Escribe al menos 2 caracteres. ↑↓ para moverte, Enter para abrir.</p>
        )}
      </dialog>
    </>
  );
}
