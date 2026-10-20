import {
  ProblemaError,
  useBuscarPartes,
  useCompararParte,
  useDesvincularParte,
  useMarcarPartePrincipal,
  useObtenerEmparejamiento,
  useVincularParte,
  type CandidatoParte,
  type Emparejamiento as RespuestaEmparejamiento,
  type MedidasPanal,
  type ParteCatalogo,
} from '@nexo/api-client';
import { ArrowLeftRight, Check, ExternalLink, Link2, Search, Star, Unlink, X } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';

import { cn } from '@/shared/cn';
import { Aviso, Boton, Dialogo, Insignia } from '@/shared/ui';

const TOLERANCIAS = [5, 10, 15, 20];

const n = (x?: string | null) => (x == null ? '—' : String(Number(x)));
const textoMedidas = (m: MedidasPanal) =>
  m.alto == null && m.largo == null ? 'sin medidas' : `${n(m.alto)}×${n(m.largo)}×${n(m.ancho)}`;

function Puntaje({ valor }: { valor: number }) {
  return (
    <span
      className={cn(
        'grid size-10 shrink-0 place-items-center rounded-full border text-sm font-semibold tabular-nums',
        valor >= 75
          ? 'border-validado text-validado'
          : valor >= 50
            ? 'border-por-validar text-por-validar'
            : 'border-borde text-suave',
      )}
      title="Puntaje"
    >
      {valor}
    </span>
  );
}

/** Una parte del catálogo en una lista (candidata, resultado de búsqueda o vinculada). */
function FilaParte({
  p,
  activa,
  alElegir,
  puntaje,
  razones,
  extra,
}: {
  p: ParteCatalogo;
  activa: boolean;
  alElegir: () => void;
  puntaje?: number;
  razones?: string[];
  extra?: ReactNode;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={alElegir}
        aria-pressed={activa}
        className={cn(
          'flex w-full items-start gap-3 px-3 py-2.5 text-left hover:bg-superficie-2',
          activa && 'bg-primario/5 ring-1 ring-primario/40 ring-inset',
        )}
      >
        {puntaje !== undefined && <Puntaje valor={puntaje} />}
        <span className="min-w-0 flex-1 text-sm">
          <span className="font-medium">{p.descripcion ?? `Parte ${p.parte_id}`}</span>
          <span className="block text-xs text-suave tabular-nums">
            {textoMedidas(p.medidas)} mm{p.numeros ? ` · ${p.numeros}` : ''} · {p.n_fuentes}{' '}
            {p.n_fuentes === 1 ? 'fuente' : 'fuentes'}
          </span>
          {razones && razones.length > 0 && (
            <span className="mt-1 flex flex-wrap gap-1">
              {razones.map((r) => (
                <Insignia key={r} className={cn(r.startsWith('Ancho distinto') ? 'text-rechazado' : 'text-texto')}>
                  {r}
                </Insignia>
              ))}
            </span>
          )}
          {extra}
        </span>
      </button>
    </li>
  );
}

