import { useEffect, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'

/**
 * Diálogo de confirmación accesible.
 *
 * Mismo contrato de accesibilidad que `ContentDetail`:
 * - `role="alertdialog"` + `aria-modal` + `aria-labelledby`/`aria-describedby`.
 * - Cierra con `Escape` y con clic en el fondo.
 * - Al abrirse mueve el foco al botón de confirmar; al cerrarse lo devuelve
 *   al elemento que lo tenía (el botón que abrió el diálogo).
 * - Atrapa el `Tab` dentro del diálogo.
 *
 * @param {boolean}  abierto
 * @param {string}   titulo
 * @param {string}   mensaje
 * @param {string}   [textoConfirmar]
 * @param {Function} onConfirmar
 * @param {Function} onCancelar
 */
export default function ConfirmDialog({
  abierto,
  titulo,
  mensaje,
  textoConfirmar = 'Confirmar',
  textoCancelar = 'Cancelar',
  onConfirmar,
  onCancelar,
}) {
  const panelRef = useRef(null)
  const confirmarRef = useRef(null)
  const focoPrevioRef = useRef(null)

  // Escape para cerrar + bloqueo del scroll de fondo.
  useEffect(() => {
    if (!abierto) return undefined

    const alPulsarTecla = (evento) => {
      if (evento.key === 'Escape') {
        evento.stopPropagation()
        onCancelar()
      }
    }

    document.addEventListener('keydown', alPulsarTecla)
    const overflowPrevio = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', alPulsarTecla)
      document.body.style.overflow = overflowPrevio
    }
  }, [abierto, onCancelar])

  // Gestión del foco.
  useEffect(() => {
    if (!abierto) return undefined

    focoPrevioRef.current = document.activeElement
    confirmarRef.current?.focus()

    return () => {
      const previo = focoPrevioRef.current
      if (previo instanceof HTMLElement) previo.focus()
    }
  }, [abierto])

  if (!abierto) return null

  // Focus trap.
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
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancelar}
        aria-hidden="true"
      />

      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="titulo-confirmacion"
        aria-describedby="mensaje-confirmacion"
        onKeyDown={alTabular}
        className="animate-fade-up relative w-full max-w-sm rounded-2xl border border-ink-700 bg-ink-900 p-6 shadow-2xl"
      >
        <div className="flex items-start gap-3">
          <span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-300"
            aria-hidden="true"
          >
            <AlertTriangle size={19} />
          </span>

          <div className="min-w-0">
            <h2 id="titulo-confirmacion" className="text-base font-semibold text-mist-100">
              {titulo}
            </h2>
            <p id="mensaje-confirmacion" className="mt-1.5 text-sm leading-relaxed text-mist-500">
              {mensaje}
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button type="button" onClick={onCancelar} className="btn-ghost">
            {textoCancelar}
          </button>
          <button
            ref={confirmarRef}
            type="button"
            onClick={onConfirmar}
            className="btn-primary"
          >
            {textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  )
}
