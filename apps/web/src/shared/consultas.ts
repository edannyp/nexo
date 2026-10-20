import type { QueryClient } from '@tanstack/react-query';

/**
 * Tras cambiar el estado o la reserva de un artículo, las listas, conteos y el panorama quedan viejos: se invalidan.
 * (Las llaves de orval empiezan con la URL del recurso.)
 */
export function invalidarArticulos(consultas: QueryClient): Promise<void> {
  return consultas.invalidateQueries({
    predicate: (q) => {
      const url = String(q.queryKey[0] ?? '');
      return (
        url.startsWith('/api/v1/articulos') || url.startsWith('/api/v1/panorama') || url.startsWith('/api/v1/busqueda')
      );
    },
  });
}
