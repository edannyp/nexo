/**
 * Componentes base del design system (pasarán a packages/ui cuando crezcan). Accesibles, mobile first y con tokens del tema.
 */
import { CircleAlert, CircleCheck, Info, X } from 'lucide-react';
import { forwardRef, useEffect, useId, useRef, type ComponentProps, type ReactNode } from 'react';

import { cn } from './cn';

const VARIANTES = {
  primario: 'bg-primario text-primario-texto hover:opacity-90',
  secundario: 'border border-borde bg-superficie text-texto hover:bg-superficie-2',
  peligro: 'bg-rechazado text-white hover:opacity-90',
  fantasma: 'text-suave hover:bg-superficie-2 hover:text-texto',
};

type BotonProps = ComponentProps<'button'> & { variante?: keyof typeof VARIANTES; cargando?: boolean };

export function Boton({ variante = 'primario', cargando, className, children, disabled, ...props }: BotonProps) {
  return (
    <button
      type="button"
      {...props}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      className={cn(
        'inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium transition',
        'disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTES[variante],
        className,
      )}
    >
      {cargando && (
        <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
      )}
      {children}
    </button>
  );
}

type CampoProps = ComponentProps<'input'> & { etiqueta: string; error?: string; ayuda?: ReactNode };

export const Campo = forwardRef<HTMLInputElement, CampoProps>(function Campo(
  { etiqueta, error, ayuda, className, id, ...props },
  ref,
) {
  const generado = useId();
  const campoId = id ?? generado;
  const describe = error ? `${campoId}-error` : ayuda ? `${campoId}-ayuda` : undefined;
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={campoId} className="block text-sm font-medium">
        {etiqueta}
      </label>
      <input
        ref={ref}
        id={campoId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describe}
        className={cn(
          'h-10 w-full rounded-md border bg-superficie px-3 text-base sm:text-sm',
          error ? 'border-rechazado' : 'border-borde',
        )}
        {...props}
      />
      {error ? (
        <p id={`${campoId}-error`} className="text-sm text-rechazado">
          {error}
        </p>
      ) : (
        ayuda && (
          <p id={`${campoId}-ayuda`} className="text-sm text-suave">
            {ayuda}
          </p>
        )
      )}
    </div>
  );
});

const TONOS = {
  error: { clase: 'border-rechazado/40 bg-rechazado/10', Icono: CircleAlert },
  exito: { clase: 'border-validado/40 bg-validado/10', Icono: CircleCheck },
  info: { clase: 'border-por-validar/40 bg-por-validar/10', Icono: Info },
};

export function Aviso({
  tono = 'info',
  titulo,
  children,
}: {
  tono?: keyof typeof TONOS;
  titulo: string;
  children?: ReactNode;
}) {
  const { clase, Icono } = TONOS[tono];
  return (
    <div role={tono === 'error' ? 'alert' : 'status'} className={cn('flex gap-3 rounded-md border p-3 text-sm', clase)}>
      <Icono className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div>
        <p className="font-medium">{titulo}</p>
        {children && <div className="mt-1 text-suave">{children}</div>}
      </div>
    </div>
  );
}

export function Insignia({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn('inline-flex items-center rounded-full border border-borde px-2 py-0.5 text-xs', className)}>
      {children}
    </span>
  );
}

/** Diálogo modal nativo: foco atrapado, Esc para cerrar y fondo inerte sin librerías. En celular ocupa el ancho. */
export function Dialogo({
  abierto,
  alCerrar,
  titulo,
  children,
}: {
  abierto: boolean;
  alCerrar: () => void;
  titulo: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (abierto && !d.open) d.showModal();
    if (!abierto && d.open) d.close();
  }, [abierto]);
  return (
    <dialog
      ref={ref}
      aria-label={titulo}
      onClose={alCerrar}
      onClick={(e) => e.target === ref.current && alCerrar()}
      className="m-auto w-[min(32rem,calc(100vw-1.5rem))] rounded-lg border border-borde bg-superficie p-0 text-texto backdrop:bg-black/40"
    >
      <div className="flex items-center justify-between border-b border-borde px-4 py-3">
        <h2 className="font-semibold">{titulo}</h2>
        <button
          type="button"
          onClick={alCerrar}
          aria-label="Cerrar"
          className="grid size-8 place-items-center rounded-md hover:bg-superficie-2"
        >
          <X className="size-4" aria-hidden />
        </button>
      </div>
      <div className="p-4">{abierto && children}</div>
    </dialog>
  );
}
