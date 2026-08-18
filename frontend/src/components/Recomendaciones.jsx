import { Sparkles, ArrowRight, Link2 } from 'lucide-react'
import CategoryBadge from './CategoryBadge'
import { Skeleton } from './Loaders'
import { aPorcentaje, colorDeCategoria } from '../data/categorias'

/**
 * Lista de contenido relacionado.
 *
 * Consume la respuesta de `GET /contenidos/{id}/recomendaciones`. Cada item
 * muestra las `palabras_compartidas` que devuelve el backend, para que la
 * recomendacion se explique sola en vez de mostrar un puntaje opaco.
 *
 * @param {object[]} recomendaciones Items del endpoint.
 * @param {string}   [estrategia]    Motor que las produjo (trazabilidad).
 * @param {boolean}  cargando
 * @param {string}   error
 * @param {Function} [onAbrir]       Callback al pulsar una recomendacion.
 */
export default function Recomendaciones({
  recomendaciones = [],
  estrategia = '',
  cargando = false,
  error = '',
  onAbrir,
}) {
  return (
    <section aria-labelledby="titulo-recomendaciones">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3
          id="titulo-recomendaciones"
          className="flex items-center gap-2 text-sm font-semibold text-mist-100"
        >
          <Sparkles size={15} className="text-brand-400" aria-hidden="true" />
          Contenido relacionado
        </h3>
        {estrategia && !cargando && (
          <span className="hidden text-[11px] text-mist-400 sm:inline" title="Motor de recomendación">
            {estrategia}
          </span>
        )}
      </div>

      {cargando && (
        <ul className="space-y-2" aria-busy="true">
          {Array.from({ length: 3 }, (_, i) => (
            <li key={i}>
              <Skeleton className="h-[68px] w-full rounded-xl" />
            </li>
          ))}
        </ul>
      )}

      {!cargando && error && (
        <p role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
          {error}
        </p>
      )}

      {!cargando && !error && recomendaciones.length === 0 && (
        <p className="rounded-xl border border-ink-700 bg-ink-900 p-4 text-sm text-mist-500">
          Todavía no encontramos contenido parecido. Analiza más cursos y AthenIA
          empezará a relacionarlos.
        </p>
      )}

      {!cargando && !error && recomendaciones.length > 0 && (
        <ul className="space-y-2">
          {recomendaciones.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onAbrir?.(item)}
                disabled={!onAbrir}
                className="group w-full rounded-xl border border-ink-700 bg-ink-900 p-3.5 text-left transition-colors hover:border-brand-500/50 disabled:cursor-default disabled:hover:border-ink-700"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-mist-100">{item.titulo}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <CategoryBadge categoria={item.categoria} tamano="sm" />
                      {item.origen && (
                        <span className="text-[11px] text-mist-400">{item.origen}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    <span
                      className="rounded-lg px-2 py-1 text-[11px] font-bold"
                      style={{
                        backgroundColor: `${colorDeCategoria(item.categoria)}1f`,
                        color: colorDeCategoria(item.categoria),
                      }}
                      title={`Relevancia: ${aPorcentaje(item.puntaje)}%`}
                    >
                      {aPorcentaje(item.puntaje)}%
                    </span>
                    {onAbrir && (
                      <ArrowRight
                        size={15}
                        className="text-mist-500 transition-colors group-hover:text-brand-400"
                        aria-hidden="true"
                      />
                    )}
                  </div>
                </div>

                {/* La evidencia: por que se recomendo este contenido. */}
                {item.palabras_compartidas?.length > 0 && (
                  <p className="mt-2.5 flex flex-wrap items-center gap-1.5 text-[11px] text-mist-400">
                    <Link2 size={11} aria-hidden="true" />
                    <span>Comparten:</span>
                    {item.palabras_compartidas.slice(0, 4).map((palabra) => (
                      <span
                        key={palabra}
                        className="rounded border border-ink-700 px-1.5 py-0.5 text-brand-300"
                      >
                        {palabra}
                      </span>
                    ))}
                  </p>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
