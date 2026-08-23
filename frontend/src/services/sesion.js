/**
 * Persistencia de la sesion (token + usuario) en `localStorage`.
 *
 * Modulo separado de `hooks/useAuth.js` a proposito: `services/api.js`
 * necesita leer el token para el interceptor de Axios, y `useAuth.js`
 * necesita leer/escribir el mismo dato para el estado de React. Si uno de
 * los dos importara del otro se formaria un ciclo (api.js <-> useAuth.js);
 * aqui viven ambos lados sin que ninguno dependa del otro.
 *
 * Mismo patron defensivo que `hooks/useHistorialBusquedas.js`: cualquier
 * fallo de `localStorage` (modo privado, JSON corrupto) degrada a "sin
 * sesion" en vez de romper el render.
 */

const CLAVE_SESION = 'athenia:sesion'

/** Lee `{ token, usuario }` guardado, o `null` si no hay sesion valida. */
export function leerSesion() {
  try {
    const crudo = window.localStorage.getItem(CLAVE_SESION)
    if (!crudo) return null

    const datos = JSON.parse(crudo)
    if (!datos || typeof datos.token !== 'string' || !datos.token || !datos.usuario) {
      return null
    }
    return datos
  } catch {
    return null
  }
}

/** Guarda la sesion, o la borra si se llama con `null`. */
export function guardarSesion(sesion) {
  try {
    if (sesion) {
      window.localStorage.setItem(CLAVE_SESION, JSON.stringify(sesion))
    } else {
      window.localStorage.removeItem(CLAVE_SESION)
    }
  } catch {
    // La sesion sigue viva en el estado de React durante esta pestaña aunque
    // no se pueda persistir (Safari privado, cuota agotada, etc.).
  }
}

/** Atajo usado por el interceptor de Axios: solo el token, o `null`. */
export function leerToken() {
  return leerSesion()?.token ?? null
}
