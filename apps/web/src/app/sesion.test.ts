import type { UsuarioSesion } from '@nexo/api-client';
import { describe, expect, it } from 'vitest';

import { destinoSeguro } from '@/features/auth/Entrar';

import { SECCIONES } from './navegacion';
import { iniciales, puedeVer } from './sesion';

const usuario = (roles: UsuarioSesion['roles'], permisos: UsuarioSesion['permisos'] = []): UsuarioSesion => ({
  id: 1,
  usuario: 'ana',
  nombre: 'Ana López',
  correo: null,
  roles,
  permisos,
  debe_cambiar_password: false,
});
const visibles = (u: UsuarioSesion) => SECCIONES.filter((s) => puedeVer(u, s)).map((s) => s.etiqueta);

describe('secciones por rol (propuesta UX §3)', () => {
  it('el operador trabaja y explora, pero no valida ni administra', () => {
    expect(visibles(usuario(['OPERADOR']))).toEqual(['Panorama', 'Trabajar', 'Explorar', 'Fabricados', 'Catálogo']);
  });

  it('el encargado de fotos ve Fotos', () => {
    expect(visibles(usuario(['FOTOS']))).toContain('Fotos');
  });

  it('Ventas depende del permiso, no del rol', () => {
    expect(visibles(usuario(['ADMINISTRADOR']))).not.toContain('Ventas');
    expect(visibles(usuario(['OPERADOR'], ['VER_ANALISIS_VENTAS']))).toContain('Ventas');
  });

  it('el administrador ve Administración', () => {
    expect(visibles(usuario(['ADMINISTRADOR']))).toContain('Administración');
  });
});

describe('después de entrar', () => {
  it('solo redirige a rutas internas', () => {
    expect(destinoSeguro('/validar?cat=18')).toBe('/validar?cat=18');
    expect(destinoSeguro('https://otro.sitio')).toBe('/');
    expect(destinoSeguro('//otro.sitio')).toBe('/');
    expect(destinoSeguro(undefined)).toBe('/');
    expect(destinoSeguro('/entrar?redirigir=%2F')).toBe('/');
  });

  it('iniciales del menú de usuario', () => {
    expect(iniciales('Ana López Pérez')).toBe('AL');
  });
});
