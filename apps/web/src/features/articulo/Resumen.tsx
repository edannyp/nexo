import {
  useListarAplicaciones,
  useListarFotos,
  useObtenerFicha,
  type ArticuloDetalle,
  type AtributoFicha,
} from '@nexo/api-client';
import { ChevronLeft, ChevronRight, ImageOff, Star, TriangleAlert } from 'lucide-react';
import { useState } from 'react';

import { cn } from '@/shared/cn';
import { Insignia } from '@/shared/ui';

import { mostrar } from './Ficha';

/** Pestañas del modo Trabajar a las que se puede saltar desde el resumen. */
export type PestanaTrabajo = 'ficha' | 'aplicaciones' | 'emparejamiento' | 'equivalencia' | 'fotos';

const MEDIDAS = [267, 269, 268]; // alto, largo, ancho del panal (PAdb)

const tarjeta = 'rounded-lg border border-borde bg-superficie p-4';
const titulo = 'mb-2 text-xs font-medium tracking-wide text-suave uppercase';

/** Fotos propias primero y luego las del catálogo maestro, de una en una. */
function Carrusel({ itemCode }: { itemCode: string }) {
  const q = useListarFotos(itemCode);
  const [i, setI] = useState(0);
  const fotos = [
    ...(q.data?.propias ?? []).filter((f) => f.url).map((f) => ({ url: f.url as string, origen: 'Propia' })),
    ...(q.data?.proveedor ?? []).map((f) => ({ url: f.url, origen: 'Catálogo maestro' })),
  ];
  const actual = fotos[Math.min(i, fotos.length - 1)];
  const mover = (d: number) => setI((x) => (x + d + fotos.length) % fotos.length);

  return (
    <section aria-label="Fotos" className={cn(tarjeta, 'p-2')}>
      <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-md bg-superficie-2">
        {q.isLoading ? (
          <span className="text-sm text-suave">Cargando fotos…</span>
        ) : actual ? (
          <img src={actual.url} alt={`Foto ${i + 1} de ${fotos.length}`} className="size-full object-contain" />
        ) : (
          <span className="flex flex-col items-center gap-1 text-sm text-suave">
            <ImageOff className="size-6" aria-hidden /> Sin fotos todavía
          </span>
        )}
        {fotos.length > 1 && (
          <>
            <button
              type="button"
              aria-label="Foto anterior"
              onClick={() => mover(-1)}
              className="absolute top-1/2 left-1 -translate-y-1/2 rounded-full bg-fondo/80 p-1.5 hover:bg-fondo"
            >
              <ChevronLeft className="size-5" aria-hidden />
            </button>
            <button
              type="button"
              aria-label="Foto siguiente"
              onClick={() => mover(1)}
              className="absolute top-1/2 right-1 -translate-y-1/2 rounded-full bg-fondo/80 p-1.5 hover:bg-fondo"
            >
              <ChevronRight className="size-5" aria-hidden />
            </button>
          </>
        )}
      </div>
      {actual && (
        <p className="mt-1.5 flex justify-between px-1 text-xs text-suave tabular-nums">
          <span>{actual.origen}</span>
          <span>
            {Math.min(i, fotos.length - 1) + 1} / {fotos.length}
          </span>
        </p>
      )}
    </section>
  );
}

function Descripciones({ a }: { a: ArticuloDetalle }) {
  return (
    <section className={tarjeta}>
      <h2 className={titulo}>Descripción</h2>
      {a.descripcion_nexo ? (
        <p className="text-base font-semibold">
          {a.descripcion_nexo}
          <Insignia className="ml-2 align-middle font-normal">
            {a.descripcion_nexo_manual ? 'ajustada' : 'automática'}
          </Insignia>
        </p>
      ) : (
        <p className="text-sm text-suave">Nexo la arma cuando el artículo tenga su vehículo principal.</p>
      )}
      <p className="mt-2 text-sm">
        <span className="text-suave">SAP: </span>
        {a.descripcion ?? '—'}
      </p>
    </section>
  );
}

