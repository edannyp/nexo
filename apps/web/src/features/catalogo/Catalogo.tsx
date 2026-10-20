import { useArticulosDeParte, useListarCatalogo, type Estado } from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { ArrowLeftRight, Link2, Search, Star } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { cn } from '@/shared/cn';
import { EtiquetaEstado } from '@/shared/estados';
import { Aviso, Boton, Insignia } from '@/shared/ui';

const POR_PAGINA = 30;
const n = (x?: string | null) => (x == null ? '—' : String(Number(x)));

function ArticulosDeParte({ parteId, tolerancia }: { parteId: number; tolerancia: number }) {
  const { filtro } = useFiltro();
  const q = useArticulosDeParte(parteId, { cat: filtro.cat, linea: filtro.linea, tolerancia });
  const d = q.data;
  if (q.isError) return <Aviso tono="error" titulo={q.error.problema.title} />;
  if (!d) return <p className="p-4 text-sm text-suave">Buscando artículos…</p>;
  const m = d.parte.medidas;
  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="font-medium">{d.parte.descripcion ?? `Parte ${d.parte.parte_id}`}</p>
        <p className="text-xs text-suave tabular-nums">
          Parte {d.parte.parte_id} · panal {n(m.alto)}×{n(m.largo)}×{n(m.ancho)} mm
          {d.parte.numeros ? ` · ${d.parte.numeros}` : ''}
        </p>
      </div>
      <div>
        <p className="mb-1 text-xs text-suave uppercase">Vinculada a ({d.vinculados.length})</p>
        {d.vinculados.length === 0 ? (
          <p className="text-sm text-suave">Ningún artículo de Nexo la usa todavía.</p>
        ) : (
          <ul className="space-y-1">
            {d.vinculados.map((a) => (
              <li key={a.item_code} className="flex flex-wrap items-center gap-2 text-sm">
                {a.es_principal && <Star className="size-3.5 fill-current text-por-validar" aria-label="Principal" />}
                <Link to="/articulos/$itemCode" params={{ itemCode: a.item_code }} className="font-medium underline">
                  {a.item_code}
                </Link>
                <EtiquetaEstado estado={a.estado as Estado} />
                <span className="truncate text-xs text-suave">{a.descripcion}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <p className="mb-1 text-xs text-suave uppercase">Artículos que podrían ser esta parte</p>
        {d.candidatos.length === 0 ? (
          <p className="text-sm text-suave">Ninguno coincide por medidas, números o vehículos.</p>
        ) : (
          <ul className="divide-y divide-borde rounded-md border border-borde">
            {d.candidatos.map((a) => (
              <li key={a.item_code} className="flex flex-wrap items-start gap-3 px-3 py-2">
                <span className="grid size-9 shrink-0 place-items-center rounded-full border border-borde text-sm font-semibold tabular-nums">
                  {a.puntaje}
                </span>
                <div className="min-w-0 flex-1 text-sm">
                  <p className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{a.item_code}</span>
                    <EtiquetaEstado estado={a.estado as Estado} />
                    <span className="text-xs text-suave">{a.linea.toLowerCase()}</span>
                  </p>
                  <p className="truncate text-xs text-suave">{a.descripcion}</p>
                  <p className="mt-1 flex flex-wrap gap-1">
                    {a.razones.map((r) => (
                      <Insignia key={r} className={cn(r.startsWith('Ancho distinto') && 'text-rechazado')}>
                        {r}
                      </Insignia>
                    ))}
                  </p>
                </div>
                <Link
                  to="/articulos/$itemCode"
                  params={{ itemCode: a.item_code }}
                  search={{ pestana: 'emparejamiento', parte: parteId }}
                  className="flex items-center gap-1 self-center rounded-md border border-borde px-2 py-1 text-xs hover:bg-superficie-2"
                >
                  <Link2 className="size-3.5" aria-hidden /> Abrir para vincular
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** Catálogo maestro, vista inversa (propuesta UX §6.8): qué partes tienen artículo y cuáles no. */
export function Catalogo() {
  const { filtro } = useFiltro();
  const [texto, setTexto] = useState('');
  const [q, setQ] = useState('');
  const [sinArticulo, setSinArticulo] = useState(false);
  const [tolerancia, setTolerancia] = useState(10);
  const [pagina, setPagina] = useState(0);
  const [elegida, setElegida] = useState<number | null>(null);
  const lista = useListarCatalogo({
    cat: filtro.cat,
    linea: filtro.linea,
    q: q || undefined,
    sin_articulo: sinArticulo,
    tolerancia,
    limite: POR_PAGINA,
    desde: pagina * POR_PAGINA,
  });

  useEffect(() => {
    const t = setTimeout(() => (setQ(texto.trim()), setPagina(0)), 350);
    return () => clearTimeout(t);
  }, [texto]);

  const r = lista.data;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Catálogo maestro</h1>
      {r && !r.disponible && (
        <Aviso tono="info" titulo="Catálogo maestro no disponible">
          La API no tiene acceso a Consolidación.
        </Aviso>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <label className="relative min-w-0 flex-1 basis-64">
          <Search className="absolute top-3 left-3 size-4 text-suave" aria-hidden />
          <input
            type="search"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            aria-label="Buscar en el catálogo"
            placeholder="400x518x26, número o descripción"
            className="h-10 w-full rounded-md border border-borde bg-superficie pr-3 pl-9 text-base sm:text-sm"
          />
        </label>
        <label className="flex items-center gap-1.5 text-sm text-suave">
          <ArrowLeftRight className="size-4" aria-hidden /> ±
          <select
            aria-label="Tolerancia de medidas"
            value={tolerancia}
            onChange={(e) => setTolerancia(Number(e.target.value))}
            className="h-9 rounded-md border border-borde bg-superficie px-2 text-sm"
          >
            {[5, 10, 15, 20].map((t) => (
              <option key={t} value={t}>
                {t} mm
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-4"
            checked={sinArticulo}
            onChange={(e) => (setSinArticulo(e.target.checked), setPagina(0))}
          />
          Solo sin artículo
        </label>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:items-start">
        <section aria-label="Partes" className="rounded-lg border border-borde bg-superficie">
          <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
            {r ? `${r.total} partes` : 'Partes'}
          </h2>
          {lista.isError && <Aviso tono="error" titulo={lista.error.problema.title} />}
          {lista.isLoading && <p className="p-4 text-sm text-suave">Cargando…</p>}
          {r?.disponible && r.partes.length === 0 && (
            <p className="p-6 text-center text-sm text-suave">Nada coincide con el filtro.</p>
          )}
          <ul className="divide-y divide-borde">
            {r?.partes.map(({ parte: p, articulos }) => (
              <li key={p.parte_id}>
                <button
                  type="button"
                  aria-pressed={elegida === p.parte_id}
                  onClick={() => setElegida(p.parte_id)}
                  className={cn(
                    'flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-superficie-2',
                    elegida === p.parte_id && 'bg-primario/5 ring-1 ring-primario/40 ring-inset',
                  )}
                >
                  <span className="min-w-0 flex-1 text-sm">
                    <span className="font-medium">{p.descripcion ?? `Parte ${p.parte_id}`}</span>
                    <span className="block text-xs text-suave tabular-nums">
                      {n(p.medidas.alto)}×{n(p.medidas.largo)}×{n(p.medidas.ancho)} mm
                      {p.numeros ? ` · ${p.numeros}` : ''} · {p.n_aplicaciones} aplicaciones
                    </span>
                  </span>
                  <Insignia className={cn(articulos ? 'border-validado/40 text-validado' : 'text-suave')}>
                    {articulos ? `${articulos} ${articulos === 1 ? 'artículo' : 'artículos'}` : 'Sin artículo'}
                  </Insignia>
                </button>
              </li>
            ))}
          </ul>
          {r && r.total > POR_PAGINA && (
            <div className="flex items-center justify-between border-t border-borde p-3 text-sm">
              <Boton variante="secundario" disabled={pagina === 0} onClick={() => setPagina((x) => x - 1)}>
                Anteriores
              </Boton>
              <span className="text-suave">
                {pagina * POR_PAGINA + 1}–{Math.min((pagina + 1) * POR_PAGINA, r.total)} de {r.total}
              </span>
              <Boton
                variante="secundario"
                disabled={(pagina + 1) * POR_PAGINA >= r.total}
                onClick={() => setPagina((x) => x + 1)}
              >
                Siguientes
              </Boton>
            </div>
          )}
        </section>
        <section aria-label="Detalle de la parte" className="rounded-lg border border-borde bg-superficie">
          <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
            Artículos de la parte
          </h2>
          {elegida ? (
            <ArticulosDeParte key={`${elegida}-${tolerancia}`} parteId={elegida} tolerancia={tolerancia} />
          ) : (
            <p className="p-4 text-sm text-suave">Elige una parte para ver qué artículos la usan o podrían usarla.</p>
          )}
        </section>
      </div>
    </div>
  );
}
