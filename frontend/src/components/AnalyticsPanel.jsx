import { Gauge, Layers, Building2, Activity } from 'lucide-react'
import { Skeleton } from './Loaders'
import { colorDeCategoria } from '../data/categorias'

/**
 * Panel de analíticas del Dashboard.
 *
 * Consume `GET /analiticas`. Todos los gráficos son SVG/CSS puro — sin
 * librerías de charts — para no engordar el bundle del MVP.
 */

/** Colores fijos por franja de confianza: verde = buena, ámbar = media, rojo = baja. */
const COLOR_CONFIANZA = {
  'Alta (≥75%)': '#34d399',
  'Media (50-74%)': '#fbbf24',
  'Baja (<50%)': '#fb7185',
}

/** Barras horizontales con etiqueta, cantidad y porcentaje. */
function BarrasDistribucion({ segmentos, colorDe, vacio }) {
  if (!segmentos?.length) {
    return <p className="text-sm text-mist-500">{vacio}</p>
  }

  const maximo = Math.max(...segmentos.map((s) => s.cantidad), 1)

  return (
    <ul className="space-y-3">
      {segmentos.map((segmento) => (
        <li key={segmento.etiqueta} className="flex items-center gap-3 text-sm">
          <span className="w-28 shrink-0 truncate text-mist-300 sm:w-40" title={segmento.etiqueta}>
            {segmento.etiqueta}
          </span>

          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-800">
            <div
              className="h-full rounded-full transition-[width] duration-700 ease-out"
              style={{
                width: `${(segmento.cantidad / maximo) * 100}%`,
                backgroundColor: colorDe(segmento.etiqueta),
              }}
            />
          </div>

          <span className="w-8 shrink-0 text-right text-xs text-mist-500">
            {segmento.cantidad}
          </span>
          <span className="w-12 shrink-0 text-right text-xs font-semibold text-mist-100">
            {segmento.porcentaje}%
          </span>
        </li>
      ))}
    </ul>
  )
}

/** Gráfico de líneas/área de la actividad diaria, en SVG puro. */
function GraficoActividad({ puntos }) {
  if (!puntos?.length) {
    return <p className="text-sm text-mist-500">Aún no hay actividad registrada.</p>
  }

  // Con un solo día no hay línea que dibujar: se muestra el dato directo.
  if (puntos.length === 1) {
    return (
      <p className="text-sm text-mist-300">
        <span className="text-2xl font-bold text-mist-100">{puntos[0].cantidad}</span>{' '}
        análisis el {puntos[0].fecha}
      </p>
    )
  }

  const ANCHO = 100
  const ALTO = 32
  const maximo = Math.max(...puntos.map((p) => p.cantidad), 1)

  const coordenadas = puntos.map((punto, indice) => {
    const x = (indice / (puntos.length - 1)) * ANCHO
    const y = ALTO - (punto.cantidad / maximo) * ALTO
    return `${x},${y}`
  })

  const area = `0,${ALTO} ${coordenadas.join(' ')} ${ANCHO},${ALTO}`

  return (
    <figure>
      <svg
        viewBox={`0 0 ${ANCHO} ${ALTO}`}
        preserveAspectRatio="none"
        className="h-28 w-full"
        role="img"
        aria-label={`Actividad diaria: ${puntos
          .map((p) => `${p.fecha}, ${p.cantidad} análisis`)
          .join('; ')}`}
      >
        <polygon points={area} fill="#8b5cf6" opacity="0.15" />
        <polyline
          points={coordenadas.join(' ')}
          fill="none"
          stroke="#8b5cf6"
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>

      <figcaption className="mt-2 flex justify-between text-[11px] text-mist-500">
        <span>{puntos[0].fecha}</span>
        <span>{puntos[puntos.length - 1].fecha}</span>
      </figcaption>
    </figure>
  )
}

/** Tarjeta contenedora de cada bloque del panel. */
function Bloque({ titulo, descripcion, icono: Icono, children, className = '' }) {
  return (
    <section className={`card p-6 ${className}`}>
      <h3 className="flex items-center gap-2 text-base font-semibold text-mist-100">
        {Icono && <Icono size={16} className="text-brand-400" aria-hidden="true" />}
        {titulo}
      </h3>
      {descripcion && <p className="mb-5 mt-1 text-sm text-mist-500">{descripcion}</p>}
      {children}
    </section>
  )
}

export default function AnalyticsPanel({ analiticas, cargando }) {
  if (cargando) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-56 w-full rounded-2xl" />
        ))}
      </div>
    )
  }

  if (!analiticas || analiticas.total_contenidos === 0) return null

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Bloque
        titulo="Distribución por categoría"
        descripcion="Qué áreas dominan tu biblioteca."
        icono={Layers}
      >
        <BarrasDistribucion
          segmentos={analiticas.distribucion_categorias}
          colorDe={colorDeCategoria}
          vacio="Sin categorías todavía."
        />
      </Bloque>

      <Bloque
        titulo="Confianza del modelo"
        descripcion="Cuánto contenido clasificó la IA con certeza alta, media o baja."
        icono={Gauge}
      >
        <BarrasDistribucion
          segmentos={analiticas.distribucion_confianza}
          colorDe={(etiqueta) => COLOR_CONFIANZA[etiqueta] ?? '#8f86ad'}
          vacio="Sin datos de confianza."
        />
      </Bloque>

      <Bloque
        titulo="Origen del contenido"
        descripcion="De dónde proviene lo que has catalogado."
        icono={Building2}
      >
        <BarrasDistribucion
          segmentos={analiticas.distribucion_origenes}
          colorDe={() => '#38bdf8'}
          vacio="Sin orígenes registrados."
        />
      </Bloque>

      <Bloque
        titulo="Actividad reciente"
        descripcion="Contenidos analizados por día."
        icono={Activity}
      >
        <GraficoActividad puntos={analiticas.actividad_reciente} />
      </Bloque>
    </div>
  )
}
