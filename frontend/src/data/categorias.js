/**
 * Identidad visual de las categorias.
 *
 * Los datos ya no viven aqui: el catalogo real llega del backend
 * (`GET /contenidos`). Este modulo solo mapea cada categoria a su color de
 * acento, para que badges, graficos y tarjetas hablen el mismo idioma.
 */

/**
 * Colores por categoria.
 *
 * Conviven DOS taxonomias porque el backend puede responder con cualquiera de
 * sus dos motores (ver `GET /salud`):
 *
 *   - `modelo_ml_real`      -> las 5 clases de `clasificador_cursos.pkl`
 *   - `clasificador_reglas` -> las categorias de la taxonomia interna (fallback)
 *
 * Mantener ambas evita que las tarjetas pierdan color al cambiar de motor.
 */
export const COLORES_CATEGORIA = {
  // --- Clases del modelo entrenado (Data Science, Semana 3) ---------------
  'Desarrollo de Software y Web': '#8b5cf6',
  'Ciencia de Datos y Analítica': '#38bdf8',
  'Cloud Computing y DevOps': '#34d399',
  'Inteligencia Artificial y ML': '#f472b6',
  'Ciberseguridad y Redes': '#fb7185',

  // --- Taxonomia del clasificador por reglas (fallback) -------------------
  Backend: '#8b5cf6',
  'Data Science': '#38bdf8',
  DevOps: '#34d399',
  Frontend: '#fbbf24',
  Cloud: '#f472b6',
  'Base de Datos': '#fb7185',
  Otros: '#8f86ad',
}

/**
 * Categorias del clasificador por reglas.
 * Solo se usan como respaldo si `GET /categorias` no responde.
 */
export const CATEGORIAS_REGLAS = [
  'Backend',
  'Frontend',
  'Data Science',
  'DevOps',
  'Cloud',
  'Base de Datos',
  'Otros',
]

/**
 * Variante oscura de cada acento, para TEXTO sobre fondo claro.
 *
 * `COLORES_CATEGORIA` se diseño para el tema oscuro, donde los tonos claros
 * resaltan. Sobre blanco esos mismos tonos fallan contraste de forma grave
 * (sky-400 da 2.1:1, emerald-400 1.9:1, muy por debajo del 4.5:1 de AA).
 *
 * Se conservan los originales para RELLENOS de gráfico —una porción de dona es
 * un elemento gráfico, no texto— y se usa esta escala para las etiquetas.
 * Todos los valores superan 4.5:1 sobre `#ffffff`.
 */
export const COLORES_TEXTO_CATEGORIA = {
  'Desarrollo de Software y Web': '#6d28d9',
  'Ciencia de Datos y Analítica': '#0369a1',
  'Cloud Computing y DevOps': '#047857',
  'Inteligencia Artificial y ML': '#be185d',
  'Ciberseguridad y Redes': '#be123c',

  Backend: '#6d28d9',
  'Data Science': '#0369a1',
  DevOps: '#047857',
  Frontend: '#b45309',
  Cloud: '#be185d',
  'Base de Datos': '#be123c',
  Ciberseguridad: '#be123c',
  Otros: '#475569',
}

const COLOR_POR_DEFECTO = COLORES_CATEGORIA.Otros
const COLOR_TEXTO_POR_DEFECTO = '#475569'

/** Color de la etiqueta de una categoria sobre fondo claro. */
export function colorTextoDeCategoria(categoria) {
  return COLORES_TEXTO_CATEGORIA[categoria] ?? COLOR_TEXTO_POR_DEFECTO
}

// Paleta de reserva para categorias que no estan en el mapa: si Data Science
// reentrena con clases nuevas, siguen recibiendo un color estable en vez de
// gris. Se elige de forma determinista a partir del nombre.
const PALETA_RESERVA = [
  '#8b5cf6',
  '#38bdf8',
  '#34d399',
  '#fbbf24',
  '#f472b6',
  '#fb7185',
  '#a78bfa',
  '#22d3ee',
]

/**
 * Color de acento de una categoria.
 *
 * Si no esta mapeada, deriva un color estable de su nombre en vez de devolver
 * gris, para que categorias distintas nunca se vean iguales.
 */
export function colorDeCategoria(categoria) {
  if (!categoria) return COLOR_POR_DEFECTO
  if (COLORES_CATEGORIA[categoria]) return COLORES_CATEGORIA[categoria]

  // Hash simple y determinista: el mismo nombre siempre da el mismo color.
  let acumulado = 0
  for (let i = 0; i < categoria.length; i += 1) {
    acumulado = (acumulado * 31 + categoria.charCodeAt(i)) % 997
  }
  return PALETA_RESERVA[acumulado % PALETA_RESERVA.length]
}

/**
 * Estilos inline para superficies tenidas por categoria.
 * Se usa `style` en vez de clases porque Tailwind no puede generar utilidades
 * a partir de valores dinamicos en tiempo de ejecucion.
 */
export function estilosDeCategoria(categoria, { borde = false } = {}) {
  const acento = colorDeCategoria(categoria)
  return {
    // El texto usa la variante oscura; el fondo, un tinte del acento al 14%.
    color: colorTextoDeCategoria(categoria),
    backgroundColor: `${acento}24`,
    ...(borde ? { border: `1px solid ${acento}55` } : {}),
  }
}

/** Formatea una probabilidad 0-1 como porcentaje entero. */
export function aPorcentaje(probabilidad) {
  return Math.round((probabilidad ?? 0) * 100)
}

/** Fecha ISO -> "27 jul 2026" (o cadena vacia si no hay fecha). */
export function formatearFecha(iso) {
  if (!iso) return ''
  const fecha = new Date(iso)
  if (Number.isNaN(fecha.getTime())) return ''
  return fecha.toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}
