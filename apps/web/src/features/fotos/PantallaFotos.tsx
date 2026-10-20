import { useListarSinFoto, type Estado } from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { ArrowLeft, ScanLine } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { cn } from '@/shared/cn';
import { EtiquetaEstado } from '@/shared/estados';
import { Boton } from '@/shared/ui';

import { FotosDelArticulo } from './FotosDelArticulo';

/** Pantalla del encargado de fotos (propuesta UX §6.9): buscar o escanear el código, subir, y lo que falta por fotografiar. */
export function PantallaFotos() {
  const { filtro } = useFiltro();
  const [codigo, setCodigo] = useState('');
  const [elegido, setElegido] = useState<string | null>(null);
  const pendientes = useListarSinFoto({ cat: filtro.cat, linea: filtro.linea, limite: 50 });

  const buscar = (e: FormEvent) => {
    e.preventDefault();
    const c = codigo.trim().toUpperCase();
    if (c) setElegido(c);
  };

  if (elegido) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <button type="button" onClick={() => setElegido(null)} className="flex items-center gap-1 text-sm text-suave">
            <ArrowLeft className="size-4" aria-hidden /> Otro artículo
          </button>
          <Link to="/articulos/$itemCode" params={{ itemCode: elegido }} className="text-sm underline">
            Ver el artículo
          </Link>
        </div>
        <h1 className="text-xl font-semibold">{elegido}</h1>
        <FotosDelArticulo key={elegido} itemCode={elegido} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-xl font-semibold">Fotos</h1>
      <form onSubmit={buscar} className="flex gap-2">
        <label className="relative flex-1">
          <ScanLine className="absolute top-3 left-3 size-4 text-suave" aria-hidden />
          <input
            autoFocus
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            aria-label="Código del artículo"
            placeholder="Escribe o escanea el código (RAD00188)"
            autoCapitalize="characters"
            className="h-10 w-full rounded-md border border-borde bg-superficie pr-3 pl-9 text-base uppercase sm:text-sm"
          />
        </label>
        <Boton type="submit">Abrir</Boton>
      </form>

      <section className="rounded-lg border border-borde bg-superficie">
        <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
          Sin foto propia · primero los que más se venden
        </h2>
        {pendientes.isLoading && <p className="p-4 text-sm text-suave">Cargando…</p>}
        {pendientes.data?.length === 0 && (
          <p className="p-6 text-center text-sm text-suave">Todos los artículos de este tipo ya tienen foto.</p>
        )}
        <ul className="divide-y divide-borde">
          {pendientes.data?.map((a) => (
            <li key={a.item_code}>
              <button
                type="button"
                onClick={() => setElegido(a.item_code)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-superficie-2"
              >
                <span
                  className={cn(
                    'grid size-7 shrink-0 place-items-center rounded-full border text-xs font-semibold',
                    a.clase === 'A' ? 'border-validado text-validado' : 'border-borde text-suave',
                  )}
                  title="Clase de venta"
                >
                  {a.clase ?? '–'}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium">{a.item_code}</span>
                  <span className="block truncate text-xs text-suave">{a.descripcion}</span>
                </span>
                <EtiquetaEstado estado={a.estado as Estado} />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
