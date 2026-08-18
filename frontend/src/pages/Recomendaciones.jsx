import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, AlertCircle, ChevronDown } from 'lucide-react'
import CategoryBadge from '../components/CategoryBadge'
import ListaRecomendaciones from '../components/Recomendaciones'
import ContentDetail from '../components/ContentDetail'
import { Skeleton } from '../components/Loaders'
import { useContenidos, useRecomendaciones } from '../hooks/useContenidos'
import { aPorcentaje } from '../data/categorias'

/**
 * Vista "Recomendaciones".
 *
 * Consume `GET /contenidos/{id}/recomendaciones` sobre un contenido de
 * referencia. Por defecto toma el mas reciente —lo que el usuario acaba de
 * analizar es lo que mas probablemente quiere explorar—, y permite cambiarlo
 * desde un selector.
 *
 * Cada sugerencia muestra las `palabras_compartidas` que devuelve el backend,
 * asi la recomendacion se explica sola.
 */
export default function Recomendaciones() {
  const { items, cargando: cargandoHistorial, error: errorHistorial } = useContenidos({
    debounceMs: 0,
  })

  const [referenciaId, setReferenciaId] = useState(null)

  // El historial llega asincrono: en cuanto hay datos se fija el mas reciente
  // como referencia, salvo que el usuario ya haya elegido otro.
  useEffect(() => {
    if (referenciaId == null && items.length > 0) {
      setReferenciaId(items[0].id)
    }
  }, [items, referenciaId])

  const referencia = items.find((i) => i.id === referenciaId) ?? null

  const { recomendaciones, estrategia, cargando, error } = useRecomendaciones(
    referencia?.id ?? null,
    { limite: 8 },
  )

  const [seleccionado, setSeleccionado] = useState(null)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-tinta-900">
          <Sparkles size={24} className="text-brand-600" aria-hidden="true" />
          Recomendaciones
        </h1>
        <p className="mt-1 text-sm text-tinta-600">
          Contenido relacionado por similitud de tecnologias y categoria.
        </p>
      </div>

      {errorHistorial && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5"
        >
          <AlertCircle size={17} className="mt-0.5 shrink-0 text-rose-600" aria-hidden="true" />
          <p className="text-sm text-rose-700">{errorHistorial}</p>
        </div>
      )}

      {/* --- Estado vacio: no hay nada sobre lo que recomendar --- */}
      {!cargandoHistorial && items.length === 0 && !errorHistorial && (
        <div className="card flex flex-col items-center justify-center p-12 text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-lienzo text-tinta-600">
            <Sparkles size={26} aria-hidden="true" />
          </span>
          <p className="mt-4 text-sm font-medium text-mist-200">Aun no hay recomendaciones</p>
          <p className="mt-1 max-w-sm text-sm text-tinta-600">
            Necesitamos al menos dos contenidos analizados para poder
            relacionarlos entre si.
          </p>
          <Link to="/agregar" className="btn-primary mt-6">
            <Sparkles size={16} aria-hidden="true" />
            Analizar contenido
          </Link>
        </div>
      )}

      {cargandoHistorial && <Skeleton className="h-24 w-full rounded-2xl" />}

      {/* --- Selector de referencia --- */}
      {referencia && (
        <>
          <section className="card p-5">
            <label
              htmlFor="referencia"
              className="mb-2 block text-xs font-medium uppercase tracking-wide text-tinta-600"
            >
              Basado en este contenido
            </label>

            <div className="relative">
              <select
                id="referencia"
                value={referencia.id}
                onChange={(e) => setReferenciaId(Number(e.target.value))}
                className="input-base appearance-none pr-10"
              >
                {items.map((contenido) => (
                  <option key={contenido.id} value={contenido.id}>
                    {contenido.titulo}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={16}
                className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-tinta-600"
                aria-hidden="true"
              />
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <CategoryBadge categoria={referencia.categoria} tamano="sm" />
              <span className="text-xs text-tinta-600">
                Confianza {aPorcentaje(referencia.probabilidad)}%
              </span>
              {referencia.informacion_adicional?.length > 0 && (
                <span className="text-xs text-tinta-600">
                  · {referencia.informacion_adicional.slice(0, 4).join(' · ')}
                </span>
              )}
            </div>
          </section>

          <ListaRecomendaciones
            recomendaciones={recomendaciones}
            estrategia={estrategia}
            cargando={cargando}
            error={error}
            onAbrir={(recomendado) =>
              setSeleccionado(items.find((i) => i.id === recomendado.id) ?? recomendado)
            }
          />
        </>
      )}

      <ContentDetail
        contenido={seleccionado}
        onCerrar={() => setSeleccionado(null)}
        onAbrirOtro={(recomendado) =>
          setSeleccionado(items.find((i) => i.id === recomendado.id) ?? recomendado)
        }
      />
    </div>
  )
}
