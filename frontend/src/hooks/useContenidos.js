import { useCallback, useEffect, useRef, useState } from 'react'
import {
  buscarCursos,
  obtenerAnaliticas,
  obtenerCategorias,
  obtenerCategoriasCursos,
  obtenerContenidos,
  obtenerCursos,
  obtenerMetricas,
  obtenerRecomendaciones,
} from '../services/api'
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

/**
 * Panel completo de analiticas (`GET /analiticas`).
 *
 * Reemplaza a `useMetricas` en el Dashboard: trae los mismos totales mas
 * distribucion de confianza, origenes y actividad temporal, en una sola
 * peticion.
 */
export function useAnaliticas() {
  const [analiticas, setAnaliticas] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  const [recarga, setRecarga] = useState(0)
  const refrescar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    const controlador = new AbortController()
    setCargando(true)

    obtenerAnaliticas(controlador.signal)
      .then((data) => {
        setAnaliticas(data)
        setError('')
      })
      .catch((fallo) => {
        if (controlador.signal.aborted) return
        setError(fallo.message)
        setAnaliticas(null)
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false)
      })

    return () => controlador.abort()
  }, [recarga])

  return { analiticas, cargando, error, refrescar }
}

/**
 * Recomendaciones para un contenido (`GET /contenidos/{id}/recomendaciones`).
 *
 * Con `contenidoId` nulo no consulta nada — asi el panel de detalle puede
 * montar el hook incondicionalmente (las reglas de hooks prohiben llamarlo
 * dentro de un `if`) y activarlo solo cuando hay un contenido seleccionado.
 */
export function useRecomendaciones(contenidoId, { limite = 5 } = {}) {
  const [recomendaciones, setRecomendaciones] = useState([])
  const [estrategia, setEstrategia] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (contenidoId == null) {
      setRecomendaciones([])
      setEstrategia('')
      setError('')
      setCargando(false)
      return undefined
    }

    const controlador = new AbortController()
    setCargando(true)

    obtenerRecomendaciones(contenidoId, { limite }, controlador.signal)
      .then((data) => {
        setRecomendaciones(data.items)
        setEstrategia(data.estrategia)
        setError('')
      })
      .catch((fallo) => {
        if (controlador.signal.aborted) return
        setError(fallo.message)
        setRecomendaciones([])
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false)
      })

    return () => controlador.abort()
  }, [contenidoId, limite])

  return { recomendaciones, estrategia, cargando, error }
}

/**
 * Catalogo de cursos (+8.000 registros indexados en ChromaDB).
 *
 * Elige el endpoint segun haya consulta o no, que es la diferencia clave con
 * `useContenidos`:
 *
 *   con `buscar`  -> GET /cursos/buscar  (semantica, con match_score)
 *   sin `buscar`  -> GET /cursos         (navegacion, match_score null)
 *
 * Esa segunda rama es la que faltaba: sin ella, la vista sin consulta caia al
 * historial de analisis (`GET /contenidos`, 8 registros de demo) y parecia que
 * el catalogo no estuviera conectado al frontend.
 *
 * @param {{categoria?: string, buscar?: string, limite?: number, debounceMs?: number}} filtros
 */
export function useCursos({ categoria, buscar, limite = 24, debounceMs = 300, activo = true } = {}) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  const termino = (buscar ?? '').trim()

  useEffect(() => {
    // `activo: false` deja el hook montado pero inerte. Las reglas de hooks
    // prohiben llamarlo dentro de un `if`, asi que la vista que alterna entre
    // catalogo e historial lo monta siempre y apaga el que no esta en uso.
    if (!activo) {
      setCargando(false)
      return undefined
    }

    const controlador = new AbortController()
    setCargando(true)

    // Sin termino no hace falta debounce: no es una respuesta al teclado.
    const espera = termino ? debounceMs : 0

    const temporizador = setTimeout(async () => {
      try {
        const data = termino
          ? await buscarCursos({ q: termino, limite }, controlador.signal)
          : await obtenerCursos({ categoria, limite }, controlador.signal)

        // `/cursos/buscar` no admite filtro por categoria (el umbral semantico
        // ya es el criterio). Si hay ambos, se filtra en cliente sobre un
        // conjunto pequeno —como mucho `limite` elementos—.
        const filtrados =
          termino && categoria ? data.items.filter((c) => c.categoria === categoria) : data.items

        setItems(filtrados)
        setTotal(termino ? filtrados.length : data.total)
        setError('')
      } catch (fallo) {
        if (controlador.signal.aborted) return
        setError(fallo.message)
        setItems([])
        setTotal(0)
      } finally {
        if (!controlador.signal.aborted) setCargando(false)
      }
    }, espera)

    return () => {
      clearTimeout(temporizador)
      controlador.abort()
    }
  }, [categoria, termino, limite, debounceMs, activo])

  return { items, total, cargando, error, hayConsulta: Boolean(termino) }
}

/**
 * Categorias reales del catalogo, con su conteo (`GET /cursos/categorias`).
 *
 * No se cablean en el frontend ni se reutilizan las del clasificador: son
 * catalogos distintos, y filtrar por una categoria ausente del indice daria
 * siempre cero resultados.
 */
export function useCategoriasCursos() {
  const [categorias, setCategorias] = useState([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    const controlador = new AbortController()

    obtenerCategoriasCursos(controlador.signal)
      .then((lista) => {
        if (!controlador.signal.aborted) setCategorias(lista)
      })
      .catch(() => {
        if (!controlador.signal.aborted) setCategorias([])
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false)
      })

    return () => controlador.abort()
  }, [])

  return { categorias, cargando }
}
