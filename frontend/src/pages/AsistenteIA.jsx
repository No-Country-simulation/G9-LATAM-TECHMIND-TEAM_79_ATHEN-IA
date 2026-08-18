import { Link } from 'react-router-dom'
import { Bot, Sparkles, Search, Library, Construction, ArrowRight } from 'lucide-react'

/**
 * Vista "Asistente IA" — placeholder honesto.
 *
 * No hay endpoint conversacional en el backend, asi que **no se simula un
 * chat**. Una caja de texto que responde con frases prefabricadas parece una
 * funcionalidad terminada y, en una demostracion, es peor que decir la verdad:
 * si el jurado escribe algo y recibe una respuesta enlatada, pierde confianza
 * en todo lo demas.
 *
 * En su lugar la vista explica que hara el asistente, sobre que se apoyara —
 * capacidades que ya existen y son verificables— y encamina al usuario a las
 * pantallas que si funcionan hoy.
 */

const CAPACIDADES_ACTUALES = [
  {
    icono: Sparkles,
    titulo: 'Clasificacion con IA',
    descripcion:
      'El modelo entrenado categoriza el contenido y extrae sus tecnologias.',
    a: '/agregar',
    accion: 'Analizar contenido',
  },
  {
    icono: Search,
    titulo: 'Busqueda en tiempo real',
    descripcion: 'Filtra la biblioteca por texto, categoria o tecnologia.',
    a: '/buscar',
    accion: 'Ir a Buscar',
  },
  {
    icono: Library,
    titulo: 'Contenido relacionado',
    descripcion:
      'Recomendaciones por similitud, con las tecnologias que explican cada sugerencia.',
    a: '/recomendaciones',
    accion: 'Ver recomendaciones',
  },
]

export default function AsistenteIA() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-mist-100">
          <Bot size={24} className="text-brand-400" aria-hidden="true" />
          Asistente IA
        </h1>
        <p className="mt-1 text-sm text-mist-400">
          Conversacion en lenguaje natural sobre tu biblioteca de conocimiento.
        </p>
      </div>

      {/* --- Estado honesto --- */}
      <section className="card border-amber-500/40 bg-amber-500/10 p-6">
        <div className="flex items-start gap-3.5">
          <span
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-300"
            aria-hidden="true"
          >
            <Construction size={21} />
          </span>

          <div className="min-w-0">
            <h2 className="text-base font-semibold text-amber-50">
              En construccion — posterior al MVP
            </h2>
            <p className="mt-1.5 text-sm leading-relaxed text-amber-100/90">
              El asistente conversacional todavia no esta implementado. No hay
              un endpoint de chat en el backend, asi que esta pantalla no simula
              respuestas: preferimos decirlo antes que aparentar una
              funcionalidad que no existe.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-amber-100/90">
              Cuando llegue, se apoyara en lo que el sistema ya sabe hacer: la
              clasificacion del modelo entrenado, las palabras clave extraidas y
              el motor de similitud que hoy alimenta las recomendaciones.
            </p>
          </div>
        </div>
      </section>

      {/* --- Lo que si funciona hoy --- */}
      <section>
        <h2 className="text-base font-semibold text-mist-100">
          Mientras tanto, esto ya funciona
        </h2>
        <p className="mb-4 mt-1 text-sm text-mist-400">
          Las capacidades sobre las que se construira el asistente.
        </p>

        <div className="grid gap-4 md:grid-cols-3">
          {CAPACIDADES_ACTUALES.map(({ icono: Icono, titulo, descripcion, a, accion }) => (
            <article key={titulo} className="card flex flex-col p-5">
              <span
                className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600/20 text-brand-300"
                aria-hidden="true"
              >
                <Icono size={20} />
              </span>

              <h3 className="mt-3.5 text-sm font-semibold text-mist-100">{titulo}</h3>
              <p className="mt-1.5 flex-1 text-sm leading-relaxed text-mist-400">
                {descripcion}
              </p>

              <Link
                to={a}
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-300 transition-colors hover:text-brand-200"
              >
                {accion}
                <ArrowRight size={15} aria-hidden="true" />
              </Link>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
