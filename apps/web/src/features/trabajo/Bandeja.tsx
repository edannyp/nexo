import { ProblemaError, useListarArticulos, useTomarSiguiente, type Bandeja as TipoBandeja } from '@nexo/api-client';
import { Link, useNavigate } from '@tanstack/react-router';
import { CheckCheck, Lock, Play } from 'lucide-react';
import { useEffect } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { EtiquetaEstado } from '@/shared/estados';
import { numero } from '@/shared/formato';
import { atajoSimple } from '@/shared/teclado';
import { Aviso, Boton } from '@/shared/ui';

const TEXTOS: Record<
  TipoBandeja,
  { titulo: string; descripcion: string; estados: ('PENDIENTE' | 'RECHAZADO' | 'POR_VALIDAR')[] }
> = {
  operador: {
    titulo: 'Trabajar',
    descripcion:
      'Pulsa «Siguiente» y Nexo te asigna el próximo artículo: primero los rechazados, luego los que más venden.',
    estados: ['PENDIENTE', 'RECHAZADO'],
  },
  supervisor: {
    titulo: 'Validar',
    descripcion: 'Revisa lo que enviaron los operadores. Nunca te tocará algo que tú enviaste a revisión.',
    estados: ['POR_VALIDAR'],
  },
};

/** Bandeja con "Siguiente" (propuesta UX §6.3 y §6.5). La tecla N toma el siguiente. */
export function Bandeja({ bandeja }: { bandeja: TipoBandeja }) {
  const { filtro } = useFiltro();
  const navegar = useNavigate();
  const t = TEXTOS[bandeja];
  const pendientes = useListarArticulos({ ...filtro, estado: t.estados, reserva: 'libre', limit: 1 });
  const mias = useListarArticulos({ ...filtro, estado: t.estados, reserva: 'mia', limit: 20 });
  const siguiente = useTomarSiguiente();

  const tomar = () =>
    siguiente.mutate(
      { bandeja, params: filtro },
      {
        onSuccess: (r) =>
          r.articulo &&
          void navegar({
            to: '/articulos/$itemCode',
            params: { itemCode: r.articulo.item_code },
            search: (p) => ({ ...p, bandeja }),
          }),
      },
    );

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (!atajoSimple(e)) return;
      if (e.key === 'n' || e.key === 'N') tomar();
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtro.cat, filtro.linea]);

  // Vacía si no hay disponibles (al llegar o tras terminar el último) o si «Siguiente» no encontró nada
  const vacia = pendientes.data?.total === 0 || (siguiente.data && !siguiente.data.articulo);
  const Icono = bandeja === 'supervisor' ? CheckCheck : Play;

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-4">
      <header>
        <h1 className="text-xl font-semibold">{t.titulo}</h1>
        <p className="text-sm text-suave">{t.descripcion}</p>
      </header>

      <section className="rounded-lg border border-borde bg-superficie p-6 text-center">
        <p className="text-sm text-suave">Disponibles en esta bandeja</p>
        <p className="mt-1 text-5xl font-semibold">{pendientes.data ? numero(pendientes.data.total) : '—'}</p>
        <div className="mt-2 flex justify-center gap-3 text-sm text-suave">
          {t.estados.map((e) => (
            <EtiquetaEstado key={e} estado={e} />
          ))}
        </div>
        <Boton
          className="mt-5 h-12 px-8 text-base"
          onClick={tomar}
          cargando={siguiente.isPending}
          disabled={pendientes.data?.total === 0}
        >
          <Icono className="size-5" aria-hidden /> Siguiente{' '}
          <kbd className="ml-1 rounded border border-current/40 px-1.5 text-xs">N</kbd>
        </Boton>
        {vacia && (
          <div className="mt-4">
            <Aviso tono="exito" titulo="No hay más artículos en esta bandeja">
              Cambia el tipo de artículo arriba o revisa más tarde.
            </Aviso>
          </div>
        )}
        {siguiente.error instanceof ProblemaError && (
          <div className="mt-4">
            <Aviso tono="error" titulo={siguiente.error.problema.title} />
          </div>
        )}
      </section>

      {!!mias.data?.items.length && (
        <section className="rounded-lg border border-borde bg-superficie p-4">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-suave">
            <Lock className="size-4" aria-hidden /> Reservados por ti
          </h2>
          <ul className="divide-y divide-borde">
            {mias.data.items.map((a) => (
              <li key={a.id}>
                <Link
                  to="/articulos/$itemCode"
                  params={{ itemCode: a.item_code }}
                  search={(p) => ({ ...p, bandeja })}
                  className="flex items-center justify-between gap-3 py-2 text-sm hover:bg-superficie-2"
                >
                  <span>
                    <span className="font-medium">{a.item_code}</span>
                    <span className="block max-w-md truncate text-suave">{a.descripcion}</span>
                  </span>
                  <EtiquetaEstado estado={a.estado} />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
