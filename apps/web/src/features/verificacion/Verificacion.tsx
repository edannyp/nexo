import {
  ProblemaError,
  useCrearVerificacion,
  useGenerarMuestreo,
  useListarVerificaciones,
  useResolverVerificacion,
  type Estado,
  type OrigenTarea,
  type TareaVerificacion,
} from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { Check, Dices, Plus, TriangleAlert } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { useUsuario } from '@/app/contexto-usuario';
import { cn } from '@/shared/cn';
import { EtiquetaEstado } from '@/shared/estados';
import { momento } from '@/shared/formato';
import { Aviso, Boton, Campo, Dialogo, Insignia } from '@/shared/ui';

const ORIGENES: Record<OrigenTarea, string> = {
  NUEVA_FOTO: 'Foto nueva',
  MUESTREO: 'Muestreo',
  CAMBIO_CATALOGO: 'Cambio en el catálogo',
  MANUAL: 'Manual',
};

const n = (x?: string | null) => (x == null ? '—' : String(Number(x)));

/** Qué hay que revisar, en palabras, según el origen de la tarea. */
export function queRevisar(t: Pick<TareaVerificacion, 'origen' | 'detalle'>): string {
  const d = t.detalle as Record<string, string | number | null>;
  switch (t.origen) {
    case 'NUEVA_FOTO':
      return 'Revisa que la foto sea de este artículo y coincida con la ficha validada.';
    case 'MUESTREO':
      return 'Control de calidad al azar: revisa ficha, aplicaciones y emparejamiento.';
    case 'CAMBIO_CATALOGO':
      return d.estado === 'FUSIONADA'
        ? `La parte ${d.parte_id} se fusionó en la ${d.fusionada_en_id}: confirma que el emparejamiento sigue siendo correcto.`
        : d.estado === 'DESCARTADA'
          ? `El catálogo descartó la parte ${d.parte_id}: empareja otra si hace falta.`
          : `La parte ${d.parte_id} ya no existe en el catálogo maestro.`;
    default:
      return `${d.nota ?? ''}${d.creada_por ? ` (${d.creada_por})` : ''}`;
  }
}

function Tarjeta({
  t,
  ocupado,
  alConforme,
  alHallazgo,
}: {
  t: TareaVerificacion;
  ocupado: boolean;
  alConforme: () => void;
  alHallazgo: () => void;
}) {
  return (
    <li className="rounded-lg border border-borde bg-superficie">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-borde px-4 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <Link to="/articulos/$itemCode" params={{ itemCode: t.item_code }} className="font-medium underline">
            {t.item_code}
          </Link>
          <Insignia>{ORIGENES[t.origen]}</Insignia>
          <EtiquetaEstado estado={t.estado_articulo as Estado} />
        </div>
        <span className="text-xs text-suave">{momento(t.creada_en)}</span>
      </div>
      <div className={cn('grid gap-4 p-4', t.foto_url && 'sm:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]')}>
        {t.foto_url && (
          <a
            href={t.foto_url}
            target="_blank"
            rel="noreferrer"
            className="block overflow-hidden rounded-md border border-borde"
          >
            <img src={t.foto_url} alt={`Foto nueva de ${t.item_code}`} className="aspect-square w-full object-cover" />
          </a>
        )}
        <div className="space-y-2 text-sm">
          <p className="text-suave">{t.descripcion}</p>
          <p className="tabular-nums">
            Panal {n(t.medidas.alto)} × {n(t.medidas.largo)} × {n(t.medidas.ancho)} mm
            {t.origen === 'NUEVA_FOTO' && ` · ${t.fotos_validadas} fotos ya validadas`}
          </p>
          <p>{queRevisar(t)}</p>
          <div className="flex flex-wrap gap-2 pt-1">
            <Boton variante="secundario" disabled={ocupado} onClick={alConforme}>
              <Check className="size-4" aria-hidden /> Conforme
            </Boton>
            <Boton variante="fantasma" className="text-rechazado" disabled={ocupado} onClick={alHallazgo}>
              <TriangleAlert className="size-4" aria-hidden /> Con hallazgo
            </Boton>
          </div>
        </div>
      </div>
    </li>
  );
}

