import { History, X, Trash2 } from 'lucide-react'

/**
 * Chips con las búsquedas recientes del usuario.
 *
 * Los datos vienen de `useHistorialBusquedas` (persistidos en localStorage).
 * Este componente es puramente presentacional: recibe las entradas y emite
 * eventos, no toca el storage.
 *
 * @param {{termino: string, momento: number}[]} entradas
 * @param {Function} onSeleccionar Reejecuta esa búsqueda.
 * @param {Function} onEliminar    Quita un término del historial.
 * @param {Function} onLimpiar     Vacía el historial completo.
 */
export default function SearchHistory({ entradas = [], onSeleccionar, onEliminar, onLimpiar }) {
  if (!entradas.length) return null

  return (
    <section aria-labelledby="titulo-historial" className="flex flex-wrap items-center gap-2">
      <h2
        id="titulo-historial"
        className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-tinta-600"
      >
        <History size={13} aria-hidden="true" />
        Búsquedas recientes
      </h2>

      <ul className="flex flex-wrap items-center gap-2">
        {entradas.map((entrada) => (
          <li key={entrada.termino}>
            {/* Grupo botón + eliminar. No se anida un <button> dentro de otro
                (HTML inválido): son hermanos dentro de un contenedor. */}
            <span className="inline-flex items-center overflow-hidden rounded-lg border border-linea bg-panel transition-colors hover:border-brand-500/50">
              <button
                type="button"
                onClick={() => onSeleccionar?.(entrada.termino)}
                className="px-2.5 py-1 text-xs text-tinta-700 transition-colors hover:text-tinta-900"
              >
                {entrada.termino}
              </button>

              <button
                type="button"
                onClick={() => onEliminar?.(entrada.termino)}
                className="border-l border-linea px-1.5 py-1 text-tinta-500 transition-colors hover:bg-lienzo hover:text-rose-600"
                aria-label={`Quitar "${entrada.termino}" del historial`}
              >
                <X size={12} />
              </button>
            </span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={onLimpiar}
        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-tinta-600 transition-colors hover:text-rose-600"
      >
        <Trash2 size={12} aria-hidden="true" />
        Limpiar
      </button>
    </section>
  )
}
