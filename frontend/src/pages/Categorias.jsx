import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Layers, AlertCircle } from 'lucide-react'
import { Skeleton } from '../components/Loaders'
import { useAnaliticas } from '../hooks/useContenidos'
import { obtenerCategorias } from '../services/api'
import { CATEGORIAS_REGLAS, estilosDeCategoria } from '../data/categorias'

/**
 * Vista "Categorias".
 *
 * Cruza el catalogo que el modelo puede predecir (`GET /categorias`) con
 * cuantos contenidos hay de cada una en el historial (`GET /analiticas`).
 * Si el backend no responde, cae al catalogo local para que la demo siga
 * siendo navegable.
 */
export default function Categorias() {
  const [catalogo, setCatalogo] = useState([])
  const [cargandoCatalogo, setCargandoCatalogo] = useState(true)
  const [sinBackend, setSinBackend] = useState(false)

  const { analiticas } = useAnaliticas()

  // Conteo por categoria a partir de las metricas del historial.
  const conteo = Object.fromEntries(
    (analiticas?.distribucion_categorias ?? []).map((d) => [d.etiqueta, d.cantidad]),
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
        <h1 className="text-2xl font-bold tracking-tight text-mist-100">Categorias</h1>
        <p className="mt-1 text-sm text-mist-500">
          Areas de conocimiento que AthenIA reconoce al clasificar contenido.
        </p>
      </div>

      {sinBackend && (
        <div
          role="alert"
          className="flex items-center gap-2.5 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3.5"
        >
          <AlertCircle size={17} className="shrink-0 text-amber-400" />
          <p className="text-sm text-amber-100">
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
                    <p className="truncate text-sm font-semibold text-mist-100">{categoria}</p>
                    <p className="text-xs text-mist-500">
                      {cantidad} contenido{cantidad === 1 ? '' : 's'} en tu biblioteca
                    </p>
                  </div>

                  <span className="text-lg font-bold text-mist-500 group-hover:text-brand-400">
                    {cantidad}
                  </span>
                </Link>
              )
            })}
      </div>
    </div>
  )
}
