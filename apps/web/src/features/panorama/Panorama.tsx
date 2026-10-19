import { useListarCategorias, useObtenerPanorama, type Panorama as DatosPanorama } from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { Clock, ShieldAlert, TriangleAlert } from 'lucide-react';
import type { ReactNode } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { useUsuario } from '@/app/contexto-usuario';
import { LINEAS } from '@/app/filtro';
import { nombreCategoria } from '@/app/FiltroGlobal';
import { rutaSeccion } from '@/app/navegacion';
import { tieneRol } from '@/app/sesion';
import { cn } from '@/shared/cn';
import { EtiquetaEstado, IconoEstado, ORDEN_ESTADOS } from '@/shared/estados';
import { fraccion, momento, numero, porcentaje } from '@/shared/formato';
import { BarraApilada, FilaBarra, Leyenda, Medidor, Tendencia } from '@/shared/graficos';
import { Aviso } from '@/shared/ui';

function Bloque({ titulo, children, className }: { titulo: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn('min-w-0 rounded-lg border border-borde bg-superficie p-4', className)} aria-label={titulo}>
      <h2 className="mb-3 text-sm font-medium text-suave">{titulo}</h2>
      {children}
    </section>
  );
}

function Cifra({ etiqueta, valor, detalle }: { etiqueta: string; valor: string; detalle?: string }) {
  return (
    <div className="rounded-lg border border-borde bg-superficie p-4">
      <p className="text-sm text-suave">{etiqueta}</p>
      <p className="mt-1 text-3xl font-semibold">{valor}</p>
      {detalle && <p className="mt-1 text-xs text-suave">{detalle}</p>}
    </div>
  );
}

function Avance({ d }: { d: DatosPanorama }) {
  const maximo = Math.max(...ORDEN_ESTADOS.map((e) => d.por_estado[e] ?? 0));
  return (
    <Bloque titulo="Avance por estado">
      <div className="space-y-2.5">
        {ORDEN_ESTADOS.map((e) => (
          <FilaBarra
            key={e}
            etiqueta={<EtiquetaEstado estado={e} />}
            valor={d.por_estado[e] ?? 0}
            maximo={maximo}
            texto={`${numero(d.por_estado[e] ?? 0)} · ${porcentaje(fraccion(d.por_estado[e] ?? 0, d.activos), 0)}`}
          />
        ))}
      </div>
    </Bloque>
  );
}

function Completitud({ d }: { d: DatosPanorama }) {
  return (
    <Bloque titulo="Completitud de la ficha (atributos obligatorios)">
      <Leyenda
        items={[
          { etiqueta: 'Confirmado', clase: 'bg-viz-confirmado' },
          { etiqueta: 'Sugerido (falta confirmar)', clase: 'bg-viz-sugerido' },
          { etiqueta: 'Sin dato', clase: 'bg-borde' },
        ]}
      />
      <div className="mt-3 space-y-2.5">
        {d.ficha.atributos.map((a) => (
          <div key={a.paid} className="grid grid-cols-[minmax(6rem,8.5rem)_1fr_auto] items-center gap-3 text-sm">
            <span className="truncate">{a.etiqueta}</span>
            <BarraApilada
              etiqueta={a.etiqueta}
              total={d.activos}
              segmentos={[
                { etiqueta: 'Confirmado', valor: a.confirmados, clase: 'bg-viz-confirmado' },
                { etiqueta: 'Sugerido', valor: a.sugeridos, clase: 'bg-viz-sugerido' },
              ]}
            />
            <span className="w-24 text-right text-xs text-suave tabular-nums">
              {numero(a.confirmados)} · {numero(a.sugeridos)} sug.
            </span>
          </div>
        ))}
        {d.ficha.atributos.length === 0 && (
          <p className="text-sm text-suave">Este tipo de parte aún no tiene atributos obligatorios configurados.</p>
        )}
      </div>
      <p className="mt-3 text-sm">
        <span className="font-medium">{numero(d.ficha.completos)}</span>{' '}
        <span className="text-suave">
          artículos con la ficha completa ({porcentaje(fraccion(d.ficha.completos, d.activos), 0)})
        </span>
      </p>
    </Bloque>
  );
}

