import {
  getListarVistasQueryKey,
  useBorrarVista,
  useGuardarVista,
  useListarArticulos,
  useListarVistas,
  type ArticuloFila,
  type Estado,
  type Orden,
} from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearch } from '@tanstack/react-router';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type VisibilityState,
} from '@tanstack/react-table';
import { Bookmark, Camera, Columns3, Link2, ListFilter, Lock, Search, TriangleAlert, X } from 'lucide-react';
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { guardar, leer } from '@/shared/almacen';
import { cn } from '@/shared/cn';
import { EtiquetaEstado, ORDEN_ESTADOS } from '@/shared/estados';
import { momento, numero, porcentaje } from '@/shared/formato';
import { Tendencia } from '@/shared/graficos';
import { atajoSimple } from '@/shared/teclado';
import { Aviso, Boton } from '@/shared/ui';

import { aBusqueda, aParametros, cuantosFiltros, validarExplorar, type FiltrosExplorar } from './filtros';

const POR_PAGINA = 50;
const CLAVE_COLUMNAS = 'nexo.explorar.columnas';
const ORDENES: { valor: Orden; nombre: string }[] = [
  { valor: 'venta', nombre: 'Venta (clase y participación)' },
  { valor: 'codigo', nombre: 'Código' },
  { valor: 'descripcion', nombre: 'Descripción' },
  { valor: 'estado', nombre: 'Estado' },
  { valor: 'anio', nombre: 'Año' },
  { valor: 'reciente', nombre: 'Último cambio' },
  { valor: 'faltantes', nombre: 'Más requisitos pendientes' },
];

const col = createColumnHelper<ArticuloFila>();
const mm = (v?: string | null) => (v ? numero(v) : '—');

const COLUMNAS = [
  col.accessor('item_code', {
    header: 'Código',
    cell: (c) => <span className="font-medium">{c.getValue()}</span>,
    meta: { orden: 'codigo', fija: true },
  }),
  col.accessor('descripcion', {
    header: 'Descripción',
    cell: (c) => <span className="block max-w-80 truncate">{c.getValue()}</span>,
    meta: { orden: 'descripcion' },
  }),
  col.accessor('estado', {
    header: 'Estado',
    cell: (c) => <EtiquetaEstado estado={c.getValue()} />,
    meta: { orden: 'estado' },
  }),
  col.display({
    id: 'vehiculo',
    header: 'Vehículo (SAP)',
    cell: ({ row: { original: a } }) => (
      <span className="block max-w-56 truncate">
        {[a.marca_vehiculo, a.modelo_vehiculo].filter(Boolean).join(' ') || '—'}
        {a.anio_desde ? (
          <span className="text-suave">
            {' '}
            · {a.anio_desde}–{a.anio_hasta ?? ''}
          </span>
        ) : null}
      </span>
    ),
    meta: { orden: 'anio' },
  }),
  col.accessor('vehiculo_principal', {
    header: 'Vehículo principal',
    cell: (c) => (
      <span className="block max-w-56 truncate">{c.getValue() ?? <span className="text-suave">—</span>}</span>
    ),
  }),
  col.display({
    id: 'medidas',
    header: 'Medidas core (mm)',
    cell: ({ row: { original: a } }) => (
      <span className="tabular-nums">
        {mm(a.panal_alto_mm)} × {mm(a.panal_largo_mm)} × {mm(a.panal_ancho_mm)}
      </span>
    ),
  }),
  col.accessor('faltan', {
    header: 'Faltan',
    cell: (c) =>
      c.getValue() === 0 ? (
        <span className="text-validado">Completo</span>
      ) : (
        <span className="tabular-nums">{c.getValue()}</span>
      ),
    meta: { orden: 'faltantes', derecha: true },
  }),
  col.display({
    id: 'cobertura',
    header: 'Foto · Emparejado · SAP',
    cell: ({ row: { original: a } }) => (
      <span className="flex items-center gap-2 text-suave">
        <span title={`${a.fotos} fotos`} className={cn('flex items-center gap-0.5', a.fotos > 0 && 'text-texto')}>
          <Camera className="size-3.5" aria-hidden />
          <span className="sr-only">Fotos:</span>
          {a.fotos}
        </span>
        <Link2
          className={cn('size-3.5', a.emparejado && 'text-texto')}
          aria-label={a.emparejado ? 'Emparejado' : 'Sin emparejar'}
        />
        {a.hallazgos > 0 && (
          <span title="Hallazgos de calidad SAP" className="flex items-center gap-0.5 text-rechazado">
            <TriangleAlert className="size-3.5" aria-hidden />
            {a.hallazgos}
          </span>
        )}
      </span>
    ),
  }),
  col.display({
    id: 'venta',
    header: 'Venta',
    cell: ({ row: { original: a } }) =>
      a.clase ? (
        <span className="flex items-center gap-2 tabular-nums">
          <span className="font-medium">{a.clase}</span>
          <span className="text-suave">{porcentaje(a.participacion)}</span>
          <Tendencia valor={a.tendencia} />
        </span>
      ) : (
        <span className="text-suave">Sin venta</span>
      ),
    meta: { orden: 'venta' },
  }),
  col.display({
    id: 'reserva',
    header: 'Reservado',
    cell: ({ row: { original: a } }) =>
      a.reservado_por ? (
        <span
          className="flex items-center gap-1 text-suave"
          title={a.reservado_hasta ? `Hasta ${momento(a.reservado_hasta)}` : ''}
        >
          <Lock className="size-3.5" aria-hidden /> {a.reservado_por}
        </span>
      ) : null,
  }),
  col.accessor('actualizado_en', {
    header: 'Último cambio',
    cell: (c) => <span className="text-suave">{momento(c.getValue())}</span>,
    meta: { orden: 'reciente' },
  }),
];

