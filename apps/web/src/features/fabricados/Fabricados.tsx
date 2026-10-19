import {
  ProblemaError,
  useCapturarCodigoEquivalente,
  useListarFabricados,
  useValidarCodigoEquivalente,
  type Estado,
  type Fabricado,
} from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { Search, ShieldCheck } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { useUsuario } from '@/app/contexto-usuario';
import { ESTADOS_CODIGO } from '@/features/articulo/Equivalencia';
import { cn } from '@/shared/cn';
import { EtiquetaEstado } from '@/shared/estados';
import { Aviso, Boton, Insignia } from '@/shared/ui';

const POR_PAGINA = 50;
const ETIQUETA = Object.fromEntries(ESTADOS_CODIGO) as Record<string, string>;

/** Captura rápida en línea: Enter guarda. */
function CodigoEnLinea({
  f,
  alGuardar,
  guardando,
}: {
  f: Fabricado;
  alGuardar: (c: string) => void;
  guardando: boolean;
}) {
  const [valor, setValor] = useState(f.codigo_equivalente ?? '');
  const sucio = valor.trim().toUpperCase() !== (f.codigo_equivalente ?? '');
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    if (sucio) alGuardar(valor);
  };
  return (
    <form onSubmit={enviar} className="flex gap-1">
      <input
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        aria-label={`Código equivalente de ${f.item_code}`}
        list={f.codigo_anterior.length ? `ant-${f.item_code}` : undefined}
        placeholder={f.codigo_anterior[0] ?? 'Código'}
        className={cn(
          'h-8 w-full min-w-0 rounded-md border bg-superficie px-2 text-base uppercase sm:text-sm',
          sucio ? 'border-por-validar' : 'border-borde',
        )}
      />
      {f.codigo_anterior.length > 0 && (
        <datalist id={`ant-${f.item_code}`}>
          {f.codigo_anterior.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>
      )}
      {sucio && (
        <Boton type="submit" variante="secundario" className="h-8 px-2 text-xs" cargando={guardando}>
          Guardar
        </Boton>
      )}
    </form>
  );
}