function Cobertura({ d }: { d: DatosPanorama }) {
  return (
    <Bloque titulo="Cobertura">
      <div className="space-y-4">
        <Medidor etiqueta="Con foto propia" valor={d.cobertura.con_foto} total={d.activos} />
        <Medidor etiqueta="Emparejados con el catálogo" valor={d.cobertura.emparejados} total={d.activos} />
        <Medidor etiqueta="Con aplicación confirmada" valor={d.cobertura.con_aplicacion} total={d.activos} />
      </div>
      <p className="mt-3 text-xs text-suave">{numero(d.cobertura.fotos)} fotos propias en total</p>
    </Bloque>
  );
}

function Atencion({ d, verCalidad }: { d: DatosPanorama; verCalidad: boolean }) {
  const items = [
    { icono: <IconoEstado estado="RECHAZADO" />, texto: 'Rechazados por corregir', n: d.atencion.rechazados },
    {
      icono: <ShieldAlert className="size-4 text-por-validar" aria-hidden />,
      texto: 'Verificaciones abiertas',
      n: d.atencion.verificaciones_abiertas,
    },
    {
      icono: <TriangleAlert className="size-4 text-rechazado" aria-hidden />,
      texto: 'Hallazgos para corregir en SAP',
      n: d.atencion.hallazgos_sap,
      enlace: verCalidad,
    },
    { icono: <Clock className="size-4 text-suave" aria-hidden />, texto: 'Reservados ahora', n: d.atencion.reservados },
    {
      icono: <Clock className="size-4 text-rechazado" aria-hidden />,
      texto: 'Reservas por vencer (5 min)',
      n: d.atencion.reservas_por_vencer,
    },
  ];
  return (
    <Bloque titulo="Atención">
      <ul className="divide-y divide-borde">
        {items.map((i) => (
          <li key={i.texto} className="flex items-center gap-3 py-2 text-sm">
            {i.icono}
            {i.enlace ? (
              <Link to={rutaSeccion('/calidad-sap')} className="flex-1 underline-offset-2 hover:underline">
                {i.texto}
              </Link>
            ) : (
              <span className="flex-1">{i.texto}</span>
            )}
            <span className={cn('tabular-nums', i.n > 0 ? 'font-medium' : 'text-suave')}>{numero(i.n)}</span>
          </li>
        ))}
      </ul>
    </Bloque>
  );
}

