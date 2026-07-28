/**
 * Identidad visual de las categorias.
 *
 * Los datos ya no viven aqui: el catalogo real llega del backend
 * (`GET /contenidos`). Este modulo solo mapea cada categoria a su color de
 * acento, para que badges, graficos y tarjetas hablen el mismo idioma.
 */

export const COLORES_CATEGORIA = {
  Backend: '#8b5cf6',
  'Data Science': '#38bdf8',
  DevOps: '#34d399',
  Frontend: '#fbbf24',
  Cloud: '#f472b6',
  'Base de Datos': '#fb7185',
  Otros: '#8f86ad',
}

const COLOR_POR_DEFECTO = COLORES_CATEGORIA.Otros

/** Devuelve el color de acento de una categoria (gris neutro si es desconocida). */
export function colorDeCategoria(categoria) {
  return COLORES_CATEGORIA[categoria] ?? COLOR_POR_DEFECTO
}

/**
 * Estilos inline para superficies tenidas por categoria.
 * Se usa `style` en vez de clases porque Tailwind no puede generar utilidades
 * a partir de valores dinamicos en tiempo de ejecucion.
 */
export function estilosDeCategoria(categoria, { borde = false } = {}) {
  const color = colorDeCategoria(categoria)
  return {
    color,
    backgroundColor: `${color}1f`,
    ...(borde ? { border: `1px solid ${color}59` } : {}),
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
