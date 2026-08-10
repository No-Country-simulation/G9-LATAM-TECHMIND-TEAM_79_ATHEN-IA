import { useCallback, useEffect, useState } from 'react'

/**
 * Historial de busquedas recientes, persistido en `localStorage`.
 *
 * Sobrevive a recargas de pagina y a cerrar el navegador, que es lo que hace
 * util la funcion: si el usuario buscó "kubernetes" ayer, quiere volver a esa
 * consulta con un clic, no reescribirla.
 *
 * Se guarda solo el termino de busqueda y su marca temporal — nada sensible.
 */

const CLAVE = 'athenia:historial-busquedas'
const MAXIMO = 8

/** Lee y valida el historial guardado. Ante cualquier problema, empieza limpio. */
function leerDeStorage() {
  try {
    const crudo = window.localStorage.getItem(CLAVE)
    if (!crudo) return []

    const datos = JSON.parse(crudo)
    if (!Array.isArray(datos)) return []

    // Se filtra por forma esperada: un localStorage manipulado a mano (o de
    // una version anterior del formato) no debe romper el render.
    return datos
      .filter((e) => e && typeof e.termino === 'string' && e.termino.trim())
      .slice(0, MAXIMO)
  } catch {
    // localStorage puede lanzar en modo privado de Safari o si el JSON esta
    // corrupto. Degradar a "sin historial" es preferible a tumbar la vista.
    return []
  }
}

function escribirEnStorage(entradas) {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(entradas))
  } catch {
    // Cuota llena o storage deshabilitado: el historial deja de persistir
    // pero la busqueda sigue funcionando con normalidad.
  }
}

/**
 * Borra el historial persistido, sin necesidad de un componente React.
 *
 * La usa "Cerrar sesion" desde el Sidebar: al no ser un hook, puede llamarse
 * desde cualquier handler. Los componentes que tengan el hook montado releen
 * el storage la proxima vez que se monten.
 */
export function limpiarHistorialBusquedas() {
  try {
    window.localStorage.removeItem(CLAVE)
  } catch {
    // Sin storage no habia nada que borrar.
  }
}

export function useHistorialBusquedas() {
  // Inicializador perezoso: `leerDeStorage` corre una sola vez, no en cada render.
  const [entradas, setEntradas] = useState(leerDeStorage)

  useEffect(() => {
    escribirEnStorage(entradas)
  }, [entradas])

  /**
   * Registra un termino. Si ya existia lo mueve al frente en vez de duplicarlo,
   * para que el historial refleje uso reciente y no primera vez.
   */
  const registrar = useCallback((termino) => {
    const limpio = termino.trim()
    if (!limpio) return

    setEntradas((previas) => {
      const sinDuplicado = previas.filter(
        (e) => e.termino.toLowerCase() !== limpio.toLowerCase(),
      )
      return [{ termino: limpio, momento: Date.now() }, ...sinDuplicado].slice(0, MAXIMO)
    })
  }, [])

  const eliminar = useCallback((termino) => {
    setEntradas((previas) => previas.filter((e) => e.termino !== termino))
  }, [])

  const limpiar = useCallback(() => setEntradas([]), [])

  return { entradas, registrar, eliminar, limpiar }
}

export default useHistorialBusquedas
