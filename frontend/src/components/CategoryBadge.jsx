import { Layers } from 'lucide-react'
import { aPorcentaje, estilosDeCategoria } from '../data/categorias'

/**
 * Badge de categoria con el color de acento correspondiente.
 *
 * @param {string}  categoria    Nombre de la categoria.
 * @param {number}  [confianza]  Probabilidad 0-1; si viene, se muestra el %.
 * @param {'sm'|'md'|'lg'} [tamano]
 * @param {boolean} [conIcono]
 */
export default function CategoryBadge({
  categoria,
  confianza,
  tamano = 'md',
  conIcono = false,
  className = '',
}) {
  const tamanos = {
    sm: 'px-2 py-0.5 text-[11px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3.5 py-2 text-sm gap-2',
  }

  return (
    <span
      className={`inline-flex items-center rounded-lg font-semibold ${tamanos[tamano]} ${className}`}
      style={estilosDeCategoria(categoria, { borde: tamano === 'lg' })}
    >
      {conIcono && <Layers size={tamano === 'lg' ? 15 : 12} />}
      {categoria}
      {confianza != null && (
        <span className="opacity-70">· {aPorcentaje(confianza)}%</span>
      )}
    </span>
  )
}

/** Badge neutro para palabras clave. */
export function KeywordBadge({ children }) {
  return <span className="badge">{children}</span>
}
