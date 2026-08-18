import { Link } from 'react-router-dom'
import {
  BookMarked,
  Layers,
  Tag,
  Gauge,
  Sparkles,
  ArrowRight,
  Clock,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import StatCard from '../components/StatCard'
import CategoryBadge from '../components/CategoryBadge'
import { SkeletonStat, Skeleton, Spinner } from '../components/Loaders'
import AnalyticsPanel from '../components/AnalyticsPanel'
import { useAnaliticas, useContenidos } from '../hooks/useContenidos'
import { aPorcentaje, colorDeCategoria, formatearFecha } from '../data/categorias'
import { nombreDePila } from '../data/usuario'

const RADIO = 54
const CIRCUNFERENCIA = 2 * Math.PI * RADIO

/**
 * Grafico de dona en SVG puro.
 * Se dibuja a mano para no sumar una libreria de charts al bundle del MVP.
 *
 * `distribucion` llega de `GET /analiticas`, cuyos segmentos usan la clave
 * generica `etiqueta` (el mismo esquema `SegmentoConteo` se reutiliza para
 * categorias, origenes y franjas de confianza).
 */
function DonaCategorias({ distribucion, total }) {
  let acumulado = 0

  return (
    <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
      <svg viewBox="0 0 140 140" className="h-40 w-40 shrink-0 -rotate-90">
        <circle cx="70" cy="70" r={RADIO} fill="none" stroke="#1a1530" strokeWidth="16" />

        {distribucion.map(({ etiqueta: categoria, cantidad }) => {
          const porcion = (cantidad / total) * CIRCUNFERENCIA
          const desfase = -acumulado
          acumulado += porcion

          return (
            <circle
              key={categoria}
              cx="70"
              cy="70"
              r={RADIO}
              fill="none"
              stroke={colorDeCategoria(categoria)}
              strokeWidth="16"
              // 2px de separacion visual entre porciones
              strokeDasharray={`${Math.max(porcion - 2, 0)} ${CIRCUNFERENCIA}`}
              strokeDashoffset={desfase}
              strokeLinecap="butt"
              className="transition-[stroke-dasharray] duration-700 ease-out"
            >
              <title>{`${categoria}: ${cantidad}`}</title>
            </circle>
          )
        })}

        {/* Total al centro (se rota de vuelta porque el SVG esta girado) */}
        <text
          x="70"
          y="66"
          textAnchor="middle"
          className="fill-mist-100 text-[22px] font-bold"
          transform="rotate(90 70 70)"
        >
          {total}
        </text>
        <text
          x="70"
          y="82"
          textAnchor="middle"
          className="fill-mist-500 text-[10px] uppercase"
          transform="rotate(90 70 70)"
        >
          cursos
        </text>
      </svg>

      <ul className="w-full space-y-2.5">
        {distribucion.map(({ etiqueta: categoria, cantidad, porcentaje }) => (
          <li key={categoria} className="flex items-center gap-2.5 text-sm">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ backgroundColor: colorDeCategoria(categoria) }}
            />
            <span className="flex-1 truncate text-mist-300">{categoria}</span>
            <span className="text-mist-500">{cantidad}</span>
            <span className="w-10 text-right font-semibold text-mist-100">{porcentaje}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Barras horizontales con las palabras clave mas frecuentes. */
function TopPalabrasClave({ palabras }) {
  const maximo = Math.max(...palabras.map((p) => p.cantidad), 1)

  return (
    <ul className="space-y-2.5">
      {palabras.map(({ palabra, cantidad }) => (
        <li key={palabra} className="flex items-center gap-3 text-sm">
          <span className="w-32 shrink-0 truncate text-mist-300">{palabra}</span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-800">
            <div
              className="h-full rounded-full bg-brand-500 transition-[width] duration-700 ease-out"
              style={{ width: `${(cantidad / maximo) * 100}%` }}
            />
          </div>
          <span className="w-6 text-right text-xs text-mist-400">{cantidad}</span>
        </li>
      ))}
    </ul>
  )
}

/** Mensaje mostrado cuando el historial esta vacio. */
function SinDatos() {
  return (
    <div className="card flex flex-col items-center justify-center p-12 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-ink-800 text-mist-500">
        <Sparkles size={26} />
      </span>
      <p className="mt-4 text-sm font-medium text-mist-300">Tu biblioteca esta vacia</p>
      <p className="mt-1 max-w-sm text-sm text-mist-500">
        Analiza tu primer contenido tecnico y AthenIA empezara a construir tus metricas.
      </p>
      <Link to="/agregar" className="btn-primary mt-6">
        <Sparkles size={16} />
        Analizar contenido
      </Link>
    </div>
  )
}

/** Vista principal: metricas generales alimentadas por el historial real. */
export default function Dashboard() {
  const { analiticas, cargando: cargandoMetricas, error, refrescar } = useAnaliticas()
  const { items: recientes, cargando: cargandoRecientes } = useContenidos({
    limite: 4,
    debounceMs: 0,
  })

  const hayDatos = analiticas && analiticas.total_contenidos > 0

  return (
    <div className="space-y-6">
      {/* --- Saludo --- */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-mist-100">
            Hola, {nombreDePila()} <span className="inline-block">👋</span>
          </h1>
          <p className="mt-1 text-sm text-mist-500">
            Este es el resumen de tu biblioteca de conocimiento tecnico.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={refrescar}
            className="btn-ghost"
            aria-label="Actualizar metricas"
          >
            <RefreshCw size={16} className={cargandoMetricas ? 'animate-spin' : ''} />
            Actualizar
          </button>
          <Link to="/agregar" className="btn-primary">
            <Sparkles size={16} />
            Analizar contenido
          </Link>
        </div>
      </div>

      {/* --- Backend caido --- */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3.5"
        >
          <AlertCircle size={17} className="mt-0.5 shrink-0 text-rose-400" />
          <p className="text-sm text-rose-200">{error}</p>
        </div>
      )}

      {/* --- Metricas --- */}
      {cargandoMetricas ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <SkeletonStat key={i} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            etiqueta="Cursos Totales"
            valor={analiticas?.total_contenidos ?? 0}
            icono={BookMarked}
            acento="#8b5cf6"
            variacion="Contenidos analizados"
          />
          <StatCard
            etiqueta="Categorias"
            valor={analiticas?.total_categorias ?? 0}
            icono={Layers}
            acento="#38bdf8"
            variacion="Detectadas por la IA"
          />
          <StatCard
            etiqueta="Palabras Clave"
            valor={analiticas?.total_palabras_clave ?? 0}
            icono={Tag}
            acento="#34d399"
            variacion="Tecnologias unicas"
          />
          <StatCard
            etiqueta="Confianza Promedio"
            valor={`${aPorcentaje(analiticas?.confianza_promedio)}%`}
            icono={Gauge}
            acento="#fbbf24"
            variacion="Precision del modelo"
          />
        </div>
      )}

      {!cargandoMetricas && !hayDatos && !error && <SinDatos />}

      {/* --- Distribucion + actividad --- */}
      {hayDatos && (
        <>
          <div className="grid gap-4 lg:grid-cols-5">
            <section className="card p-6 lg:col-span-3">
              <h2 className="text-base font-semibold text-mist-100">
                Categorias mas estudiadas
              </h2>
              <p className="mb-6 mt-1 text-sm text-mist-500">
                Distribucion del contenido clasificado por AthenIA.
              </p>
              <DonaCategorias
                distribucion={analiticas.distribucion_categorias}
                total={analiticas.total_contenidos}
              />
            </section>

            <section className="card flex flex-col p-6 lg:col-span-2">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-mist-100">Actividad reciente</h2>
                  <p className="mt-1 text-sm text-mist-500">Ultimos contenidos analizados.</p>
                </div>
                {cargandoRecientes && <Spinner tamano={16} />}
              </div>

              <ul className="flex-1 space-y-3">
                {cargandoRecientes
                  ? Array.from({ length: 4 }, (_, i) => (
                      <li key={i}>
                        <Skeleton className="h-14 w-full rounded-xl" />
                      </li>
                    ))
                  : recientes.map((contenido) => (
                      <li
                        key={contenido.id}
                        className="flex items-start gap-3 rounded-xl border border-ink-700 bg-ink-900 p-3"
                      >
                        <Clock size={15} className="mt-0.5 shrink-0 text-mist-500" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-mist-100">
                            {contenido.titulo}
                          </p>
                          <p className="text-xs text-mist-400">
                            {formatearFecha(contenido.creado_en)}
                          </p>
                        </div>
                        <CategoryBadge categoria={contenido.categoria} tamano="sm" />
                      </li>
                    ))}
              </ul>

              <Link
                to="/buscar"
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-400 hover:text-brand-300"
              >
                Ver todo
                <ArrowRight size={15} />
              </Link>
            </section>
          </div>

          {/* --- Palabras clave mas frecuentes --- */}
          {analiticas.top_palabras_clave.length > 0 && (
            <section className="card p-6">
              <h2 className="text-base font-semibold text-mist-100">
                Tecnologias mas frecuentes
              </h2>
              <p className="mb-5 mt-1 text-sm text-mist-500">
                Palabras clave extraidas por el modelo en todo tu contenido.
              </p>
              <TopPalabrasClave palabras={analiticas.top_palabras_clave} />
            </section>
          )}

          {/* --- Panel de analiticas (Semana 4) --- */}
          <div>
            <h2 className="mb-1 text-lg font-bold tracking-tight text-mist-100">
              Analiticas
            </h2>
            <p className="mb-4 text-sm text-mist-500">
              Confianza del modelo, origenes y actividad en el tiempo.
            </p>
            <AnalyticsPanel analiticas={analiticas} cargando={false} />
          </div>
        </>
      )}
    </div>
  )
}
