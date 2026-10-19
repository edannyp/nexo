import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { mes, porcentaje } from './formato';
import { Columnas, Medidor, Tendencia } from './graficos';

describe('formatos', () => {
  it('porcentaje legible, sin dividir entre cero ni mostrar 0.0 % para valores mínimos', () => {
    expect(porcentaje(0.0613)).toBe('6.1 %');
    expect(porcentaje(0.0004)).toBe('<0.1 %');
    expect(porcentaje(null)).toBe('—');
  });

  it('los meses se leen en UTC (sin correrse al mes anterior por zona horaria)', () => {
    expect(mes('2026-09-01')).toMatch(/sept?\.? 26/i);
  });
});

describe('gráficos', () => {
  it('la tendencia lleva flecha, signo y texto, no solo color', () => {
    render(<Tendencia valor={0.25} />);
    expect(screen.getByLabelText('Sube +25 %')).toHaveTextContent('↑ +25 %');
  });

  it('el medidor expone su valor a lectores de pantalla', () => {
    render(<Medidor etiqueta="Con foto propia" valor={404} total={1095} />);
    const m = screen.getByRole('meter', { name: 'Con foto propia' });
    expect(m).toHaveAttribute('aria-valuenow', '404');
    expect(screen.getByText('37 %')).toBeInTheDocument();
  });

  it('las columnas muestran el detalle con el foco del teclado y tienen vista de tabla', async () => {
    const datos = [
      { etiqueta: 'ago 26', valor: 2203 },
      { etiqueta: 'sept 26', valor: 2167 },
    ];
    render(<Columnas titulo="Unidades por mes" unidad="Unidades" datos={datos} />);
    fireEvent.focus(screen.getByRole('listitem', { name: 'ago 26: 2,203 unidades' }));
    expect(screen.getByRole('tooltip')).toHaveTextContent('2,203 ago 26');

    await userEvent.click(screen.getByRole('button', { name: 'Ver tabla' }));
    expect(screen.getByRole('table')).toHaveTextContent('sept 262,167');
  });
});