/** Revisión de fabricados (propuesta UX §6.7, ADR 0018): código equivalente y su estado, filtrable. */
export function Fabricados() {
  const { filtro } = useFiltro();
  const usuario = useUsuario();
  const valida = usuario.roles.some((r) => r === 'SUPERVISOR' || r === 'ADMINISTRADOR');
  const [estado, setEstado] = useState<string | undefined>();
  const [texto, setTexto] = useState('');
  const [q, setQ] = useState('');
  const [pagina, setPagina] = useState(0);
  const [hecho, setHecho] = useState<string>();
  const lista = useListarFabricados({
    cat: filtro.cat,
    linea: 'FABRICADO',
    estado_codigo: estado,
    q: q || undefined,
    limite: POR_PAGINA,
    desde: pagina * POR_PAGINA,
  });
  const capturar = useCapturarCodigoEquivalente();
  const validar = useValidarCodigoEquivalente();
  const error = [capturar.error, validar.error].find((e) => e instanceof ProblemaError);

  useEffect(() => {
    const t = setTimeout(() => (setQ(texto.trim()), setPagina(0)), 350);
    return () => clearTimeout(t);
  }, [texto]);

  const r = lista.data;
  const total = r ? Object.values(r.por_estado).reduce((a, b) => a + b, 0) : 0;
  const elegir = (e?: string) => (setEstado(e), setPagina(0));

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <h1 className="text-xl font-semibold">Fabricados</h1>
      {error instanceof ProblemaError && (
        <Aviso tono="error" titulo={error.problema.title}>
          {error.problema.detail}
        </Aviso>
      )}
      {hecho && !error && <Aviso tono="exito" titulo={hecho} />}

      {r && (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Estado del código">
          <button
            type="button"
            aria-pressed={!estado}
            onClick={() => elegir(undefined)}
            className="rounded-full border border-borde px-3 py-1 text-sm aria-pressed:border-primario aria-pressed:bg-primario/10"
          >
            Todos ({total})
          </button>
          {ESTADOS_CODIGO.map(([e, etiqueta]) => (
            <button
              key={e}
              type="button"
              aria-pressed={estado === e}
              onClick={() => elegir(e)}
              className="rounded-full border border-borde px-3 py-1 text-sm aria-pressed:border-primario aria-pressed:bg-primario/10"
            >
              {etiqueta} ({r.por_estado[e] ?? 0})
            </button>
          ))}
        </div>
      )}
      <label className="relative block">
        <Search className="absolute top-3 left-3 size-4 text-suave" aria-hidden />
        <input
          type="search"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          aria-label="Buscar fabricado"
          placeholder="Código, descripción o código anterior"
          className="h-10 w-full rounded-md border border-borde bg-superficie pr-3 pl-9 text-base sm:text-sm"
        />
      </label>

      {lista.isError && <Aviso tono="error" titulo={lista.error.problema.title} />}
      {lista.isLoading && <p className="text-sm text-suave">Cargando…</p>}
      {r && r.fabricados.length === 0 && (
        <p className="rounded-lg border border-borde bg-superficie p-8 text-center text-sm text-suave">
          No hay fabricados con ese filtro.
        </p>
      )}
      {r && r.fabricados.length > 0 && (
        <ul className="divide-y divide-borde rounded-lg border border-borde bg-superficie">
          {r.fabricados.map((f) => (
            <li
              key={f.item_code}
              className="grid gap-2 px-4 py-3 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_auto] md:items-center md:gap-4"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Link to="/articulos/$itemCode" params={{ itemCode: f.item_code }} className="font-medium underline">
                    {f.item_code}
                  </Link>
                  <EtiquetaEstado estado={f.estado as Estado} />
                </div>
                <p className="truncate text-xs text-suave">{f.descripcion}</p>
              </div>
              <CodigoEnLinea
                key={f.codigo_equivalente ?? ''}
                f={f}
                guardando={capturar.isPending && capturar.variables?.itemCode === f.item_code}
                alGuardar={(c) =>
                  capturar.mutate(
                    { itemCode: f.item_code, data: { codigo: c.trim() || null } },
                    { onSuccess: () => (setHecho(`${f.item_code}: código guardado.`), void lista.refetch()) },
                  )
                }
              />
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <Insignia className={cn(f.estado_codigo === 'VALIDADO' && 'border-validado/40 text-validado')}>
                  {ETIQUETA[f.estado_codigo] ?? f.estado_codigo}
                </Insignia>
                {f.importado && <span className="text-suave">≡ {f.importado}</span>}
                {valida && f.estado_codigo === 'LISTO_PARA_VALIDAR' && (
                  <Boton
                    className="h-8 px-2 text-xs"
                    cargando={validar.isPending && validar.variables?.itemCode === f.item_code}
                    onClick={() =>
                      validar.mutate(
                        { itemCode: f.item_code },
                        { onSuccess: () => (setHecho(`${f.item_code}: código validado.`), void lista.refetch()) },
                      )
                    }
                  >
                    <ShieldCheck className="size-3.5" aria-hidden /> Validar
                  </Boton>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {r && r.total > POR_PAGINA && (
        <div className="flex items-center justify-between text-sm">
          <Boton variante="secundario" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>
            Anteriores
          </Boton>
          <span className="text-suave">
            {pagina * POR_PAGINA + 1}–{Math.min((pagina + 1) * POR_PAGINA, r.total)} de {r.total}
          </span>
          <Boton
            variante="secundario"
            disabled={(pagina + 1) * POR_PAGINA >= r.total}
            onClick={() => setPagina((p) => p + 1)}
          >
            Siguientes
          </Boton>
        </div>
      )}
    </div>
  );
}
