import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Layers, AlertCircle } from 'lucide-react'
import { Skeleton } from '../components/Loaders'
import { useAnaliticas, useCategoriasCursos } from '../hooks/useContenidos'
import { obtenerCategorias } from '../services/api'
import { CATEGORIAS_REGLAS, estilosDeCategoria } from '../data/categorias'

/**
 * Vista "Categorias".
 *
 * Cruza tres fuentes reales del backend:
 *
 *   GET /categorias        clases que el clasificador puede predecir
 *   GET /cursos/categorias cuantos cursos del catalogo hay en cada una
 *   GET /analiticas        cuantos contenidos analizados hay en cada una
 *
 * Las dos primeras son catalogos distintos y no siempre coinciden: el
 * clasificador puede predecir una clase que el indice apenas contenga. Se
 * muestran ambas cifras en vez de elegir una, porque significan cosas
 * distintas. Si el backend no responde, cae al catalogo local para que la demo
 * siga siendo navegable.
 */
export default function Categorias() {
  const [catalogo, setCatalogo] = useState([])
  const [cargandoCatalogo, setCargandoCatalogo] = useState(true)
  const [sinBackend, setSinBackend] = useState(false)

  const { analiticas } = useAnaliticas()
  const { categorias: categoriasCatalogo } = useCategoriasCursos()

  // Conteo por categoria a partir de las metricas del historial.
  const conteo = Object.fromEntries(
    (analiticas?.distribucion_categorias ?? []).map((d) => [d.etiqueta, d.cantidad]),
  )

  // Conteo real de cursos indexados por categoria (+8.000 en total).
  const cursosPorCategoria = Object.fromEntries(
    categoriasCatalogo.map((c) => [c.nombre, c.total]),
  )

  useEffect(() => {
    let vigente = true

    obtenerCategorias()
      .then((categorias) => {
        if (vigente) setCatalogo(categorias)
      })
      .catch(() => {
        if (!vigente) return
        setSinBackend(true)
        setCatalogo(CATEGORIAS_REGLAS)
      })
      .finally(() => {
        if (vigente) setCargandoCatalogo(false)
      })

    return () => {
      vigente = false
    }
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-tinta-900">Categorias</h1>
        <p className="mt-1 text-sm text-tinta-500">
          Areas de conocimiento que AthenIA reconoce al clasificar contenido.
        </p>
      </div>

      {sinBackend && (
        <div
          role="alert"
          className="flex items-center gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5"
        >
          <AlertCircle size={17} className="shrink-0 text-amber-600" />
          <p className="text-sm text-amber-800">
            No se pudo consultar el catalogo del backend. Mostrando las categorias locales.
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {cargandoCatalogo
          ? Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-[88px] w-full rounded-2xl" />
            ))
          : catalogo.map((categoria) => {
              const cantidad = conteo[categoria] ?? 0
              const cursos = cursosPorCategoria[categoria] ?? 0

              return (
                <Link
                  key={categoria}
                  to={`/buscar?q=${encodeURIComponent(categoria)}`}
                  className="card group flex items-center gap-4 p-5 transition-colors hover:border-brand-500/50"
                >
                  <span
                    className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl"
                    style={estilosDeCategoria(categoria)}
                  >
                    <Layers size={22} />
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-tinta-900">{categoria}</p>
                    <p className="text-xs text-tinta-600">
                      {cursos > 0 && (
                        <>
                          <span className="font-semibold text-tinta-700">{cursos}</span> curso
                          {cursos === 1 ? '' : 's'} en el catalogo
                          <span aria-hidden="true"> · </span>
                        </>
                      )}
                      {cantidad} en tu biblioteca
                    </p>
                  </div>

                  <span className="text-lg font-bold text-tinta-500 group-hover:text-brand-600">
                    {cursos > 0 ? cursos : cantidad}
                  </span>
                </Link>
              )
            })}
      </div>
    </div>
  )
}