/** Comparación lado a lado con diferencias resaltadas, números, vehículos, imágenes y botones para vincular. */
function Comparar({
  itemCode,
  parteId,
  e,
  ocupado,
  alVincular,
}: {
  itemCode: string;
  parteId: number;
  e: RespuestaEmparejamiento;
  ocupado: boolean;
  alVincular: (principal: boolean, traer: boolean) => void;
}) {
  const q = useCompararParte(itemCode, parteId, { tolerancia: e.tolerancia });
  const [traer, setTraer] = useState(true);
  const [zoom, setZoom] = useState<string | null>(null);
  const c = q.data;
  if (q.isError) return <Aviso tono="error" titulo={q.error.problema.title} />;
  if (!c) return <p className="p-4 text-sm text-suave">Cargando la comparación…</p>;

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="font-medium">{c.parte.descripcion ?? `Parte ${c.parte.parte_id}`}</p>
        <p className="text-xs text-suave">
          Parte {c.parte.parte_id} · {c.parte.tipo_parte}
        </p>
      </div>
      {c.invertida && (
        <Aviso tono="info" titulo="Alto y largo invertidos">
          El catálogo publica las medidas al revés que SAP. Revisa cuál es el alto antes de confirmar la ficha.
        </Aviso>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-suave">
            <th className="py-1 font-normal">Atributo</th>
            <th className="py-1 font-normal">{itemCode}</th>
            <th className="py-1 font-normal">Catálogo</th>
            <th className="w-16 py-1" />
          </tr>
        </thead>
        <tbody className="divide-y divide-borde">
          {c.filas.map((f) => (
            <tr key={f.paid} className={cn(f.coincide === false && 'bg-rechazado/5')}>
              <td className="py-1.5 pr-2">{f.etiqueta}</td>
              <td className="py-1.5 pr-2 tabular-nums">{f.articulo ?? '—'}</td>
              <td className="py-1.5 pr-2 tabular-nums">{f.parte ?? '—'}</td>
              <td className="py-1.5 text-xs whitespace-nowrap">
                {f.coincide === true && (
                  <span className="flex items-center gap-0.5 text-validado">
                    <Check className="size-3.5" aria-label="Coincide" />
                    {f.diferencia}
                  </span>
                )}
                {f.coincide === false && (
                  <span className="flex items-center gap-0.5 text-rechazado">
                    <X className="size-3.5" aria-label="No coincide" />
                    {f.diferencia}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {c.numeros.length > 0 && (
        <div className="text-sm">
          <p className="text-xs text-suave">Números</p>
          <p className="flex flex-wrap gap-1.5">
            {c.numeros.map((x) => (
              <Insignia key={`${x.tipo}${x.numero}`}>
                {x.tipo} {x.marca ? `${x.marca} ` : ''}
                {x.numero}
              </Insignia>
            ))}
          </p>
        </div>
      )}
      {c.vehiculos.length > 0 && (
        <div className="text-sm">
          <p className="text-xs text-suave">
            Vehículos{c.vehiculos_comunes > 0 && ` · ${c.vehiculos_comunes} en común con el artículo`}
          </p>
          <p>{c.vehiculos.join(' · ')}</p>
        </div>
      )}
      {c.imagenes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {c.imagenes.map((i) => (
            <button
              key={i.url}
              type="button"
              onClick={() => setZoom(i.url)}
              className="overflow-hidden rounded-md border border-borde bg-white"
              aria-label={`Ampliar ${i.tipo.toLowerCase()}`}
            >
              <img src={i.url} alt={i.tipo.toLowerCase()} loading="lazy" className="h-28 w-40 object-contain" />
            </button>
          ))}
        </div>
      )}
      {c.fuentes.length > 0 && (
        <p className="flex flex-wrap gap-x-3 text-xs text-suave">
          {c.fuentes.map((f) =>
            f.url ? (
              <a
                key={f.id_en_fuente}
                href={f.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 underline"
              >
                {f.fuente} {f.id_en_fuente} <ExternalLink className="size-3" aria-hidden />
              </a>
            ) : (
              <span key={f.id_en_fuente}>
                {f.fuente} {f.id_en_fuente}
              </span>
            ),
          )}
        </p>
      )}

      {e.editable && !c.vinculada && c.parte.estado === 'ACTIVA' && (
        <div className="space-y-2 border-t border-borde pt-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="size-4" checked={traer} onChange={(x) => setTraer(x.target.checked)} />
            Traer sus atributos y aplicaciones como sugerencias
          </label>
          <div className="flex flex-wrap gap-2">
            <Boton cargando={ocupado} onClick={() => alVincular(true, traer)}>
              <Star className="size-4" aria-hidden /> Vincular como principal
            </Boton>
            <Boton variante="secundario" disabled={ocupado} onClick={() => alVincular(false, traer)}>
              <Link2 className="size-4" aria-hidden /> Vincular
            </Boton>
          </div>
        </div>
      )}
      {c.vinculada && <p className="text-sm text-validado">Ya está vinculada a este artículo.</p>}

      <Dialogo abierto={!!zoom} alCerrar={() => setZoom(null)} titulo="Imagen del catálogo">
        {zoom && (
          <div className="space-y-2">
            <img src={zoom} alt="Imagen ampliada" className="max-h-[70vh] w-full bg-white object-contain" />
            <a href={zoom} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm underline">
              Abrir en otra pestaña <ExternalLink className="size-3.5" aria-hidden />
            </a>
          </div>
        )}
      </Dialogo>
    </div>
  );
}

/** Pestaña Emparejamiento y diagramas (propuesta UX §6.4, ADR 0011). */
export function Emparejamiento({ itemCode, parteInicial }: { itemCode: string; parteInicial?: number }) {
  const [tolerancia, setTolerancia] = useState(10);
  const [texto, setTexto] = useState('');
  const [buscado, setBuscado] = useState('');
  const [elegida, setElegida] = useState<number | null>(parteInicial ?? null);
  const [hecho, setHecho] = useState<string>();
  const q = useObtenerEmparejamiento(itemCode, { tolerancia });
  const e = q.data;
  const busqueda = useBuscarPartes(
    { q: buscado, tolerancia, part_terminology_id: e?.part_terminology_id ?? undefined },
    { query: { enabled: buscado.length >= 2 && !!e?.catalogo_disponible } },
  );
  const vincular = useVincularParte();
  const principal = useMarcarPartePrincipal();
  const desvincular = useDesvincularParte();

  // La búsqueda manual espera a que se deje de escribir
  useEffect(() => {
    const t = setTimeout(() => setBuscado(texto.trim()), 350);
    return () => clearTimeout(t);
  }, [texto]);

  if (q.isError) return <Aviso tono="error" titulo={q.error.problema.title} />;
  if (!e) return <p className="text-sm text-suave">Cargando el emparejamiento…</p>;

  const ocupado = vincular.isPending || principal.isPending || desvincular.isPending;
  const error = [vincular.error, principal.error, desvincular.error].find((x) => x instanceof ProblemaError);
  const visible = elegida ?? e.vinculadas[0]?.parte_id ?? e.candidatos[0]?.parte.parte_id ?? null;
  const params = { tolerancia };
  const alVincular = (parteId: number, esPrincipal: boolean, traer: boolean) =>
    vincular.mutate(
      {
        itemCode,
        data: { version: e.version, parte_id: parteId, principal: esPrincipal, traer_sugerencias: traer },
        params,
      },
      {
        onSuccess: (r) => {
          setElegida(parteId);
          const t = r.traidos;
          const partes = [
            t?.atributos ? `${t.atributos} ${t.atributos === 1 ? 'atributo' : 'atributos'}` : '',
            t?.aplicaciones ? `${t.aplicaciones} ${t.aplicaciones === 1 ? 'aplicación' : 'aplicaciones'}` : '',
          ].filter(Boolean);
          setHecho(
            partes.length
              ? `Vinculada. Se trajeron ${partes.join(' y ')} como sugerencias: revísalas en Ficha y Aplicaciones.`
              : 'Vinculada. El artículo ya tenía todos sus datos: no se trajo nada.',
          );
        },
      },
    );
  const lista: CandidatoParte[] | ParteCatalogo[] = buscado.length >= 2 ? (busqueda.data ?? []) : e.candidatos;

  return (
    <div className="space-y-4">
      {!e.editable && (
        <Aviso tono="info" titulo="Solo lectura">
          {e.razon_no_editable}
        </Aviso>
      )}
      {!e.catalogo_disponible && (
        <Aviso tono="info" titulo="Catálogo maestro no disponible">
          La API no tiene acceso a Consolidación: se ven las partes vinculadas por su número, pero no se puede buscar.
        </Aviso>
      )}
      {error instanceof ProblemaError && (
        <Aviso tono="error" titulo={error.problema.title}>
          {error.problema.detail}{' '}
          {error.problema.status === 409 && (
            <button type="button" className="underline" onClick={() => void q.refetch()}>
              Recargar
            </button>
          )}
        </Aviso>
      )}
      {hecho && !error && <Aviso tono="exito" titulo={hecho} />}

      {e.vinculadas.length > 0 && (
        <section className="rounded-lg border border-borde bg-superficie">
          <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
            Vinculadas ({e.vinculadas.length})
          </h2>
          <ul className="divide-y divide-borde">
            {e.vinculadas.map((v) => (
              <li key={v.parte_id} className="flex flex-wrap items-center gap-2 px-4 py-2.5">
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left text-sm"
                  onClick={() => setElegida(v.parte_id)}
                >
                  <span className="flex items-center gap-1.5 font-medium">
                    {v.es_principal && <Star className="size-4 fill-current text-por-validar" aria-label="Principal" />}
                    {v.parte?.descripcion ?? `Parte ${v.parte_id}`}
                  </span>
                  <span className="block text-xs text-suave">
                    {v.parte ? `${textoMedidas(v.parte.medidas)} mm · ` : ''}
                    {v.es_principal ? 'Principal' : 'Secundaria'} · {v.confirmado_por ?? v.origen.toLowerCase()}
                  </span>
                  {v.parte && v.parte.estado !== 'ACTIVA' && (
                    <span className="block text-xs text-rechazado">
                      {v.parte.estado === 'FUSIONADA'
                        ? `Se fusionó en la parte ${v.parte.fusionada_en_id}: vincula esa y quita esta.`
                        : 'El catálogo la descartó: quítala o vincula otra.'}
                    </span>
                  )}
                </button>
                {e.editable && (
                  <div className="flex gap-1">
                    {!v.es_principal && (
                      <Boton
                        variante="secundario"
                        className="h-8 px-2 text-xs"
                        disabled={ocupado}
                        onClick={() =>
                          principal.mutate(
                            { itemCode, data: { version: e.version, parte_id: v.parte_id }, params },
                            { onSuccess: () => setHecho('Principal cambiada.') },
                          )
                        }
                      >
                        <Star className="size-3.5" aria-hidden /> Principal
                      </Boton>
                    )}
                    <Boton
                      variante="fantasma"
                      className="h-8 px-2"
                      disabled={ocupado}
                      aria-label={`Desvincular parte ${v.parte_id}`}
                      title="Desvincular"
                      onClick={() =>
                        confirm('¿Desvincular esta parte? Sus sugerencias aún sin confirmar se quitan.') &&
                        desvincular.mutate(
                          { itemCode, data: { version: e.version, parte_id: v.parte_id }, params },
                          { onSuccess: () => (setHecho('Parte desvinculada.'), setElegida(null)) },
                        )
                      }
                    >
                      <Unlink className="size-4" aria-hidden />
                    </Boton>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {e.catalogo_disponible && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:items-start">
          <section aria-label="Candidatos" className="rounded-lg border border-borde bg-superficie">
            <div className="space-y-2 border-b border-borde p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-xs font-medium tracking-wide text-suave uppercase">
                  Candidatos del catálogo maestro
                </h2>
                <label className="flex items-center gap-1.5 text-xs text-suave">
                  <ArrowLeftRight className="size-3.5" aria-hidden /> Medidas ±
                  <select
                    aria-label="Tolerancia de medidas"
                    value={tolerancia}
                    onChange={(x) => setTolerancia(Number(x.target.value))}
                    className="h-7 rounded border border-borde bg-superficie px-1 text-xs"
                  >
                    {TOLERANCIAS.map((t) => (
                      <option key={t} value={t}>
                        {t} mm
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <p className="text-xs text-suave tabular-nums">
                {itemCode}: {textoMedidas(e.medidas)} mm · alto y largo se comparan en cualquier orden
              </p>
              <label className="relative block">
                <Search className="absolute top-2.5 left-2.5 size-4 text-suave" aria-hidden />
                <input
                  type="search"
                  aria-label="Buscar manualmente en el catálogo"
                  placeholder="Buscar: 400x518x26, número o descripción"
                  value={texto}
                  onChange={(x) => setTexto(x.target.value)}
                  className="h-9 w-full rounded-md border border-borde bg-superficie pr-2 pl-8 text-base sm:text-sm"
                />
              </label>
            </div>
            {buscado.length >= 2 && busqueda.isLoading && <p className="p-4 text-sm text-suave">Buscando…</p>}
            {lista.length === 0 && !(buscado.length >= 2 && busqueda.isLoading) && (
              <p className="p-4 text-center text-sm text-suave">
                {buscado.length >= 2
                  ? 'Nada coincide con la búsqueda.'
                  : 'Sin candidatos: prueba con más tolerancia o busca manualmente.'}
              </p>
            )}
            <ul className="divide-y divide-borde">
              {lista.map((x) =>
                'puntaje' in x ? (
                  <FilaParte
                    key={x.parte.parte_id}
                    p={x.parte}
                    puntaje={x.puntaje}
                    razones={x.razones}
                    activa={visible === x.parte.parte_id}
                    alElegir={() => setElegida(x.parte.parte_id)}
                  />
                ) : (
                  <FilaParte
                    key={x.parte_id}
                    p={x}
                    activa={visible === x.parte_id}
                    alElegir={() => setElegida(x.parte_id)}
                    extra={x.tipo_parte && <span className="block text-xs text-suave">{x.tipo_parte}</span>}
                  />
                ),
              )}
            </ul>
          </section>

          <section aria-label="Comparación" className="rounded-lg border border-borde bg-superficie">
            <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
              Comparación
            </h2>
            {visible ? (
              <Comparar
                key={visible}
                itemCode={itemCode}
                parteId={visible}
                e={e}
                ocupado={vincular.isPending}
                alVincular={(p, t) => alVincular(visible, p, t)}
              />
            ) : (
              <p className="p-4 text-sm text-suave">Elige un candidato para compararlo con el artículo.</p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
