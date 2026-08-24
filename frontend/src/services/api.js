/**
 * Cliente HTTP de AthenIA.
 * ------------------------
 * Unico punto del frontend que conoce la URL del backend. Cambiar de local a
 * produccion (OCI) es cuestion de ajustar VITE_API_URL en el archivo .env.
 */
import axios from 'axios'
import { leerToken } from './sesion'

// En desarrollo se usa el proxy de Vite ("/api" -> http://127.0.0.1:8000),
// asi no hay que preocuparse por CORS ni por puertos al hacer la demo.
export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

// Adjunta el JWT de sesion (si hay una) a cada peticion. Se lee de
// `localStorage` en cada request en vez de guardarse en una variable del
// modulo, para que un login/logout en OTRA pestaña se refleje de inmediato
// sin tener que recargar esta.
api.interceptors.request.use((config) => {
  const token = leerToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
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
// Autenticacion (Semana 5)
// ---------------------------------------------------------------------------

/**
 * POST /auth/registro - crea una cuenta y devuelve un token (login automatico).
 *
 * El primer usuario de una instalacion nueva de AthenIA recibe el rol
 * 'admin' automaticamente; el resto entra como 'estudiante'.
 *
 * @param {{email: string, password: string, nombre: string}} datos
 * @returns {Promise<{access_token:string, token_type:string, usuario:object}>}
 */
export function registrarUsuario({ email, password, nombre }) {
  return peticion(() => api.post('/auth/registro', { email, password, nombre }))
}

/**
 * POST /auth/login - autentica y devuelve un token.
 *
 * @param {{email: string, password: string}} credenciales
 * @returns {Promise<{access_token:string, token_type:string, usuario:object}>}
 */
export function iniciarSesion({ email, password }) {
  return peticion(() => api.post('/auth/login', { email, password }))
}

/** GET /auth/me - usuario dueño del token adjunto por el interceptor de arriba. */
export function obtenerUsuarioActual() {
  return peticion(() => api.get('/auth/me'))
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
// Historial de analisis
// ---------------------------------------------------------------------------

/**
 * Traduce un curso de `GET /cursos[/buscar]` a la forma que renderizan las
 * tarjetas del historial, para que ambas fuentes compartan componente.
 *
 * `match_score` llega en 0..1 (similitud coseno) y se mapea a `probabilidad`,
 * que es la escala 0..1 que ya usa `aPorcentaje()` en el resto de la app.
 *
 * @param {{id:string, title:string, description:string, category:string,
 *          url:string, site:string, match_score:number}} curso
 */
function mapearCurso(curso, indice) {
  return {
    // El id del indice es estable ("curso_1423"). Antes se caia a
    // `Math.random()`, que genera una key distinta en CADA render y obliga a
    // React a desmontar y remontar toda la lista.
    id: curso?.id ?? `curso_${indice}`,
    titulo: curso?.title || 'Sin título',
    origen: curso?.site || 'Curso',
    categoria: curso?.category || 'Otras Áreas',
    // OJO con el rango: `aPorcentaje()` multiplica por 100. El respaldo
    // anterior era `?? 100`, asi que sin puntaje del backend las tarjetas
    // mostraban "10000%".
    // `null` al navegar el catalogo: no hubo consulta contra la que medir
    // afinidad. La tarjeta oculta el badge en ese caso, en vez de mostrar 0%.
    probabilidad: typeof curso?.match_score === 'number' ? curso.match_score : null,
    texto: curso?.description || '',
    url: curso?.url || '',
    imagen: curso?.image || '',
    // Marca el origen para que la UI sepa que este item NO esta en el
    // historial: no tiene detalle ni recomendaciones, se abre en su plataforma.
    esCatalogo: true,
  }
}

// ---------------------------------------------------------------------------
// Catalogo de cursos (+8.000 registros indexados en ChromaDB)
// ---------------------------------------------------------------------------

/**
 * GET /cursos - navega el catalogo SIN consulta semantica.
 *
 * Es lo que permite mostrar cursos reales nada mas cargar la vista. Antes de
 * que existiera, la unica via al catalogo era `/cursos/buscar`, que exige un
 * texto; sin el, la interfaz caia al historial de analisis (8 registros de
 * demo) y parecia que el catalogo no estuviera conectado.
 *
 * @param {{categoria?: string, limite?: number, desplazamiento?: number}} opciones
 * @param {AbortSignal} [signal]
 * @returns {Promise<{total:number, items:object[]}>}
 */
export async function obtenerCursos({ categoria, limite = 24, desplazamiento = 0 } = {}, signal) {
  const data = await peticion(() =>
    api.get('/cursos', {
      params: {
        ...(categoria && { categoria }),
        limite,
        desplazamiento,
      },
      signal,
    }),
  )
  return {
    total: data.total_indexado ?? data.total ?? 0,
    items: (data.items ?? []).map(mapearCurso),
  }
}

/**
 * GET /cursos/buscar - busqueda semantica en el catalogo.
 *
 * @param {{q: string, limite?: number, minScore?: number}} opciones
 * @param {AbortSignal} [signal]
 */
export async function buscarCursos({ q, limite = 24, minScore }, signal) {
  const data = await peticion(() =>
    api.get('/cursos/buscar', {
      params: { q, limite, ...(minScore != null && { min_score: minScore }) },
      signal,
    }),
  )
  return {
    total: data.total ?? 0,
    items: (data.resultados ?? []).map(mapearCurso),
  }
}

/**
 * GET /cursos/categorias - categorias reales del catalogo, con su conteo.
 *
 * Distinto de `obtenerCategorias()`, que devuelve las clases del clasificador
 * (`clasificador_cursos.pkl`). Son catalogos distintos: filtrar el catalogo por
 * una categoria que solo existe en el clasificador daria siempre cero.
 */
export async function obtenerCategoriasCursos(signal) {
  const data = await peticion(() => api.get('/cursos/categorias', { signal }))
  return data.items ?? []
}

/**
 * GET /contenidos - historial de analisis del usuario, con filtros del backend.
 *
 * Para el catalogo de +8.000 cursos usa `obtenerCursos` / `buscarCursos`.
 *
 * @param {{categoria?: string, buscar?: string, limite?: number}} filtros
 * @param {AbortSignal} [signal] Para cancelar busquedas que quedaron obsoletas.
 * @returns {Promise<{total: number, items: object[]}>}
 */
export function obtenerContenidos(filtros = {}, signal) {
  // Solo el historial. Esta funcion tuvo una rama que desviaba a
  // `/cursos/buscar` cuando habia termino de busqueda, y hacia que la vista
  // "Mi biblioteca" devolviera cursos del catalogo en vez del historial del
  // usuario. Consultar el catalogo es responsabilidad de `useCursos` /
  // `buscarCursos`: una funcion, un endpoint.
  const parametros = Object.fromEntries(
    Object.entries(filtros).filter(([, valor]) => valor !== '' && valor != null),
  )
  return peticion(() => api.get('/contenidos', { params: parametros, signal }))
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
// Recomendaciones
// ---------------------------------------------------------------------------

/**
 * GET /contenidos/{id}/recomendaciones - contenido relacionado.
 *
 * Cada item trae `puntaje` y `palabras_compartidas`, para que la UI pueda
 * explicar por que se recomendo en vez de mostrar solo un numero.
 *
 * @param {number} id Contenido de referencia.
 * @param {{limite?: number}} opciones
 * @param {AbortSignal} [signal]
 * @returns {Promise<{contenido_id:number, estrategia:string, total:number, items:object[]}>}
 */
//export function obtenerRecomendaciones(id, { limite = 5 } = {}, signal) {
//  return peticion(() =>
//    api.get(`/contenidos/${id}/recomendaciones`, { params: { limite }, signal }),
//  )
//}
/**
 * GET /cursos/{id}/relacionados-matriz (Modelo .pkl) con fallback a /contenidos/{id}/recomendaciones.
 */
export async function obtenerRecomendaciones(id, { limite = 5 } = {}, signal) {
  try {
    // 1. Intento primario: Tu modelo relacional (.pkl)
    const dataMatriz = await peticion(() =>
      api.get(`/cursos/${id}/relacionados-matriz`, { params: { limite }, signal })
    )

    if (dataMatriz?.recomendaciones && dataMatriz.recomendaciones.length > 0) {
      return {
        contenido_id: id,
        estrategia: 'matriz-similitud-pkl',
        total: dataMatriz.recomendaciones.length,
        items: dataMatriz.recomendaciones.map((item) => {
          const valorDecimal = (item.match_score ?? item.similitud ?? 0) / 100
          return {
            id: item.id,
            titulo: item.titulo,
            categoria: item.categoria,
            origen: item.proveedor || 'Plataforma',
            probabilidad: valorDecimal,
            puntaje: valorDecimal,
            palabras_compartidas: item.tags || [item.categoria],
            informacion_adicional: item.tags || [],
            // Agregados por `scripts/enriquecer_mapeo_cursos.py` en el backend
            // (cruce por titulo contra `Data/cursos_dataset.json`). Un mapeo
            // viejo puede no traerlos todavia, de ahi el default a ''.
            descripcion: item.descripcion || '',
            url: item.url || ''
          }
        })
      }
    }
  } catch (error) {
    if (error.name === 'CanceledError' || error.name === 'AbortError') throw error
  }

  // 2. Fallback: Lógica original por categorías/Jaccard
  return peticion(() =>
    api.get(`/contenidos/${id}/recomendaciones`, { params: { limite }, signal })
  )
}

// ---------------------------------------------------------------------------
// Metricas y metadatos
// ---------------------------------------------------------------------------

/** GET /metricas - resumen basico (compatibilidad; usa /analiticas para el panel). */
export function obtenerMetricas(signal) {
  return peticion(() => api.get('/metricas', { signal }))
}

/**
 * GET /analiticas - panel completo del Dashboard.
 *
 * Superset de `/metricas`: agrega distribucion de confianza, distribucion por
 * origen, actividad temporal y el motor de clasificacion activo.
 */
export function obtenerAnaliticas(signal) {
  return peticion(() => api.get('/analiticas', { signal }))
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

// ---------------------------------------------------------------------------
// Asistente IA
// ---------------------------------------------------------------------------

/**
 * POST /asistente/mensaje - conversa con el Asistente sobre el catalogo.
 *
 * `cursos_relacionados` viene siempre de la busqueda semantica del backend
 * (nunca del texto que redacta el modelo), asi que se reutiliza `mapearCurso`
 * para que las tarjetas de curso sean identicas a las del resto de la app.
 *
 * @param {string} mensaje
 * @param {{rol:string, texto:string}[]} historial
 */
export async function enviarMensajeAsistente(mensaje, historial = []) {
  const data = await peticion(() => api.post('/asistente/mensaje', { mensaje, historial }))
  return {
    respuesta: data.respuesta ?? '',
    cursosRelacionados: (data.cursos_relacionados ?? []).map(mapearCurso),
    motor: data.motor ?? 'desconocido',
    disponible: Boolean(data.disponible),
  }
}

/**
 * GET /asistente/estado - diagnostico (permite distinguir "sin API key" de
 * "catalogo caido" antes de dejar escribir al usuario).
 */
export function obtenerEstadoAsistente(signal) {
  return peticion(() => api.get('/asistente/estado', { signal }))
}

export default api