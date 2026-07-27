/**
 * Cliente HTTP de AthenIA.
 * ------------------------
 * Unico punto del frontend que conoce la URL del backend. Cambiar de local a
 * produccion (OCI) es cuestion de ajustar VITE_API_URL en el archivo .env.
 */
import axios from 'axios'

// En desarrollo se usa el proxy de Vite ("/api" -> http://127.0.0.1:8000),
// asi no hay que preocuparse por CORS ni por puertos al hacer la demo.
export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Traduce cualquier fallo de axios a un mensaje legible en espanol.
 * Evita que el usuario vea "Request failed with status code 422".
 */
export function mensajeDeError(error) {
  if (error.code === 'ECONNABORTED') {
    return 'El analisis tardo demasiado. Intenta de nuevo.'
  }

  // Sin respuesta => el backend no esta arriba.
  if (!error.response) {
    return 'No se pudo conectar con el servidor de AthenIA. Verifica que el backend este ejecutandose en el puerto 8000.'
  }

  const { status, data } = error.response

  // El backend responde con el esquema ErrorResponse: { error, mensaje, detail }
  if (status === 422 && Array.isArray(data?.detail)) {
    const campos = data.detail
      .map((e) => e.loc?.[e.loc.length - 1])
      .filter(Boolean)
      .join(', ')
    if (campos) return `Revisa los campos: ${campos}. No pueden estar vacios.`
  }

  if (typeof data?.mensaje === 'string') return data.mensaje
  if (typeof data?.detail === 'string') return data.detail
  if (status >= 500) return 'El servidor de AthenIA tuvo un problema. Intenta mas tarde.'

  return `Ocurrio un error inesperado (codigo ${status}).`
}

/** Envuelve una llamada para que siempre lance un Error con mensaje listo para la UI. */
async function peticion(ejecutar) {
  try {
    const { data } = await ejecutar()
    return data
  } catch (error) {
    throw new Error(mensajeDeError(error))
  }
}

// ---------------------------------------------------------------------------
// Analisis
// ---------------------------------------------------------------------------

/**
 * POST /contenido - envia contenido tecnico al modelo de IA.
 * El backend guarda el analisis en el historial y devuelve su `id`.
 *
 * @param {{titulo: string, texto: string, origen?: string, url?: string}} contenido
 * @returns {Promise<{id:number, categoria:string, probabilidad:number, informacion_adicional:string[]}>}
 */
export function analizarContenido({ titulo, texto, origen, url }) {
  return peticion(() => api.post('/contenido', { titulo, texto, origen, url }))
}

// ---------------------------------------------------------------------------
// Historial
// ---------------------------------------------------------------------------

/**
 * GET /contenidos - historial de analisis, del mas reciente al mas antiguo.
 *
 * @param {{categoria?: string, buscar?: string, limite?: number}} filtros
 * @param {AbortSignal} [signal] Para cancelar busquedas que quedaron obsoletas.
 * @returns {Promise<{total: number, items: object[]}>}
 */
export function obtenerContenidos(filtros = {}, signal) {
  // Se omiten los filtros vacios para no ensuciar la query string.
  const params = Object.fromEntries(
    Object.entries(filtros).filter(([, valor]) => valor !== '' && valor != null),
  )
  return peticion(() => api.get('/contenidos', { params, signal }))
}

/** GET /contenidos/{id} - detalle de un analisis. */
export function obtenerContenido(id) {
  return peticion(() => api.get(`/contenidos/${id}`))
}

/** DELETE /contenidos - vacia el historial (utilidad de QA). */
export function limpiarHistorial() {
  return peticion(() => api.delete('/contenidos'))
}

// ---------------------------------------------------------------------------
// Metricas y metadatos
// ---------------------------------------------------------------------------

/** GET /metricas - agregados que alimentan el Dashboard. */
export function obtenerMetricas(signal) {
  return peticion(() => api.get('/metricas', { signal }))
}

/** GET /salud - verificacion de uptime (la usa el indicador del Header). */
export function verificarSalud() {
  return peticion(() => api.get('/salud'))
}

/** GET /categorias - catalogo de categorias soportadas por el modelo. */
export async function obtenerCategorias() {
  const data = await peticion(() => api.get('/categorias'))
  return data.categorias
}

export default api
