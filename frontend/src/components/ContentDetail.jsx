import { useEffect, useRef } from 'react'
import { X, Calendar, Link as LinkIcon, Tag, Gauge } from 'lucide-react'
import CategoryBadge, { KeywordBadge } from './CategoryBadge'
import Recomendaciones from './Recomendaciones'
import { useRecomendaciones } from '../hooks/useContenidos'
import { aPorcentaje, colorDeCategoria, formatearFecha } from '../data/categorias'

/**
 * Panel lateral con el detalle de un contenido y sus recomendaciones.
 *
 * Es un diálogo modal accesible:
 * - `role="dialog"` + `aria-modal` + `aria-labelledby`.
 * - Cierra con `Escape` y con clic en el fondo.
 * - Mueve el foco al panel al abrirse y lo devuelve al elemento previo al cerrar.
 * - Atrapa el `Tab` dentro del panel mientras está abierto.
 *
 * @param {object|null} contenido Item del historial; `null` cierra el panel.
 * @param {Function}    onCerrar
 * @param {Function}    [onAbrirOtro] Navegar a otro contenido desde las recomendaciones.
 */
export default function ContentDetail({ contenido, onCerrar, onAbrirOtro }) {
  const panelRef = useRef(null)
  const focoPrevioRef = useRef(null)

  const abierto = Boolean(contenido)

  const { recomendaciones, estrategia, cargando, error } = useRecomendaciones(
    contenido?.id ?? null,
  )

  // Escape para cerrar + bloqueo del scroll de fondo mientras está abierto.
  useEffect(() => {
    if (!abierto) return undefined

    const alPulsarTecla = (evento) => {
      if (evento.key === 'Escape') {
        evento.stopPropagation()
        onCerrar()
      }
    }

    document.addEventListener('keydown', alPulsarTecla)
    const overflowPrevio = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', alPulsarTecla)
      document.body.style.overflow = overflowPrevio
    }
  }, [abierto, onCerrar])

  // Gestión del foco: al abrir se guarda quién lo tenía y se mueve al panel;
  // al cerrar se devuelve, para no dejar al usuario de teclado perdido.
  useEffect(() => {
    if (!abierto) return undefined

    focoPrevioRef.current = document.activeElement
    panelRef.current?.focus()

    return () => {
      const previo = focoPrevioRef.current
      if (previo instanceof HTMLElement) previo.focus()
    }
  }, [abierto])

  if (!abierto) return null

  const color = colorDeCategoria(contenido.categoria)

  // Focus trap: mantiene el Tab dentro del diálogo.
  const alTabular = (evento) => {
    if (evento.key !== 'Tab') return

    const focusables = panelRef.current?.querySelectorAll(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
    )
    if (!focusables?.length) return

    const primero = focusables[0]
    const ultimo = focusables[focusables.length - 1]

    if (evento.shiftKey && document.activeElement === primero) {
      evento.preventDefault()
      ultimo.focus()
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault()
      primero.focus()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Fondo oscurecido. Es decorativo: el cierre accesible es Escape y el botón. */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCerrar}
        aria-hidden="true"
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-detalle"
        tabIndex={-1}
        onKeyDown={alTabular}
        className="animate-fade-up relative flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-ink-700 bg-ink-950 shadow-2xl focus:outline-none sm:w-[min(100%,36rem)]"
      >
        {/* --- Encabezado --- */}
        <div className="sticky top-0 z-10 flex items-start gap-3 border-b border-ink-700 bg-ink-900/95 p-5 backdrop-blur">
          <span
            className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${color}1f`, color }}
            aria-hidden="true"
          >
            <Tag size={19} />
          </span>

          <div className="min-w-0 flex-1">
            <h2 id="titulo-detalle" className="text-base font-semibold leading-snug text-mist-100">
              {contenido.titulo}
            </h2>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-mist-500">
              <span>{contenido.origen || 'Sin origen'}</span>
              {contenido.creado_en && (
                <>
                  <span aria-hidden="true">·</span>
                  <Calendar size={11} aria-hidden="true" />
                  <span>{formatearFecha(contenido.creado_en)}</span>
                </>
              )}
              <span aria-hidden="true">·</span>
              <span>#{contenido.id}</span>
            </p>
          </div>

          <button
            type="button"
            onClick={onCerrar}
            className="rounded-lg p-1.5 text-mist-500 transition-colors hover:bg-ink-800 hover:text-mist-100"
            aria-label="Cerrar detalle"
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-6 p-5">
          {/* --- Clasificación --- */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-mist-500">
                Categoría
              </p>
              <CategoryBadge categoria={contenido.categoria} tamano="lg" conIcono />
            </div>

            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-mist-500">
                <Gauge size={12} aria-hidden="true" />
                Confianza
              </p>
              <div
                className="h-2 w-full overflow-hidden rounded-full bg-ink-800"
                role="progressbar"
                aria-valuenow={aPorcentaje(contenido.probabilidad)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Confianza del modelo"
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${aPorcentaje(contenido.probabilidad)}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
              <p className="mt-1 text-sm font-bold text-mist-100">
                {aPorcentaje(contenido.probabilidad)}%
              </p>
            </div>
          </div>

          {/* --- Palabras clave --- */}
          {contenido.informacion_adicional?.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-mist-500">
                Palabras clave detectadas
              </p>
              <ul className="flex flex-wrap gap-2">
                {contenido.informacion_adicional.map((palabra) => (
                  <li key={palabra}>
                    <KeywordBadge>{palabra}</KeywordBadge>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* --- Texto original --- */}
          {contenido.texto && (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-mist-500">
                Contenido analizado
              </p>
              <p className="max-h-48 overflow-y-auto rounded-xl border border-ink-700 bg-ink-900 p-3.5 text-sm leading-relaxed text-mist-300">
                {contenido.texto}
              </p>
            </div>
          )}

          {contenido.url && (
            <a
              href={contenido.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-400 hover:text-brand-300"
            >
              <LinkIcon size={14} aria-hidden="true" />
              Ver recurso original
            </a>
          )}

          {/* --- Recomendaciones --- */}
          <div className="border-t border-ink-700 pt-5">
            <Recomendaciones
              recomendaciones={recomendaciones}
              estrategia={estrategia}
              cargando={cargando}
              error={error}
              onAbrir={onAbrirOtro}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