/** Pantalla Verificación (propuesta UX §6.6, ADR 0012). */
export function Verificacion() {
  const { filtro } = useFiltro();
  const usuario = useUsuario();
  const esAdmin = usuario.roles.includes('ADMINISTRADOR');
  const [origen, setOrigen] = useState<OrigenTarea | undefined>();
  const [hallazgo, setHallazgo] = useState<TareaVerificacion | null>(null);
  const [nueva, setNueva] = useState(false);
  const [hecho, setHecho] = useState<string>();
  const filtroApi = { cat: filtro.cat, linea: filtro.linea };
  const q = useListarVerificaciones({ ...filtroApi, origen });
  const resolver = useResolverVerificacion();
  const muestreo = useGenerarMuestreo();
  const crear = useCrearVerificacion();

  const error = [resolver.error, muestreo.error].find((e) => e instanceof ProblemaError);
  const refrescar = () => void q.refetch();
  const resolverTarea = (t: TareaVerificacion, resultado: 'CONFORME' | 'CON_HALLAZGO', nota?: string) =>
    resolver.mutate(
      { tareaId: t.id, data: { resultado, nota } },
      {
        onSuccess: () => {
          setHallazgo(null);
          setHecho(
            resultado === 'CONFORME'
              ? `${t.item_code}: conforme.`
              : `${t.item_code}: regresó a Pendiente con tu nota para que lo corrijan.`,
          );
          refrescar();
        },
      },
    );

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold">Verificación</h1>
        <div className="flex flex-wrap gap-2">
          <Boton variante="secundario" onClick={() => setNueva(true)}>
            <Plus className="size-4" aria-hidden /> Nueva
          </Boton>
          {esAdmin && (
            <Boton
              variante="secundario"
              cargando={muestreo.isPending}
              onClick={() =>
                muestreo.mutate(
                  { data: { cantidad: 10 }, params: filtroApi },
                  {
                    onSuccess: (r) => {
                      setHecho(
                        r.creadas
                          ? `Muestreo: ${r.creadas} artículos validados al azar.`
                          : 'No hay artículos validados sin verificación abierta.',
                      );
                      refrescar();
                    },
                  },
                )
              }
            >
              <Dices className="size-4" aria-hidden /> Muestreo de 10
            </Boton>
          )}
        </div>
      </div>

      {error instanceof ProblemaError && (
        <Aviso tono="error" titulo={error.problema.title}>
          {error.problema.detail}
        </Aviso>
      )}
      {hecho && !error && <Aviso tono="exito" titulo={hecho} />}

      {q.data && (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Origen">
          <button
            type="button"
            aria-pressed={!origen}
            onClick={() => setOrigen(undefined)}
            className="rounded-full border border-borde px-3 py-1 text-sm aria-pressed:border-primario aria-pressed:bg-primario/10"
          >
            Todas ({Object.values(q.data.por_origen).reduce((a, b) => a + b, 0)})
          </button>
          {(Object.keys(ORIGENES) as OrigenTarea[]).map((o) => (
            <button
              key={o}
              type="button"
              aria-pressed={origen === o}
              onClick={() => setOrigen(o)}
              className="rounded-full border border-borde px-3 py-1 text-sm aria-pressed:border-primario aria-pressed:bg-primario/10"
            >
              {ORIGENES[o]} ({q.data.por_origen[o] ?? 0})
            </button>
          ))}
        </div>
      )}

      {q.isError && <Aviso tono="error" titulo={q.error.problema.title} />}
      {q.isLoading && <p className="text-sm text-suave">Cargando…</p>}
      {q.data?.tareas.length === 0 && (
        <p className="rounded-lg border border-borde bg-superficie p-8 text-center text-sm text-suave">
          No hay verificaciones abiertas{origen ? ` de «${ORIGENES[origen]}»` : ''} en este tipo de artículo.
        </p>
      )}
      <ul className="space-y-3">
        {q.data?.tareas.map((t) => (
          <Tarjeta
            key={t.id}
            t={t}
            ocupado={resolver.isPending}
            alConforme={() => resolverTarea(t, 'CONFORME')}
            alHallazgo={() => setHallazgo(t)}
          />
        ))}
      </ul>

      <Dialogo abierto={!!hallazgo} alCerrar={() => setHallazgo(null)} titulo="Con hallazgo">
        {hallazgo && (
          <DialogoHallazgo
            t={hallazgo}
            enviando={resolver.isPending}
            alConfirmar={(nota) => resolverTarea(hallazgo, 'CON_HALLAZGO', nota)}
          />
        )}
      </Dialogo>
      <Dialogo abierto={nueva} alCerrar={() => setNueva(false)} titulo="Nueva verificación">
        <FormNueva
          enviando={crear.isPending}
          error={crear.error instanceof ProblemaError ? crear.error.problema.title : undefined}
          alCrear={(item_code, nota) =>
            crear.mutate(
              { data: { item_code, nota } },
              {
                onSuccess: () => (
                  setNueva(false),
                  setHecho(`Verificación creada para ${item_code.toUpperCase()}.`),
                  refrescar()
                ),
              },
            )
          }
        />
      </Dialogo>
    </div>
  );
}

function DialogoHallazgo({
  t,
  enviando,
  alConfirmar,
}: {
  t: TareaVerificacion;
  enviando: boolean;
  alConfirmar: (nota: string) => void;
}) {
  const [nota, setNota] = useState('');
  return (
    <form onSubmit={(e) => (e.preventDefault(), nota.trim() && alConfirmar(nota.trim()))} className="space-y-3 text-sm">
      <p className="text-suave">
        {t.item_code} regresará a <strong>Pendiente</strong> para que un operador lo corrija. Escribe qué encontraste.
      </p>
      <textarea
        autoFocus
        required
        value={nota}
        onChange={(e) => setNota(e.target.value)}
        aria-label="Qué encontraste"
        rows={4}
        className="w-full rounded-md border border-borde bg-superficie p-2 text-base sm:text-sm"
        placeholder="La foto es de otro artículo; el alto real es 420 mm…"
      />
      <div className="flex justify-end">
        <Boton type="submit" variante="peligro" cargando={enviando} disabled={!nota.trim()}>
          Regresar a Pendiente
        </Boton>
      </div>
    </form>
  );
}

function FormNueva({
  enviando,
  error,
  alCrear,
}: {
  enviando: boolean;
  error?: string;
  alCrear: (itemCode: string, nota: string) => void;
}) {
  const enviar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    alCrear(String(d.get('item_code')).trim(), String(d.get('nota')).trim());
  };
  return (
    <form onSubmit={enviar} className="space-y-3">
      <Campo
        etiqueta="Artículo"
        name="item_code"
        required
        minLength={3}
        placeholder="RAD00188"
        autoCapitalize="characters"
      />
      <Campo etiqueta="Qué hay que revisar" name="nota" required minLength={3} />
      {error && <Aviso tono="error" titulo={error} />}
      <div className="flex justify-end">
        <Boton type="submit" cargando={enviando}>
          Crear
        </Boton>
      </div>
    </form>
  );
}