const COLUMNAS_DEFECTO: VisibilityState = { reserva: true, actualizado_en: false };

function Faceta({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-1.5">
      <legend className="mb-1 text-xs font-medium tracking-wide text-suave uppercase">{titulo}</legend>
      {children}
    </fieldset>
  );
}

function Casilla({
  marcada,
  alCambiar,
  children,
}: {
  marcada: boolean;
  alCambiar: (v: boolean) => void;
  children: ReactNode;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm">
      <input type="checkbox" checked={marcada} onChange={(e) => alCambiar(e.target.checked)} className="size-4" />
      {children}
    </label>
  );
}

/** Sí / No / Indiferente para filtros booleanos. */
function TresEstados({
  etiqueta,
  valor,
  alCambiar,
}: {
  etiqueta: string;
  valor?: boolean;
  alCambiar: (v?: boolean) => void;
}) {
  const opciones: { v?: boolean; t: string }[] = [{ t: 'Todos' }, { v: true, t: 'Sí' }, { v: false, t: 'No' }];
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <span>{etiqueta}</span>
      <div className="flex rounded-md border border-borde" role="group" aria-label={etiqueta}>
        {opciones.map((o) => (
          <button
            key={o.t}
            type="button"
            aria-pressed={valor === o.v}
            onClick={() => alCambiar(o.v)}
            className="px-2 py-0.5 text-xs first:rounded-l-md last:rounded-r-md aria-pressed:bg-superficie-2 aria-pressed:font-medium"
          >
            {o.t}
          </button>
        ))}
      </div>
    </div>
  );
}

function PanelFiltros({ f, poner }: { f: FiltrosExplorar; poner: (cambios: Partial<FiltrosExplorar>) => void }) {
  const alternar = <T,>(lista: T[] | undefined, v: T, si: boolean) => {
    const nueva = si ? [...(lista ?? []), v] : (lista ?? []).filter((x) => x !== v);
    return nueva.length ? nueva : undefined;
  };
  return (
    <div className="space-y-5">
      <Faceta titulo="Estado">
        {ORDEN_ESTADOS.map((e) => (
          <Casilla
            key={e}
            marcada={!!f.estado?.includes(e)}
            alCambiar={(si) => poner({ estado: alternar<Estado>(f.estado, e, si) })}
          >
            <EtiquetaEstado estado={e} />
          </Casilla>
        ))}
      </Faceta>
      <Faceta titulo="Ficha">
        <TresEstados
          etiqueta="Completa"
          valor={f.completitud === undefined ? undefined : f.completitud === 'completa'}
          alCambiar={(v) => poner({ completitud: v === undefined ? undefined : v ? 'completa' : 'incompleta' })}
        />
        <TresEstados etiqueta="Con foto" valor={f.con_foto} alCambiar={(v) => poner({ con_foto: v })} />
        <TresEstados etiqueta="Emparejado" valor={f.emparejado} alCambiar={(v) => poner({ emparejado: v })} />
        <TresEstados etiqueta="Hallazgo SAP" valor={f.con_hallazgo} alCambiar={(v) => poner({ con_hallazgo: v })} />
      </Faceta>
      <Faceta titulo="Vehículo principal">
        <TresEstados etiqueta="Tiene" valor={f.con_principal} alCambiar={(v) => poner({ con_principal: v })} />
        <input
          key={f.vehiculo ?? ''}
          type="search"
          aria-label="Marca o modelo del vehículo principal"
          placeholder="Marca o modelo (Enter)"
          defaultValue={f.vehiculo ?? ''}
          className="h-8 w-full rounded-md border border-borde bg-superficie px-2 text-sm"
          onBlur={(e) => poner({ vehiculo: e.currentTarget.value.trim() || undefined })}
          onKeyDown={(e) => e.key === 'Enter' && poner({ vehiculo: e.currentTarget.value.trim() || undefined })}
        />
      </Faceta>
      <Faceta titulo="Clase de venta">
        {['A', 'B', 'C', 'SIN_VENTA'].map((c) => (
          <Casilla
            key={c}
            marcada={!!f.clase?.includes(c)}
            alCambiar={(si) => poner({ clase: alternar(f.clase, c, si) })}
          >
            {c === 'SIN_VENTA' ? 'Sin venta' : `Clase ${c}`}
          </Casilla>
        ))}
      </Faceta>
      <Faceta titulo="Reserva">
        <select
          aria-label="Reserva"
          value={f.reserva ?? ''}
          onChange={(e) => poner({ reserva: (e.target.value || undefined) as FiltrosExplorar['reserva'] })}
          className="h-9 w-full rounded-md border border-borde bg-superficie px-2 text-sm"
        >
          <option value="">Todos</option>
          <option value="mia">Reservados por mí</option>
          <option value="libre">Libres</option>
          <option value="otros">Reservados por otros</option>
        </select>
      </Faceta>
    </div>
  );
}

