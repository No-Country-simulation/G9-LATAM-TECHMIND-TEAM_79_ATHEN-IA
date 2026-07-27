import { useCallback, useEffect, useRef, useState } from 'react'
import { obtenerContenidos, obtenerMetricas } from '../services/api'

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
