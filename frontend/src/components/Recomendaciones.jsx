import { Sparkles, ArrowRight, Link2, ExternalLink } from 'lucide-react'
import CategoryBadge from './CategoryBadge'
import { Skeleton } from './Loaders'
import { aPorcentaje, estilosDeCategoria } from '../data/categorias'

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
          className="flex items-center gap-2 text-sm font-semibold text-tinta-900"
        >
          <Sparkles size={15} className="text-brand-600" aria-hidden="true" />
          Contenido relacionado
        </h3>
        {estrategia && !cargando && (
          <span className="hidden text-[11px] text-tinta-600 sm:inline" title="Motor de recomendación">
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
        <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </p>
      )}

      {!cargando && !error && recomendaciones.length === 0 && (
        <p className="rounded-xl border border-linea bg-panel-suave p-4 text-sm text-tinta-500">
          Todavía no encontramos contenido parecido. Analiza más cursos y AthenIA
          empezará a relacionarlos.
        </p>
      )}

      {!cargando && !error && recomendaciones.length > 0 && (
        <ul className="space-y-2">
          {recomendaciones.map((item) => (
            <li
              key={item.id}
              className="group rounded-xl border border-linea bg-panel-suave p-3.5 transition-colors hover:border-brand-500/50"
            >
              <button
                type="button"
                onClick={() => onAbrir?.(item)}
                disabled={!onAbrir}
                className="w-full text-left disabled:cursor-default"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-tinta-900">{item.titulo}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <CategoryBadge categoria={item.categoria} tamano="sm" />
                      {item.origen && (
                        <span className="text-[11px] text-tinta-600">{item.origen}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    <span
                      className="rounded-lg px-2 py-1 text-[11px] font-bold"
                      style={estilosDeCategoria(item.categoria)}
                      title={`Relevancia: ${aPorcentaje(item.puntaje)}%`}
                    >
                      {aPorcentaje(item.puntaje)}%
                    </span>
                    {onAbrir && (
                      <ArrowRight
                        size={15}
                        className="text-tinta-500 transition-colors group-hover:text-brand-600"
                        aria-hidden="true"
                      />
                    )}
                  </div>
                </div>
              </button>

              {/* Resumen del curso — mismo dato que ya muestra el buscador
                  (`descripcion`), agregado al Modelo Relacional via
                  `scripts/enriquecer_mapeo_cursos.py`. */}
              {item.descripcion && (
                <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-tinta-700">
                  {item.descripcion}
                </p>
              )}

              {/* La evidencia: por que se recomendo este contenido. */}
              {item.palabras_compartidas?.length > 0 && (
                <p className="mt-2.5 flex flex-wrap items-center gap-1.5 text-[11px] text-tinta-600">
                  <Link2 size={11} aria-hidden="true" />
                  <span>Comparten:</span>
                  {item.palabras_compartidas.slice(0, 4).map((palabra) => (
                    <span
                      key={palabra}
                      className="rounded border border-linea px-1.5 py-0.5 text-brand-700"
                    >
                      {palabra}
                    </span>
                  ))}
                </p>
              )}

              {/* Enlace directo a la plataforma, igual que las tarjetas del
                  buscador (`CourseCard`). Fuera del <button> a proposito: un
                  <a> dentro de un <button> es HTML invalido y duplicaria el
                  click (abriria el detalle Y el enlace a la vez). */}
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(evento) => evento.stopPropagation()}
                  className="mt-2.5 inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 transition-colors hover:text-brand-700"
                >
                  Ver curso en {item.origen || 'la plataforma'}
                  <ExternalLink size={12} aria-hidden="true" />
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