function MenuVistas({ f, aplicar }: { f: FiltrosExplorar; aplicar: (f: FiltrosExplorar) => void }) {
  const consultas = useQueryClient();
  const vistas = useListarVistas();
  const guardarVista = useGuardarVista();
  const borrar = useBorrarVista();
  const refrescar = () => void consultas.invalidateQueries({ queryKey: getListarVistasQueryKey() });
  return (
    <>
      <Boton variante="secundario" popoverTarget="menu-vistas" className="h-9 px-3">
        <Bookmark className="size-4" aria-hidden /> Vistas
      </Boton>
      <div
        id="menu-vistas"
        popover="auto"
        className="m-auto w-72 rounded-lg border border-borde bg-superficie p-2 text-texto shadow-lg"
      >
        <p className="px-2 pb-1 text-xs text-suave">Mis vistas guardadas</p>
        {vistas.data?.length === 0 && <p className="px-2 py-1 text-sm text-suave">Aún no tienes vistas.</p>}
        <ul>
          {vistas.data?.map((v) => (
            <li key={v.id} className="flex items-center gap-1">
              <button
                type="button"
                className="flex-1 truncate rounded-md px-2 py-1.5 text-left text-sm hover:bg-superficie-2"
                onClick={() => aplicar(validarExplorar(v.parametros as Record<string, unknown>))}
              >
                {v.nombre}
              </button>
              <button
                type="button"
                aria-label={`Borrar la vista ${v.nombre}`}
                className="grid size-7 place-items-center rounded-md text-suave hover:bg-superficie-2"
                onClick={() => borrar.mutate({ vistaId: v.id }, { onSuccess: refrescar })}
              >
                <X className="size-3.5" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="mt-1 w-full rounded-md border-t border-borde px-2 pt-2 pb-1 text-left text-sm hover:bg-superficie-2"
          onClick={() => {
            const nombre = prompt('Nombre de la vista (filtros, búsqueda y orden actuales):');
            if (nombre?.trim()) {
              guardarVista.mutate(
                { data: { nombre: nombre.trim(), parametros: aBusqueda(f) } },
                { onSuccess: refrescar },
              );
            }
          }}
        >
          Guardar la vista actual…
        </button>
      </div>
    </>
  );
}

/** Explorar: tabla de artículos del tipo elegido (propuesta UX §6.2). Filtros y orden en la URL; columnas por usuario. */
export function Explorar() {
  const { filtro } = useFiltro();
  const navegar = useNavigate();
  const f = validarExplorar(useSearch({ strict: false }) as Record<string, unknown>);
  const [texto, setTexto] = useState(f.q ?? '');
  const [cursores, setCursores] = useState<(string | undefined)[]>([undefined]);
  const [activo, setActivo] = useState(0);
  const [verFiltros, setVerFiltros] = useState(false);
  const [columnas, setColumnas] = useState<VisibilityState>(() => {
    try {
      return { ...COLUMNAS_DEFECTO, ...(JSON.parse(leer(CLAVE_COLUMNAS) ?? '{}') as VisibilityState) };
    } catch {
      return COLUMNAS_DEFECTO;
    }
  });
  const cursor = cursores[cursores.length - 1];
  const clave = JSON.stringify([f, filtro]);

  const poner = (cambios: Partial<FiltrosExplorar>) =>
    void navegar({ to: '.', search: (prev) => ({ ...prev, ...aBusqueda({ ...f, ...cambios }) }), replace: true });

  // Al cambiar filtros o tipo: vuelve a la primera página
  useEffect(() => {
    setCursores([undefined]);
    setActivo(0);
  }, [clave]);
  // Búsqueda con espera breve mientras se escribe
  useEffect(() => {
    const t = setTimeout(() => (texto.trim() || undefined) !== f.q && poner({ q: texto.trim() || undefined }), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto]);

  const q = useListarArticulos(
    { ...aParametros(f), ...filtro, limit: POR_PAGINA, ...(cursor ? { cursor } : {}) },
    { query: { placeholderData: (previo) => previo } },
  );
  const filas = useMemo(() => q.data?.items ?? [], [q.data]);
  // TanStack Table 8 no es compatible con el compilador de React: este componente no se memoiza (es lo esperado)
  // eslint-disable-next-line react-hooks/incompatible-library
  const tabla = useReactTable({
    data: filas,
    columns: COLUMNAS,
    getCoreRowModel: getCoreRowModel(),
    state: { columnVisibility: columnas },
    onColumnVisibilityChange: (u) =>
      setColumnas((prev) => {
        const nuevo = typeof u === 'function' ? u(prev) : u;
        guardar(CLAVE_COLUMNAS, JSON.stringify(nuevo));
        return nuevo;
      }),
  });

  const abrir = (item: string) => void navegar({ to: '/articulos/$itemCode', params: { itemCode: item } });

  // Teclado: J/K para moverse, Enter para abrir (fuera de los campos de texto)
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (!atajoSimple(e)) return;
      if (e.key === 'j') setActivo((i) => Math.min(i + 1, filas.length - 1));
      if (e.key === 'k') setActivo((i) => Math.max(i - 1, 0));
      if (e.key === 'Enter' && filas[activo]) abrir(filas[activo].item_code);
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filas, activo]);

  const n = cuantosFiltros(f);
  const pagina = cursores.length;
  const total = q.data?.total ?? 0;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Explorar</h1>
          <p className="text-sm text-suave">
            {q.data ? `${numero(total)} artículos` : 'Cargando…'} · <kbd className="text-xs">J</kbd>/
            <kbd className="text-xs">K</kbd> para moverte, <kbd className="text-xs">Enter</kbd> para abrir
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <MenuVistas
            f={f}
            aplicar={(v) =>
              void navegar({ to: '.', search: (prev) => ({ cat: prev.cat, linea: prev.linea, ...aBusqueda(v) }) })
            }
          />
          <Boton variante="secundario" popoverTarget="menu-columnas" className="hidden h-9 px-3 md:inline-flex">
            <Columns3 className="size-4" aria-hidden /> Columnas
          </Boton>
          <div
            id="menu-columnas"
            popover="auto"
            className="m-auto w-60 rounded-lg border border-borde bg-superficie p-3 text-texto shadow-lg"
          >
            <p className="mb-2 text-xs text-suave">Columnas visibles</p>
            {tabla
              .getAllLeafColumns()
              .filter((c) => !(c.columnDef.meta as { fija?: boolean } | undefined)?.fija)
              .map((c) => (
                <Casilla key={c.id} marcada={c.getIsVisible()} alCambiar={(v) => c.toggleVisibility(v)}>
                  {String(c.columnDef.header)}
                </Casilla>
              ))}
          </div>
          <select
            aria-label="Ordenar por"
            value={f.orden ?? 'venta'}
            onChange={(e) => poner({ orden: e.target.value as Orden })}
            className="h-9 rounded-md border border-borde bg-superficie px-2 text-sm"
          >
            {ORDENES.map((o) => (
              <option key={o.valor} value={o.valor}>
                Orden: {o.nombre}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="flex gap-2">
        <label className="relative flex-1">
          <span className="sr-only">Buscar en la tabla</span>
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-suave" aria-hidden />
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Código, número de parte, código anterior o descripción"
            className="h-10 w-full rounded-md border border-borde bg-superficie pr-3 pl-9 text-base sm:text-sm"
          />
        </label>
        <Boton
          variante="secundario"
          className="lg:hidden"
          onClick={() => setVerFiltros((v) => !v)}
          aria-expanded={verFiltros}
        >
          <ListFilter className="size-4" aria-hidden /> Filtros{n ? ` (${n})` : ''}
        </Boton>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <aside
          className={cn('rounded-lg border border-borde bg-superficie p-4 lg:block', !verFiltros && 'hidden')}
          aria-label="Filtros"
        >
          <PanelFiltros f={f} poner={poner} />
          {n > 0 && (
            <button
              type="button"
              className="mt-4 text-sm text-suave underline"
              onClick={() =>
                void navegar({ to: '.', search: (prev) => ({ cat: prev.cat, linea: prev.linea, q: f.q }) })
              }
            >
              Quitar filtros
            </button>
          )}
        </aside>

        <div className={cn('min-w-0 space-y-3', q.isPlaceholderData && 'opacity-60')}>
          {q.isError && (
            <Aviso tono="error" titulo="No se pudo cargar la lista">
              {q.error.problema.detail}
            </Aviso>
          )}
          {q.data && filas.length === 0 && (
            <Aviso tono="info" titulo="No hay artículos con estos filtros">
              Cambia o quita filtros, o revisa el tipo de artículo elegido arriba.
            </Aviso>
          )}

          {/* Celular: tarjetas */}
          <ul className="space-y-2 md:hidden">
            {filas.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  onClick={() => abrir(a.item_code)}
                  className="w-full rounded-lg border border-borde bg-superficie p-3 text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-medium">{a.item_code}</span>
                    <EtiquetaEstado estado={a.estado} />
                  </div>
                  <p className="truncate text-sm text-suave">{a.descripcion}</p>
                  <p className="mt-1 flex items-center gap-3 text-xs text-suave">
                    <span>{a.faltan === 0 ? 'Ficha completa' : `Faltan ${a.faltan}`}</span>
                    {a.clase && <span>Clase {a.clase}</span>}
                    {a.reservado_por && (
                      <span className="flex items-center gap-1">
                        <Lock className="size-3" aria-hidden /> {a.reservado_por}
                      </span>
                    )}
                  </p>
                </button>
              </li>
            ))}
          </ul>

          {/* Escritorio: tabla */}
          {filas.length > 0 && (
            <div className="hidden overflow-x-auto rounded-lg border border-borde bg-superficie md:block">
              <table className="w-full text-sm">
                <thead className="border-b border-borde text-left text-suave">
                  {tabla.getHeaderGroups().map((g) => (
                    <tr key={g.id}>
                      {g.headers.map((h) => {
                        const meta = h.column.columnDef.meta as { orden?: Orden; derecha?: boolean } | undefined;
                        const ordenada = meta?.orden && (f.orden ?? 'venta') === meta.orden;
                        return (
                          <th
                            key={h.id}
                            scope="col"
                            aria-sort={ordenada ? 'ascending' : undefined}
                            className={cn('px-3 py-2 font-medium whitespace-nowrap', meta?.derecha && 'text-right')}
                          >
                            {meta?.orden ? (
                              <button
                                type="button"
                                onClick={() => poner({ orden: meta.orden })}
                                className={cn('hover:text-texto', ordenada && 'text-texto')}
                              >
                                {flexRender(h.column.columnDef.header, h.getContext())}
                                {ordenada && ' ↓'}
                              </button>
                            ) : (
                              flexRender(h.column.columnDef.header, h.getContext())
                            )}
                          </th>
                        );
                      })}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {tabla.getRowModel().rows.map((r, i) => (
                    <tr
                      key={r.id}
                      onClick={() => abrir(r.original.item_code)}
                      onMouseEnter={() => setActivo(i)}
                      aria-selected={i === activo}
                      className="cursor-pointer border-b border-borde last:border-0 aria-selected:bg-superficie-2"
                    >
                      {r.getVisibleCells().map((c) => (
                        <td
                          key={c.id}
                          className={cn(
                            'px-3 py-2 whitespace-nowrap',
                            (c.column.columnDef.meta as { derecha?: boolean } | undefined)?.derecha && 'text-right',
                          )}
                        >
                          {flexRender(c.column.columnDef.cell, c.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {total > POR_PAGINA && (
            <nav className="flex items-center justify-between text-sm" aria-label="Páginas">
              <Boton variante="secundario" disabled={pagina === 1} onClick={() => setCursores((c) => c.slice(0, -1))}>
                Anterior
              </Boton>
              <span className="text-suave">
                Página {pagina} de {Math.ceil(total / POR_PAGINA)}
              </span>
              <Boton
                variante="secundario"
                disabled={!q.data?.next_cursor}
                onClick={() => q.data?.next_cursor && setCursores((c) => [...c, q.data.next_cursor ?? undefined])}
              >
                Siguiente
              </Boton>
            </nav>
          )}
        </div>
      </div>
    </div>
  );
}
