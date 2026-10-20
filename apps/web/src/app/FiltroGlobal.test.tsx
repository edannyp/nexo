import type { Categoria } from '@nexo/api-client';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { FiltroGlobal } from './FiltroGlobal';

const categorias: Categoria[] = [
  {
    id: 1,
    codigo: '25',
    nombre: 'RADIADORES',
    part_terminology_id: 2172,
    activos: { IMPORTADO: 1095, FABRICADO: 2028 },
  },
  { id: 3, codigo: '18', nombre: 'INTERCOOLER', part_terminology_id: 12616, activos: { IMPORTADO: 79, FABRICADO: 40 } },
];

describe('FiltroGlobal', () => {
  it('muestra categorías legibles y los activos de cada línea', () => {
    render(<FiltroGlobal categorias={categorias} filtro={{ cat: '25', linea: 'IMPORTADO' }} onCambiar={() => {}} />);
    expect(screen.getByRole('option', { name: 'Radiadores' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Importados (1,095)' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Fabricados (2,028)' })).toBeInTheDocument();
  });

  it('avisa el cambio de categoría conservando la línea', async () => {
    const onCambiar = vi.fn();
    render(<FiltroGlobal categorias={categorias} filtro={{ cat: '25', linea: 'FABRICADO' }} onCambiar={onCambiar} />);
    await userEvent.selectOptions(screen.getByLabelText('Categoría'), '18');
    expect(onCambiar).toHaveBeenCalledWith({ cat: '18', linea: 'FABRICADO' });
  });

  it('sin conexión deja los selectores deshabilitados', () => {
    render(
      <FiltroGlobal categorias={undefined} error filtro={{ cat: '25', linea: 'IMPORTADO' }} onCambiar={() => {}} />,
    );
    expect(screen.getByLabelText('Categoría')).toBeDisabled();
    expect(screen.getByRole('option', { name: 'Sin conexión' })).toBeInTheDocument();
  });
});
