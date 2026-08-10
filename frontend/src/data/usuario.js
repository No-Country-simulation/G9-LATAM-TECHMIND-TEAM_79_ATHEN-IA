/**
 * Identidad del usuario de la demo.
 *
 * Hasta la Semana 4 el nombre estaba duplicado y desincronizado: el Header
 * decia "Luis Perez" y el Dashboard saludaba con un "Luis" escrito aparte.
 * Centralizarlo evita que se separen otra vez.
 *
 * En la Semana 5, cuando exista autenticacion, este modulo se sustituye por el
 * contexto de sesion (o un `useUsuario()` que lea del backend) sin tocar los
 * componentes que ya lo consumen.
 */

export const USUARIO_DEMO = {
  nombre: 'Luis Pérez',
  rol: 'Estudiante',
}

/** Primer nombre, para saludos ("Hola, Luis"). */
export function nombreDePila(nombreCompleto = USUARIO_DEMO.nombre) {
  return nombreCompleto.trim().split(/\s+/)[0]
}

/** Iniciales para el avatar ("Luis Pérez" -> "LP"). */
export function iniciales(nombreCompleto = USUARIO_DEMO.nombre) {
  return nombreCompleto
    .trim()
    .split(/\s+/)
    .map((parte) => parte[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}
