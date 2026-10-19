import { useListarCategorias, useObtenerSaludLista } from '@nexo/api-client';
import { CircleCheck, CircleX, LoaderCircle } from 'lucide-react';

import { useFiltro } from '@/app/contexto-filtro';
import { LINEAS } from '@/app/filtro';
import { nombreCategoria } from '@/app/FiltroGlobal';

const numero = new Intl.NumberFormat('es-GT');

function Tarjeta({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-borde bg-superficie p-4">
      <h2 className="text-sm font-medium text-suave">{titulo}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function Proximamente({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <Tarjeta titulo={titulo}>
      <p className="text-sm text-suave">{texto}</p>
      <p className="mt-3 text-xs text-suave">Llega en el paso 4</p>
    </Tarjeta>
  );
}

/** Panorama del tipo de artículo elegido. En el esqueleto: activos del tipo y estado del servicio. */
export function Panorama() {
  const { filtro } = useFiltro();
  const categorias = useListarCategorias({ query: { staleTime: 60_000 } });
  const salud = useObtenerSaludLista({ query: { retry: false } });

  const categoria = categorias.data?.find((c) => c.codigo === filtro.cat);
  const linea = LINEAS.find((l) => l.valor === filtro.linea)?.nombre ?? '';
  const activos = categoria?.activos[filtro.linea];

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold">Panorama</h1>
        <p className="text-sm text-suave">
          {categoria ? `${nombreCategoria(categoria.nombre)} · ${linea}` : 'Cargando…'}
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Tarjeta titulo="Artículos activos">
          <p className="text-3xl font-semibold tabular-nums">{activos === undefined ? '—' : numero.format(activos)}</p>
        </Tarjeta>
        <Tarjeta titulo="Servicio">
          {salud.isPending ? (
            <p className="flex items-center gap-2 text-sm text-suave">
              <LoaderCircle className="size-4 animate-spin" aria-hidden /> Comprobando…
            </p>
          ) : salud.isSuccess ? (
            <p className="flex items-center gap-2 text-sm">
              <CircleCheck className="size-4 text-validado" aria-hidden /> Base disponible · migración{' '}
              {salud.data.migracion}
            </p>
          ) : (
            <p className="flex items-center gap-2 text-sm">
              <CircleX className="size-4 text-rechazado" aria-hidden /> Base no disponible
            </p>
          )}
        </Tarjeta>
        <Proximamente titulo="Avance por estado" texto="Pendiente, por validar, rechazado, validado y sincronizado." />
        <Proximamente titulo="Atención" texto="Verificaciones abiertas, hallazgos de SAP y reservas por vencer." />
        <Proximamente titulo="Completitud de la ficha" texto="Atributos sugeridos desde SAP frente a confirmados." />
        <Proximamente titulo="Cobertura" texto="Artículos con foto, emparejados y con aplicación." />
        <Proximamente titulo="Prioridad por venta" texto="Clase ABC, participación y tendencia (sin montos)." />
        <Proximamente titulo="Productividad" texto="Enviados y rechazados por operador en los últimos 7 días." />
      </div>
    </div>
  );
}
