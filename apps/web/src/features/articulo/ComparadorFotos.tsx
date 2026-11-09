import { useCompararParte, useListarFotos, type Emparejamiento as RespuestaEmparejamiento } from '@nexo/api-client';
import { Check, ChevronLeft, ChevronRight, ExternalLink, ImageOff, Link2, Star, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import { cn } from '@/shared/cn';
import { Boton, Dialogo, Insignia } from '@/shared/ui';

const MEDIDAS = [267, 269, 268]; // alto, largo, ancho del panal

interface Imagen {
  url: string;
  etiqueta: string;
}

/** Una imagen grande sobre fondo blanco, con miniaturas para cambiar y enlace para abrirla aparte. */
function Visor({
  titulo,
  detalle,
  imagenes,
  cargando,
}: {
  titulo: string;
  detalle?: string;
  imagenes: Imagen[];
  cargando: boolean;
}) {
  const [i, setI] = useState(0);
  const [rotas, setRotas] = useState<Set<string>>(new Set());
  const actual = imagenes[Math.min(i, imagenes.length - 1)];
  return (
    <section aria-label={titulo} className="flex min-h-0 flex-col gap-2">
      <header className="min-h-10">
        <h3 className="truncate font-semibold">{titulo}</h3>
        {detalle && <p className="truncate text-sm text-suave">{detalle}</p>}
      </header>
      <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-lg border border-borde bg-white">
        {cargando ? (
          <span className="text-sm text-suave">Cargando…</span>
        ) : actual && rotas.has(actual.url) ? (
          <span className="flex flex-col items-center gap-1 px-4 text-center text-sm text-suave">
            <ImageOff className="size-8" aria-hidden /> No se pudo cargar la imagen
            <span className="text-xs">El enlace del proveedor puede haber caducado: ábrela aparte para revisarla.</span>
          </span>
        ) : actual ? (
          <img
            src={actual.url}
            alt={actual.etiqueta}
            onError={() => setRotas((r) => new Set(r).add(actual.url))}
            className="size-full object-contain"
          />
        ) : (
          <span className="flex flex-col items-center gap-1 text-sm text-suave">
            <ImageOff className="size-8" aria-hidden /> Sin imágenes
          </span>
        )}
        {actual && (
          <span className="absolute top-2 left-2 rounded bg-black/60 px-1.5 py-0.5 text-xs text-white">
            {actual.etiqueta} · {Math.min(i, imagenes.length - 1) + 1}/{imagenes.length}
          </span>
        )}
        {actual && (
          <a
            href={actual.url}
            target="_blank"
            rel="noreferrer"
            className="absolute top-2 right-2 grid size-8 place-items-center rounded bg-black/60 text-white hover:bg-black/80"
            aria-label="Abrir la imagen en otra pestaña"
            title="Abrir en otra pestaña"
          >
            <ExternalLink className="size-4" aria-hidden />
          </a>
        )}
      </div>
      {imagenes.length > 1 && (
        <ul className="flex gap-2 overflow-x-auto pb-1">
          {imagenes.map((m, k) => (
            <li key={m.url} className="shrink-0">
              <button
                type="button"
                onClick={() => setI(k)}
                aria-label={`Ver ${m.etiqueta} ${k + 1}`}
                aria-pressed={k === Math.min(i, imagenes.length - 1)}
                className="overflow-hidden rounded-md border-2 border-transparent bg-white aria-pressed:border-primario"
              >
                <img src={m.url} alt="" loading="lazy" className="h-14 w-20 object-contain" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Comparar fotos (ADR 0027): las del artículo a la izquierda y las del candidato a la derecha, en grande, con las medidas en el
 * medio. Se recorren los candidatos sin cerrar (botones o flechas del teclado) y se vincula desde aquí.
 */
export function ComparadorFotos({
  itemCode,
  e,
  ids,
  inicial,
  abierto,
  ocupado,
  alCerrar,
  alCambiar,
  alVincular,
}: {
  itemCode: string;
  e: RespuestaEmparejamiento;
  ids: number[]; // candidatos en el orden de la lista
  inicial: number;
  abierto: boolean;
  ocupado: boolean;
  alCerrar: () => void;
  alCambiar: (parteId: number) => void; // para que la lista quede en el mismo candidato
  alVincular: (parteId: number, principal: boolean, traer: boolean) => void;
}) {
  const [actual, setActual] = useState(inicial);
  const [traer, setTraer] = useState(true);
  const pos = ids.indexOf(actual);
  const fotos = useListarFotos(itemCode, { query: { enabled: abierto } });
  const q = useCompararParte(itemCode, actual, { tolerancia: e.tolerancia }, { query: { enabled: abierto } });
  const c = q.data;

  const ir = (d: number) => {
    if (pos < 0 || !ids.length) return;
    const otro = ids[(pos + d + ids.length) % ids.length];
    if (otro === undefined) return;
    setActual(otro);
    alCambiar(otro);
  };
  // Flechas del teclado: candidato anterior / siguiente
  useEffect(() => {
    if (!abierto) return;
    const tecla = (x: KeyboardEvent) => {
      if ((x.target as HTMLElement)?.tagName === 'INPUT') return;
      if (x.key === 'ArrowRight') ir(1);
      if (x.key === 'ArrowLeft') ir(-1);
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  });

  const propias: Imagen[] = [
    ...(fotos.data?.propias ?? []).filter((f) => f.url).map((f) => ({ url: f.url as string, etiqueta: 'Foto propia' })),
  ];
  const delCandidato: Imagen[] = (c?.imagenes ?? []).map((m) => ({
    url: m.url,
    etiqueta: m.tipo === 'DIAGRAMA' ? 'Diagrama' : m.tipo === 'DIBUJO_TECNICO' ? 'Dibujo técnico' : 'Foto',
  }));
  const medidas = (c?.filas ?? []).filter((f) => MEDIDAS.includes(f.paid));
  const puedeVincular = e.editable && c && !c.vinculada && c.parte.estado === 'ACTIVA';

  return (
    <Dialogo
      abierto={abierto}
      alCerrar={alCerrar}
      titulo="Comparar fotos"
      amplio
      pie={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Boton variante="secundario" disabled={ids.length < 2} onClick={() => ir(-1)} title="Anterior (←)">
              <ChevronLeft className="size-4" aria-hidden /> Anterior
            </Boton>
            <span className="text-sm text-suave tabular-nums">{pos >= 0 ? `${pos + 1} de ${ids.length}` : ''}</span>
            <Boton variante="secundario" disabled={ids.length < 2} onClick={() => ir(1)} title="Siguiente (→)">
              Siguiente <ChevronRight className="size-4" aria-hidden />
            </Boton>
          </div>
          {c && !e.editable && !c.vinculada && (
            <span className="text-sm text-suave">{e.razon_no_editable ?? 'Toma el artículo para vincular.'}</span>
          )}
          {c?.vinculada ? (
            <span className="flex items-center gap-1 text-sm text-validado">
              <Check className="size-4" aria-hidden /> Ya está vinculada a {itemCode}
            </span>
          ) : (
            puedeVincular && (
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="size-4"
                    checked={traer}
                    onChange={(x) => setTraer(x.target.checked)}
                  />
                  Traer atributos y aplicaciones como sugerencias
                </label>
                <Boton variante="secundario" disabled={ocupado} onClick={() => alVincular(actual, false, traer)}>
                  <Link2 className="size-4" aria-hidden /> Vincular
                </Boton>
                <Boton cargando={ocupado} onClick={() => alVincular(actual, true, traer)}>
                  <Star className="size-4" aria-hidden /> Vincular como principal
                </Boton>
              </div>
            )
          )}
        </div>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_14rem_minmax(0,1fr)]">
        <Visor titulo={`Artículo ${itemCode}`} detalle="Fotos propias" imagenes={propias} cargando={fotos.isLoading} />

        {/* En medio: lo que se compara, para decidir sin cambiar de pantalla */}
        <aside aria-label="Medidas y coincidencias" className="space-y-3 self-center text-sm lg:pt-10">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-suave">
                <th className="font-normal">mm</th>
                <th className="font-normal">Artículo</th>
                <th className="font-normal">Candidato</th>
              </tr>
            </thead>
            <tbody>
              {medidas.map((f) => (
                <tr key={f.paid} className={cn(f.coincide === false && 'text-rechazado')}>
                  <td className="py-1 text-suave">{f.etiqueta}</td>
                  <td className="py-1 tabular-nums">{f.articulo ?? '—'}</td>
                  <td className="py-1 tabular-nums">
                    <span className="flex items-center gap-1">
                      {f.parte ?? '—'}
                      {f.coincide === true && <Check className="size-3.5 text-validado" aria-label="Coincide" />}
                      {f.coincide === false && <X className="size-3.5" aria-label="No coincide" />}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {c?.invertida && <p className="text-xs text-por-validar">Alto y largo vienen invertidos en el catálogo.</p>}
          {c && c.vehiculos_comunes > 0 && (
            <Insignia className="text-validado">{c.vehiculos_comunes} vehículos en común</Insignia>
          )}
          {c && c.numeros.length > 0 && (
            <p className="text-xs text-suave">
              {c.numeros
                .slice(0, 4)
                .map((x) => `${x.tipo} ${x.numero}`)
                .join(' · ')}
              {c.numeros.length > 4 && ` · +${c.numeros.length - 4}`}
            </p>
          )}
        </aside>

        <Visor
          key={actual}
          titulo={c?.parte.descripcion ?? `Parte ${actual}`}
          detalle={c ? `Parte ${c.parte.parte_id} · ${c.fuentes.map((f) => f.fuente).join(', ')}` : undefined}
          imagenes={delCandidato}
          cargando={q.isLoading}
        />
      </div>
    </Dialogo>
  );
}
