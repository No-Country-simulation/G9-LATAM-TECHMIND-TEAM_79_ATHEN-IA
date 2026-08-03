import { useCallback, useEffect, useRef, useState } from 'react'
import { obtenerCategorias, obtenerContenidos, obtenerMetricas } from '../services/api'
import { CATEGORIAS_REGLAS } from '../data/categorias'

/**
 * Historial de analisis con filtros aplicados en el backend.
 *
 * Cada cambio de `categoria` o `buscar` dispara una consulta nueva, con
 * debounce para no golpear la API en cada tecla. Las peticiones que quedan
 * obsoletas se cancelan con `AbortController`, de modo que una respuesta lenta
 * no puede sobrescribir a una mas reciente.
 *
 * @param {{categoria?: string, buscar?: string, limite?: number, debounceMs?: number}} filtros
 */
export function useContenidos({ categoria, buscar, limite, debounceMs = 250 } = {}) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  // Cambiar este valor fuerza un refetch desde fuera del hook.
  const [recarga, setRecarga] = useState(0)
  const refrescar = useCallback(() => setRecarga((n) => n + 1), [])

  // Solo se muestra el spinner a pantalla completa en la primera carga; los
  // refiltrados posteriores usan un indicador discreto.
  const primeraCarga = useRef(true)

  useEffect(() => {
    const controlador = new AbortController()
    setCargando(true)

    const temporizador = setTimeout(async () => {
      try {
        const data = await obtenerContenidos({ categoria, buscar, limite }, controlador.signal)
        setItems(data.items)
        setTotal(data.total)
        setError('')
      } catch (fallo) {
        // Una peticion cancelada no es un error que deba ver el usuario.
        if (controlador.signal.aborted) return
        setError(fallo.message)
        setItems([])
        setTotal(0)
      } finally {
        if (!controlador.signal.aborted) {
          setCargando(false)
          primeraCarga.current = false
        }
      }
    }, debounceMs)

    return () => {
      clearTimeout(temporizador)
      controlador.abort()
    }
  }, [categoria, buscar, limite, debounceMs, recarga])

  return { items, total, cargando, error, refrescar, esPrimeraCarga: primeraCarga.current }
}

/**
 * Catalogo de categorias del motor activo (`GET /categorias`).
 *
 * Es importante que venga del backend y no este cableado en el frontend: las
 * clases del modelo entrenado (`clasificador_cursos.pkl`) no coinciden con las
 * de la taxonomia por reglas. Si se cablearan, los filtros mostrarian
 * categorias que el motor activo nunca devuelve y siempre darian 0 resultados.
 */
export function useCategorias() {
  const [categorias, setCategorias] = useState([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    const controlador = new AbortController()

    obtenerCategorias()
      .then((lista) => {
        if (!controlador.signal.aborted) setCategorias(lista)
      })
      .catch(() => {
        // Sin backend se muestran las de reglas para que la UI siga navegable.
        if (!controlador.signal.aborted) setCategorias(CATEGORIAS_REGLAS)
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false)
      })

    return () => controlador.abort()
  }, [])

  return { categorias, cargando }
}

/**
 * Metricas agregadas del historial (`GET /metricas`).
 * Alimenta las tarjetas y el grafico del Dashboard.
 */
export function useMetricas() {
  const [metricas, setMetricas] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  const [recarga, setRecarga] = useState(0)
  const refrescar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    const controlador = new AbortController()
    setCargando(true)

    obtenerMetricas(controlador.signal)
      .then((data) => {
        setMetricas(data)
        setError('')
      })
      .catch((fallo) => {
        if (controlador.signal.aborted) return
        setError(fallo.message)
        setMetricas(null)
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false)
      })

    return () => controlador.abort()
  }, [recarga])

  return { metricas, cargando, error, refrescar }
}
