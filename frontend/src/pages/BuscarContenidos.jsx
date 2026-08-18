import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, X, SearchX, AlertCircle } from 'lucide-react'
import CourseCard from '../components/CourseCard'
import CategoryBadge from '../components/CategoryBadge'
import ContentDetail from '../components/ContentDetail'
import SearchHistory from '../components/SearchHistory'
import { SkeletonGrid, Spinner, Skeleton } from '../components/Loaders'
import { useCategorias, useContenidos } from '../hooks/useContenidos'
import { useHistorialBusquedas } from '../hooks/useHistorialBusquedas'

const FILTRO_TODOS = 'Todos'

// Un término se registra en el historial solo tras esta pausa sin escribir.
// Sin ella, teclear "docker" guardaría "d", "do", "doc"... como 6 búsquedas.
const MS_ANTES_DE_REGISTRAR = 1200

/**
 * Vista "Buscar Contenidos".
 *
 * Filtra en tiempo real el historial real del backend (`GET /contenidos`):
 * cada tecla dispara una consulta con debounce, y el filtro por categoria se
 * aplica del lado del servidor. El termino vive en la query string (`?q=`)
 * para que el buscador del Header pueda navegar hasta aqui y los resultados
 * sean compartibles por URL.
 */
export default function BuscarContenidos() {
  const [parametros, setParametros] = useSearchParams()
  const consultaUrl = parametros.get('q') ?? ''

  const [consulta, setConsulta] = useState(consultaUrl)
  const [categoriaActiva, setCategoriaActiva] = useState(FILTRO_TODOS)

  // Las categorias vienen del motor activo, no cableadas en el frontend.
  const { categorias, cargando: cargandoCategorias } = useCategorias()

  // Mantiene el input sincronizado cuando la URL cambia desde el Header.
  useEffect(() => setConsulta(consultaUrl), [consultaUrl])

  // Refleja el termino en la URL sin apilar entradas en el historial.
  useEffect(() => {
    const termino = consulta.trim()
    if (termino === consultaUrl) return

    const temporizador = setTimeout(
      () => setParametros(termino ? { q: termino } : {}, { replace: true }),
      300,
    )
    return () => clearTimeout(temporizador)
  }, [consulta, consultaUrl, setParametros])

  const filtros = useMemo(
    () => ({
      buscar: consulta.trim(),
      categoria: categoriaActiva === FILTRO_TODOS ? '' : categoriaActiva,
    }),
    [consulta, categoriaActiva],
  )

  const { items, total, cargando, error } = useContenidos(filtros)

  // --- Historial de búsquedas (persistido en localStorage) ------------------
  const historial = useHistorialBusquedas()
  const { registrar } = historial

  // Solo se registra cuando la búsqueda "reposa" y además devolvió resultados:
  // guardar términos que no encontraron nada no le sirve al usuario.
  useEffect(() => {
    const termino = consulta.trim()
    if (!termino || cargando || total === 0) return undefined

    const temporizador = setTimeout(() => registrar(termino), MS_ANTES_DE_REGISTRAR)
    return () => clearTimeout(temporizador)
  }, [consulta, cargando, total, registrar])

  // --- Detalle + recomendaciones -------------------------------------------
  const [seleccionado, setSeleccionado] = useState(null)

  /**
   * Abre el detalle de una recomendación. Como el item recomendado solo trae
   * campos resumidos, se busca la versión completa en los resultados ya
   * cargados; si no está (por filtros activos), se usa lo que vino.
   */
  const abrirRelacionado = useCallback(
    (recomendado) => {
      const completo = items.find((i) => i.id === recomendado.id)
      setSeleccionado(completo ?? recomendado)
    },
    [items],
  )

  const limpiarBusqueda = () => setConsulta('')

  const hayFiltros = Boolean(filtros.buscar) || categoriaActiva !== FILTRO_TODOS

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-tinta-900">Buscar Contenidos</h1>
        <p className="mt-1 text-sm text-tinta-500">
          Encuentra cursos, temas y tecnologias en tu biblioteca analizada.
        </p>
      </div>

      {/* --- Buscador en tiempo real --- */}
      <div className="relative">
        <Search
          size={17}
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-tinta-500"
        />
        <input
          type="text"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder="Ej: docker, spring boot, python..."
          aria-label="Buscar contenidos"
          className="input-base px-11"
        />

        <div className="absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-2">
          {cargando && <Spinner tamano={15} />}
          {consulta && (
            <button
              type="button"
              onClick={limpiarBusqueda}
              className="rounded-md p-0.5 text-tinta-500 hover:text-tinta-900"
              aria-label="Limpiar busqueda"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* --- Búsquedas recientes (localStorage) --- */}
      <SearchHistory
        entradas={historial.entradas}
        onSeleccionar={setConsulta}
        onEliminar={historial.eliminar}
        onLimpiar={historial.limpiar}
      />

      {/* --- Filtros por categoria (del motor activo) --- */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setCategoriaActiva(FILTRO_TODOS)}
          aria-pressed={categoriaActiva === FILTRO_TODOS}
          className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-colors ${
            categoriaActiva === FILTRO_TODOS
              ? 'bg-brand-600 text-white'
              : 'border border-linea text-tinta-700 hover:border-brand-500 hover:text-tinta-900'
          }`}
        >
          Todos
        </button>

        {cargandoCategorias
          ? Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-[26px] w-28 rounded-lg" />
            ))
          : categorias.map((categoria) => {
              const activa = categoria === categoriaActiva

              return (
                <button
                  key={categoria}
                  type="button"
                  onClick={() => setCategoriaActiva(activa ? FILTRO_TODOS : categoria)}
                  aria-pressed={activa}
                  className={`rounded-lg transition-opacity ${
                    activa ? 'ring-2 ring-brand-400' : 'opacity-85 hover:opacity-100'
                  }`}
                >
                  <CategoryBadge categoria={categoria} />
                </button>
              )
            })}
      </div>

      {/* --- Estado de la consulta --- */}
      <p className="text-sm text-tinta-500">
        {cargando ? (
          'Buscando...'
        ) : (
          <>
            {total} resultado{total === 1 ? '' : 's'}
            {hayFiltros && (
              <>
                {filtros.buscar && (
                  <>
                    {' '}
                    para <span className="text-tinta-900">"{filtros.buscar}"</span>
                  </>
                )}
                {categoriaActiva !== FILTRO_TODOS && (
                  <>
                    {' '}
                    en <span className="text-tinta-900">{categoriaActiva}</span>
                  </>
                )}
              </>
            )}
          </>
        )}
      </p>

      {/* --- Error de conexion --- */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5"
        >
          <AlertCircle size={17} className="mt-0.5 shrink-0 text-rose-600" />
          <p className="text-sm text-rose-700">{error}</p>
        </div>
      )}

      {/* --- Resultados --- */}
      {cargando && items.length === 0 ? (
        <SkeletonGrid cantidad={6} />
      ) : items.length > 0 ? (
        <div
          className={`grid gap-4 transition-opacity md:grid-cols-2 xl:grid-cols-3 ${
            cargando ? 'opacity-75' : 'opacity-100'
          }`}
        >
          {items.map((contenido) => (
            <CourseCard key={contenido.id} contenido={contenido} onVer={setSeleccionado} />
          ))}
        </div>
      ) : (
        !error && (
          <div className="card flex flex-col items-center justify-center p-12 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-lienzo text-tinta-500">
              <SearchX size={26} />
            </span>
            <p className="mt-4 text-sm font-medium text-tinta-700">Sin resultados</p>
            <p className="mt-1 max-w-sm text-sm text-tinta-500">
              {hayFiltros
                ? 'No encontramos contenido que coincida. Prueba con otro termino o quita el filtro de categoria.'
                : 'Aun no has analizado contenido. Ve a "Agregar Curso" para empezar.'}
            </p>
          </div>
        )
      )}

      {/* --- Detalle lateral con recomendaciones --- */}
      <ContentDetail
        contenido={seleccionado}
        onCerrar={() => setSeleccionado(null)}
        onAbrirOtro={abrirRelacionado}
      />
    </div>
  )
}
