import type { Estado } from '@nexo/api-client';
import { CheckCheck, CircleCheck, CircleDashed, CircleX, Send, type LucideIcon } from 'lucide-react';

import { cn } from './cn';

/** Estados del flujo (context/workflow-estados.md): siempre ícono + texto + color, nunca solo color. */
export const ESTADOS: Record<Estado, { etiqueta: string; icono: LucideIcon; clase: string }> = {
  PENDIENTE: { etiqueta: 'Pendiente', icono: CircleDashed, clase: 'text-pendiente' },
  POR_VALIDAR: { etiqueta: 'Por validar', icono: Send, clase: 'text-por-validar' },
  RECHAZADO: { etiqueta: 'Rechazado', icono: CircleX, clase: 'text-rechazado' },
  VALIDADO: { etiqueta: 'Validado', icono: CircleCheck, clase: 'text-validado' },
  SINCRONIZADO: { etiqueta: 'Sincronizado', icono: CheckCheck, clase: 'text-sincronizado' },
};

export const ORDEN_ESTADOS: Estado[] = ['PENDIENTE', 'POR_VALIDAR', 'RECHAZADO', 'VALIDADO', 'SINCRONIZADO'];

export function IconoEstado({ estado, className }: { estado: Estado; className?: string }) {
  const { icono: Icono, clase } = ESTADOS[estado];
  return <Icono className={cn('size-4 shrink-0', clase, className)} aria-hidden />;
}

export function EtiquetaEstado({ estado }: { estado: Estado }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm whitespace-nowrap">
      <IconoEstado estado={estado} />
      {ESTADOS[estado].etiqueta}
    </span>
  );
}