function Ventas({ d }: { d: DatosPanorama }) {
  const v = d.ventas;
  if (!v.disponible) {
    return (
      <Bloque titulo="Prioridad por venta">
        <p className="text-sm text-suave">Las ventas aún no se han cargado (tarea «actualizar-ventas»).</p>
      </Bloque>
    );
  }
  const maximo = Math.max(...v.por_clase.map((c) => Number(c.participacion)), 0);
  return (
    <Bloque titulo={`Prioridad por venta · unidades de los últimos ${v.meses} meses`} className="lg:col-span-2">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div>
          <p className="mb-2 text-xs text-suave">Participación en las unidades vendidas del tipo</p>
          <div className="space-y-2.5">
            {v.por_clase.map((c) => (
              <FilaBarra
                key={c.clase}
                etiqueta={`Clase ${c.clase} · ${numero(c.articulos)} art.`}
                valor={Number(c.participacion)}
                maximo={maximo}
                texto={porcentaje(c.participacion, 0)}
              />
            ))}
            <p className="text-sm text-suave">{numero(v.sin_venta)} artículos sin venta en el periodo</p>
          </div>
          {v.actualizado_en && <p className="mt-3 text-xs text-suave">Actualizado: {momento(v.actualizado_en)}</p>}
        </div>
        <div className="min-w-0">
          <p className="mb-2 text-xs text-suave">Los que más venden y aún no están validados</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-suave">
                <tr>
                  <th className="py-1.5 pr-2 font-medium">Artículo</th>
                  <th className="py-1.5 pr-2 font-medium">Estado</th>
                  <th className="py-1.5 pr-2 text-right font-medium">Clase</th>
                  <th className="py-1.5 pr-2 text-right font-medium">Part.</th>
                  <th className="py-1.5 text-right font-medium">Tendencia</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {v.prioridad.map((p) => (
                  <tr key={p.articulo_id} className="border-t border-borde">
                    <td className="py-1.5 pr-2">
                      <span className="font-medium">{p.item_code}</span>
                      <span className="block max-w-72 truncate text-xs text-suave">{p.descripcion}</span>
                    </td>
                    <td className="py-1.5 pr-2">
                      <EtiquetaEstado estado={p.estado} />
                    </td>
                    <td className="py-1.5 pr-2 text-right">{p.clase}</td>
                    <td className="py-1.5 pr-2 text-right">{porcentaje(p.participacion)}</td>
                    <td className="py-1.5 text-right">
                      <Tendencia valor={p.tendencia} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Bloque>
  );
}

function Productividad({ d }: { d: DatosPanorama }) {
  return (
    <Bloque titulo="Productividad · últimos 7 días">
      {d.productividad.length === 0 ? (
        <p className="text-sm text-suave">Sin movimientos en los últimos 7 días.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-suave">
            <tr>
              <th className="py-1.5 font-medium">Usuario</th>
              <th className="py-1.5 text-right font-medium">Enviados</th>
              <th className="py-1.5 text-right font-medium">Validados</th>
              <th className="py-1.5 text-right font-medium">Rechazados</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {d.productividad.map((p) => (
              <tr key={p.usuario_id} className="border-t border-borde">
                <td className="py-1.5">{p.nombre}</td>
                <td className="py-1.5 text-right">{numero(p.enviados)}</td>
                <td className="py-1.5 text-right">{numero(p.validados)}</td>
                <td className="py-1.5 text-right">{numero(p.rechazados)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Bloque>
  );
}

/** Panorama del tipo de artículo del filtro global (architecture/ux/propuesta.md §6.1). */
export function Panorama() {
  const { filtro } = useFiltro();
  const usuario = useUsuario();
  const q = useObtenerPanorama(filtro, { query: { placeholderData: (previo) => previo } });
  const categorias = useListarCategorias({ query: { staleTime: 60_000 } });
  const categoria = categorias.data?.find((c) => c.codigo === filtro.cat);
  const linea = LINEAS.find((l) => l.valor === filtro.linea)?.nombre ?? '';
  const d = q.data;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold">Panorama</h1>
        <p className="text-sm text-suave">{categoria ? `${nombreCategoria(categoria.nombre)} · ${linea}` : linea}</p>
      </header>

      {q.isError && (
        <Aviso tono="error" titulo="No se pudo cargar el panorama">
          {q.error.problema.detail}
        </Aviso>
      )}
      {!d && q.isPending && <p className="text-sm text-suave">Cargando…</p>}

      {d && (
        // Al cambiar el filtro se conserva el panorama anterior atenuado (sin parpadeo) hasta que llega el nuevo
        <div
          className={cn('space-y-4 transition-opacity', q.isPlaceholderData && 'opacity-60')}
          aria-busy={q.isFetching}
        >
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Cifra etiqueta="Artículos activos" valor={numero(d.activos)} />
            <Cifra
              etiqueta="Validados"
              valor={porcentaje(
                fraccion((d.por_estado.VALIDADO ?? 0) + (d.por_estado.SINCRONIZADO ?? 0), d.activos),
                0,
              )}
              detalle={`${numero((d.por_estado.VALIDADO ?? 0) + (d.por_estado.SINCRONIZADO ?? 0))} de ${numero(d.activos)}`}
            />
            <Cifra
              etiqueta="Ficha completa"
              valor={porcentaje(fraccion(d.ficha.completos, d.activos), 0)}
              detalle={`${numero(d.ficha.completos)} artículos`}
            />
            <Cifra
              etiqueta="Con foto propia"
              valor={porcentaje(fraccion(d.cobertura.con_foto, d.activos), 0)}
              detalle={`${numero(d.cobertura.fotos)} fotos`}
            />
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Avance d={d} />
            <Atencion d={d} verCalidad={tieneRol(usuario, ['SUPERVISOR', 'ADMINISTRADOR'])} />
            <Completitud d={d} />
            <Cobertura d={d} />
            <Ventas d={d} />
            <Productividad d={d} />
          </div>
        </div>
      )}
    </div>
  );
}
