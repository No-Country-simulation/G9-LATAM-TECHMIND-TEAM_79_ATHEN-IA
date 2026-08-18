import { BookOpen, Calendar } from 'lucide-react'
import CategoryBadge from './CategoryBadge'
import { aPorcentaje, estilosDeCategoria, formatearFecha } from '../data/categorias'

/**
 * Tarjeta de un contenido ya analizado. La usa la vista Buscar Contenidos.
 *
 * @param {object}   contenido  Registro devuelto por `GET /contenidos`.
 * @param {Function} [onVer]    Callback al pulsar la tarjeta.
 */
export default function CourseCard({ contenido, onVer }) {
  const {
    titulo,
    resumen,
    texto,
    categoria,
    probabilidad,
    informacion_adicional: palabrasClave = [],
    origen,
    creado_en: creadoEn,
  } = contenido

  const descripcion = resumen || texto
  const confianza = aPorcentaje(probabilidad)

  return (
    <article className="card group flex flex-col p-5 transition-colors hover:border-brand-500/50">
      <div className="flex items-start gap-3">
        <span
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
          style={estilosDeCategoria(categoria)}
        >
          <BookOpen size={18} />
        </span>

        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold leading-snug text-tinta-900">{titulo}</h3>
          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-tinta-600">
            {origen || 'Sin origen'}
            {creadoEn && (
              <>
                <span aria-hidden="true">·</span>
                <Calendar size={11} />
                {formatearFecha(creadoEn)}
              </>
            )}
          </p>
        </div>

        <span
          className="shrink-0 rounded-lg px-2 py-1 text-xs font-bold"
          style={estilosDeCategoria(categoria)}
          title="Confianza de la clasificacion"
        >
          {confianza}%
        </span>
      </div>

      <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-tinta-700">{descripcion}</p>

      <ul className="mt-4 flex flex-wrap gap-1.5">
        <li>
          <CategoryBadge categoria={categoria} tamano="sm" />
        </li>
        {palabrasClave.slice(0, 3).map((palabra) => (
          <li
            key={palabra}
            className="rounded-lg border border-linea px-2 py-0.5 text-[11px] text-tinta-600"
          >
            {palabra}
          </li>
        ))}
        {palabrasClave.length > 3 && (
          <li className="px-1 py-0.5 text-[11px] text-tinta-600">
            +{palabrasClave.length - 3}
          </li>
        )}
      </ul>

      {onVer && (
        <button
          type="button"
          onClick={() => onVer(contenido)}
          className="mt-4 self-start text-xs font-semibold text-brand-600 transition-colors hover:text-brand-700"
        >
          Ver detalle
        </button>
      )}
    </article>
  )
}