function VehiculoPrincipal({ itemCode, alIr }: { itemCode: string; alIr?: (p: PestanaTrabajo) => void }) {
  const q = useListarAplicaciones(itemCode);
  const grupos = q.data?.grupos ?? [];
  const principal = grupos.find((g) => g.principal);
  const otras = grupos.filter((g) => !g.principal);
  return (
    <section className={tarjeta}>
      <h2 className={cn(titulo, 'flex items-center gap-1')}>
        <Star className="size-3.5" aria-hidden /> Vehículo principal (ACES)
      </h2>
      {q.isLoading ? (
        <p className="text-sm text-suave">Cargando…</p>
      ) : principal ? (
        <>
          <p className="font-medium">
            {principal.titulo} <span className="text-suave tabular-nums">{principal.anios}</span>
          </p>
          <p className="text-sm text-suave">{principal.detalle}</p>
          {principal.sugeridos > 0 && <p className="text-xs text-por-validar">Falta confirmarlo</p>}
        </>
      ) : (
        <p className="text-sm text-suave">Todavía no tiene vehículo principal.</p>
      )}
      {(otras.length > 0 || alIr) && (
        <p className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm text-suave">
          <span>
            {otras.length
              ? `${otras.length} aplicación${otras.length > 1 ? 'es' : ''} adicional${otras.length > 1 ? 'es' : ''}`
              : ''}
          </span>
          {alIr && (
            <button type="button" className="underline hover:text-texto" onClick={() => alIr('aplicaciones')}>
              Ver aplicaciones
            </button>
          )}
        </p>
      )}
    </section>
  );
}

function Atributos({ itemCode, alIr }: { itemCode: string; alIr?: (p: PestanaTrabajo) => void }) {
  const q = useObtenerFicha(itemCode);
  const atributos = q.data?.atributos ?? [];
  const confirmados = atributos.filter((x) => x.confirmado && x.valor);
  const medida = (paid: number) => atributos.find((x) => x.paid === paid);
  const otros = confirmados.filter((x) => !MEDIDAS.includes(x.paid)).slice(0, 8);
  const valor = (x?: AtributoFicha) => (x?.valor ? mostrar(x, x.valor) : x?.valor_sap ? `${x.valor_sap} (SAP)` : '—');

  return (
    <section className={tarjeta}>
      <h2 className={titulo}>Medidas del panal</h2>
      <dl className="grid grid-cols-3 gap-2 text-sm">
        {MEDIDAS.map((paid) => {
          const x = medida(paid);
          return (
            <div key={paid}>
              <dt className="text-xs text-suave">{x?.etiqueta ?? paid}</dt>
              <dd className={cn('tabular-nums', !x?.confirmado && 'text-suave')}>{valor(x)}</dd>
            </div>
          );
        })}
      </dl>
      <h2 className={cn(titulo, 'mt-4')}>Atributos confirmados</h2>
      {otros.length ? (
        <dl className="grid grid-cols-[minmax(7rem,auto)_1fr] gap-x-3 gap-y-1 text-sm">
          {otros.map((x) => (
            <div key={x.paid} className="contents">
              <dt className="text-suave">{x.etiqueta}</dt>
              <dd>{mostrar(x, x.valor)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="text-sm text-suave">Ninguno todavía.</p>
      )}
      <p className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-suave">
        <span>
          {confirmados.length} de {atributos.length} confirmados
        </span>
        {alIr && (
          <button type="button" className="underline hover:text-texto" onClick={() => alIr('ficha')}>
            Ver ficha completa
          </button>
        )}
      </p>
    </section>
  );
}

/**
 * Resumen del artículo (ADR 0027): lo que es y en qué va, de solo lectura. Editar se hace en el modo Trabajar.
 * `alIr` lleva a una pestaña de trabajo (solo si el usuario puede trabajarlo).
 */
export function Resumen({ a, alIr }: { a: ArticuloDetalle; alIr?: (p: PestanaTrabajo) => void }) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div className="space-y-4">
        <Carrusel itemCode={a.item_code} />
        {a.requisitos.length > 0 && (
          <section className={tarjeta}>
            <h2 className={titulo}>Para enviar a revisión falta</h2>
            <ul className="flex flex-wrap gap-1.5 text-xs">
              {a.requisitos.map((r) => (
                <li key={r.codigo}>
                  {alIr ? (
                    <button
                      type="button"
                      onClick={() => alIr(r.pestana as PestanaTrabajo)}
                      className="rounded-full border border-borde px-2 py-0.5 hover:bg-superficie-2"
                    >
                      {r.etiqueta}
                    </button>
                  ) : (
                    <span className="rounded-full border border-borde px-2 py-0.5">{r.etiqueta}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
        {a.hallazgos.length > 0 && (
          <p className="flex items-center gap-2 rounded-md border border-rechazado/40 bg-rechazado/10 px-3 py-2 text-sm">
            <TriangleAlert className="size-4 shrink-0 text-rechazado" aria-hidden />
            {a.hallazgos.length} hallazgo{a.hallazgos.length > 1 && 's'} para corregir en SAP (ver Datos SAP)
          </p>
        )}
      </div>
      <div className="space-y-4">
        <Descripciones a={a} />
        <VehiculoPrincipal itemCode={a.item_code} alIr={alIr} />
        <Atributos itemCode={a.item_code} alIr={alIr} />
      </div>
    </div>
  );
}
