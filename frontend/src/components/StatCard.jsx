/**
 * Tarjeta de metrica del Dashboard.
 *
 * @param {string}   etiqueta  Nombre de la metrica ("Cursos Totales").
 * @param {number}   valor     Valor numerico a destacar.
 * @param {Function} icono     Componente de icono de lucide-react.
 * @param {string}   acento    Color hex del acento (borde e icono).
 * @param {string}   variacion Texto opcional de tendencia ("+3 esta semana").
 */
export default function StatCard({
  etiqueta,
  valor,
  icono: Icono,
  acento = '#8b5cf6',
  variacion,
}) {
  return (
    <article className="card group relative overflow-hidden p-5 transition-colors hover:border-ink-600">
      {/* Halo de color que reacciona al hover */}
      <div
        className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-15 blur-2xl transition-opacity group-hover:opacity-30"
        style={{ backgroundColor: acento }}
        aria-hidden="true"
      />

      {/* `min-w-0` en el texto y `shrink-0` en el icono: sin ellos, un valor o
          una etiqueta larga empujan el icono fuera de la tarjeta (que tiene
          `overflow-hidden`, asi que se recortaria). `truncate` corta con
          puntos suspensivos en vez de desbordar. */}
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium uppercase tracking-wide text-mist-500">
            {etiqueta}
          </p>
          <p
            className="mt-2 truncate text-3xl font-bold tracking-tight text-mist-100"
            title={String(valor)}
          >
            {valor}
          </p>
          {variacion && <p className="mt-1 truncate text-xs text-mist-500">{variacion}</p>}
        </div>

        {Icono && (
          <span
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${acento}1f`, color: acento }}
            aria-hidden="true"
          >
            <Icono size={20} strokeWidth={2} />
          </span>
        )}
      </div>
    </article>
  )
}
