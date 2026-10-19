import { useCallback, useEffect, useState } from 'react';

import { guardar, leer } from './almacen';

export type Tema = 'sistema' | 'claro' | 'oscuro';

const CLAVE = 'nexo.tema';
const consulta = () => window.matchMedia('(prefers-color-scheme: dark)');

export function temaGuardado(): Tema {
  const t = leer(CLAVE);
  return t === 'claro' || t === 'oscuro' ? t : 'sistema';
}

export function esOscuro(tema: Tema, sistemaOscuro: boolean): boolean {
  return tema === 'oscuro' || (tema === 'sistema' && sistemaOscuro);
}

/** Tema elegido por el usuario; con "sistema" sigue los cambios del sistema operativo en vivo. */
export function useTema(): [Tema, (t: Tema) => void] {
  const [tema, setTema] = useState<Tema>(temaGuardado);

  useEffect(() => {
    const aplicar = () => document.documentElement.classList.toggle('dark', esOscuro(tema, consulta().matches));
    aplicar();
    if (tema !== 'sistema') return;
    const mq = consulta();
    mq.addEventListener('change', aplicar);
    return () => mq.removeEventListener('change', aplicar);
  }, [tema]);

  const cambiar = useCallback((t: Tema) => {
    guardar(CLAVE, t);
    setTema(t);
  }, []);

  return [tema, cambiar];
}
