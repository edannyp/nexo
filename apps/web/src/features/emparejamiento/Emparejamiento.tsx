import { useListarArticulos, type Estado } from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { ChevronLeft, ChevronRight, Link2, Search, Unlink } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { cn } from '@/shared/cn';
import { EtiquetaEstado } from '@/shared/estados';
import { useRecorrido } from '@/shared/recorrido';
import { Aviso, Boton } from '@/shared/ui';

const POR_PAGINA = 30;
const VISTAS = [
  { id: 'sin', etiqueta: 'Sin emparejar', emparejado: false },
  { id: 'con', etiqueta: 'Emparejados', emparejado: true },
  { id: 'todos', etiqueta: 'Todos', emparejado: undefined },
] as const;
type Vista = (typeof VISTAS)[number]['id'];

const n = (x?: string | null) => (x == null ? '—' : String(Number(x)));

/**
 * Sección Emparejamiento (ADR 0028): fuera del proceso del artículo y solo con el permiso EMPAREJAR_CATALOGO. Lista los
 * artículos del tipo elegido (primero los que no tienen enlace) y abre el emparejador; no reserva ni cambia el estado.
 */
export function Emparejamiento() {
  useRecorrido('emparejamiento');
  const { filtro } = useFiltro();
  const [vista, setVista] = useState<Vista>('sin');
  const [texto, setTexto] = useState('');
  const [buscado, setBuscado] = useState('');
  const emparejado = VISTAS.find((v) => v.id === vista)?.emparejado;

  // Búsqueda con espera breve mientras se escribe; al cambiar filtros vuelve a la primera página
  useEffect(() => {
    const t = setTimeout(() => setBuscado(texto.trim()), 300);
    return () => clearTimeout(t);
  }, [texto]);
  // Las páginas recorridas valen para estos filtros: si cambian, se vuelve a la primera
  const clave = `${vista}|${buscado}|${filtro.cat}|${filtro.linea}`;
  const [paginas, setPaginas] = useState<{ clave: string; cursores: (string | undefined)[] }>({
    clave,
    cursores: [undefined],
  });
  const cursores = paginas.clave === clave ? paginas.cursores : [undefined];
  const setCursores = (f: (c: (string | undefined)[]) => (string | undefined)[]) =>
    setPaginas({ clave, cursores: f(cursores) });
  const pagina = cursores.length - 1;

  const q = useListarArticulos(
    {
      ...filtro,
      ...(emparejado !== undefined ? { emparejado } : {}),
      ...(buscado ? { q: buscado } : {}),
      orden: 'venta',
      limit: POR_PAGINA,
      ...(cursores[pagina] ? { cursor: cursores[pagina] } : {}),
    },
    { query: { placeholderData: (previo) => previo } },
  );
  const d = q.data;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold">Emparejamiento</h1>
        <p className="text-sm text-suave">
          Enlaza los artículos con su diagrama del catálogo maestro. No es parte del proceso del artículo: no hay que
          reservarlo y su estado no cambia.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div role="tablist" aria-label="Qué artículos ver" className="flex rounded-md border border-borde p-0.5">
          {VISTAS.map((v) => (
            <button
              key={v.id}
              role="tab"
              type="button"
              aria-selected={vista === v.id}
              onClick={() => setVista(v.id)}
              className="rounded px-3 py-1 text-sm text-suave aria-selected:bg-superficie-2 aria-selected:font-medium aria-selected:text-texto"
            >
              {v.etiqueta}
            </button>
          ))}
        </div>
        <label className="relative min-w-56 flex-1">
          <Search className="absolute top-2.5 left-2.5 size-4 text-suave" aria-hidden />
          <input
            type="search"
            aria-label="Buscar artículo"
            placeholder="Código, número de parte o descripción"
            value={texto}
            onChange={(x) => setTexto(x.target.value)}
            className="h-9 w-full rounded-md border border-borde bg-superficie pr-2 pl-8 text-base sm:text-sm"
          />
        </label>
      </div>

      {q.isError && <Aviso tono="error" titulo={q.error.problema.title} />}
      {!d && !q.isError && <p className="text-sm text-suave">Cargando…</p>}
      {d && (
        <section
          aria-label="Artículos"
          className={cn('rounded-lg border border-borde bg-superficie', q.isPlaceholderData && 'opacity-60')}
        >
          <p className="border-b border-borde px-4 py-2 text-xs text-suave">
            {d.total} {d.total === 1 ? 'artículo' : 'artículos'} · ordenados por venta
          </p>
          {d.items.length === 0 ? (
            <p className="p-6 text-center text-sm text-suave">
              {vista === 'sin' && !buscado
                ? 'Todos los artículos de este tipo ya están emparejados.'
                : 'Nada coincide.'}
            </p>
          ) : (
            <ul className="divide-y divide-borde">
              {d.items.map((a) => (
                <li key={a.item_code}>
                  <Link
                    to="/emparejamiento/$itemCode"
                    params={{ itemCode: a.item_code }}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-superficie-2"
                  >
                    {a.emparejado ? (
                      <Link2 className="size-4 shrink-0 text-validado" aria-label="Emparejado" />
                    ) : (
                      <Unlink className="size-4 shrink-0 text-suave" aria-label="Sin emparejar" />
                    )}
                    <span className="min-w-0 flex-1 text-sm">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{a.item_code}</span>
                        <EtiquetaEstado estado={a.estado as Estado} />
                        {a.clase && <span className="text-xs text-suave">Clase {a.clase}</span>}
                      </span>
                      <span className="block truncate text-xs text-suave">{a.descripcion}</span>
                      <span className="block text-xs text-suave tabular-nums">
                        Panal {n(a.panal_alto_mm)}×{n(a.panal_largo_mm)}×{n(a.panal_ancho_mm)} mm
                        {a.vehiculo_principal && ` · ${a.vehiculo_principal}`}
                      </span>
                    </span>
                    <ChevronRight className="size-4 shrink-0 text-suave" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {(pagina > 0 || d.next_cursor) && (
            <div className="flex items-center justify-between border-t border-borde px-4 py-2">
              <Boton variante="secundario" disabled={pagina === 0} onClick={() => setCursores((c) => c.slice(0, -1))}>
                <ChevronLeft className="size-4" aria-hidden /> Anterior
              </Boton>
              <span className="text-xs text-suave">Página {pagina + 1}</span>
              <Boton
                variante="secundario"
                disabled={!d.next_cursor}
                onClick={() => d.next_cursor && setCursores((c) => [...c, d.next_cursor ?? undefined])}
              >
                Siguiente <ChevronRight className="size-4" aria-hidden />
              </Boton>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
