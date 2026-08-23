import { Link } from 'react-router-dom'
import { Bot, Send, Construction, ArrowRight, Sparkles, Search, Library } from 'lucide-react'
import { iniciales } from '../data/usuario'
import { useAuth } from '../hooks/useAuth'

/**
 * Vista "Asistente IA" (pantalla 06 del mockup).
 *
 * MAQUETA — no hay endpoint conversacional en el backend.
 *
 * Se reproduce la interfaz de chat del diseño (burbujas moradas del usuario,
 * blancas de la IA), pero el campo de entrada esta deshabilitado y no se envia
 * nada. La conversacion visible es un ejemplo rotulado como tal.
 *
 * Por que no simular respuestas: si el jurado escribe y recibe una frase
 * enlatada, descubre el truco en dos mensajes y pierde confianza en el resto
 * de la demo — donde la IA si es real. Mostrar la maqueta y decirlo cuesta
 * mucho menos.
 */

/** Conversacion de ejemplo, para ilustrar el formato del futuro asistente. */
const CONVERSACION_EJEMPLO = [
  {
    de: 'usuario',
    texto: '¿Que cursos tengo sobre Python?',
    hora: '10:30',
  },
  {
    de: 'ia',
    texto: 'Tienes 4 contenidos relacionados con Python:',
    lista: [
      'Introduccion a Python',
      'Python para Data Science',
      'Machine Learning con Python',
      'Automatizacion con Python',
    ],
    cierre: '¿Te gustaria ver alguno en particular?',
    hora: '10:30',
  },
]

const SUGERENCIAS = [
  '¿Que deberia estudiar despues de Spring Boot?',
  'Muestrame cursos sobre Docker',
  'Recomiendame algo de IA',
]

const CAPACIDADES = [
  { icono: Sparkles, titulo: 'Clasificacion con IA', a: '/agregar', accion: 'Analizar contenido' },
  { icono: Search, titulo: 'Busqueda en tiempo real', a: '/buscar', accion: 'Ir a Buscar' },
  {
    icono: Library,
    titulo: 'Contenido relacionado',
    a: '/recomendaciones',
    accion: 'Ver recomendaciones',
  },
]

export default function AsistenteIA() {
  const { usuario } = useAuth()
  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-tinta-900">
          <Bot size={24} className="text-brand-600" aria-hidden="true" />
          Asistente AthenIA
        </h1>
        <p className="mt-1 text-sm text-tinta-500">
          Tu asistente inteligente para aprender y organizar tu conocimiento.
        </p>
      </div>

      {/* --- Aviso: es una maqueta --- */}
      <div
        role="status"
        className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4"
      >
        <Construction size={18} className="mt-0.5 shrink-0 text-amber-600" aria-hidden="true" />
        <p className="text-sm leading-relaxed text-amber-800">
          <span className="font-semibold">Vista previa del diseño.</span> El
          asistente conversacional llega despues del MVP: todavia no hay un
          endpoint de chat, asi que la conversacion de abajo es un ejemplo y el
          campo de entrada esta desactivado.
        </p>
      </div>

      {/* --- Ventana de chat --- */}
      <section
        className="card flex h-[28rem] flex-col overflow-hidden"
        aria-label="Conversacion de ejemplo"
      >
        <div className="flex-1 space-y-4 overflow-y-auto bg-panel-suave p-5">
          {CONVERSACION_EJEMPLO.map((mensaje, indice) =>
            mensaje.de === 'usuario' ? (
              <div key={indice} className="flex justify-end gap-2.5">
                <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 shadow-sm">
                  <p className="text-sm text-white">{mensaje.texto}</p>
                  <p className="mt-1 text-right text-[10px] text-brand-100">{mensaje.hora}</p>
                </div>
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-tinta-700 text-[11px] font-bold text-white">
                  {iniciales(usuario?.nombre)}
                </span>
              </div>
            ) : (
              <div key={indice} className="flex gap-2.5">
                <span
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600"
                  aria-hidden="true"
                >
                  <Bot size={16} />
                </span>
                <div className="max-w-[75%] rounded-2xl rounded-tl-sm border border-linea bg-panel px-4 py-2.5 shadow-sm">
                  <p className="text-sm text-tinta-700">{mensaje.texto}</p>

                  {mensaje.lista && (
                    <ul className="mt-2 space-y-1">
                      {mensaje.lista.map((item) => (
                        <li key={item} className="flex items-start gap-1.5 text-sm text-tinta-700">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-500" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}

                  {mensaje.cierre && (
                    <p className="mt-2 text-sm text-tinta-700">{mensaje.cierre}</p>
                  )}
                  <p className="mt-1 text-[10px] text-tinta-500">{mensaje.hora}</p>
                </div>
              </div>
            ),
          )}
        </div>

        {/* --- Sugerencias --- */}
        <div className="flex flex-wrap gap-2 border-t border-linea bg-panel px-5 py-3">
          {SUGERENCIAS.map((sugerencia) => (
            <span
              key={sugerencia}
              className="cursor-not-allowed rounded-lg border border-linea bg-panel-suave px-2.5 py-1 text-xs text-tinta-500"
              title="Disponible cuando se active el asistente"
            >
              {sugerencia}
            </span>
          ))}
        </div>

        {/* --- Entrada (desactivada a proposito) --- */}
        <div className="flex items-center gap-2.5 border-t border-linea bg-panel p-4">
          <input
            type="text"
            disabled
            placeholder="El asistente estara disponible despues del MVP"
            aria-label="Escribe tu pregunta (no disponible)"
            className="input-base cursor-not-allowed bg-panel-suave"
          />
          <button
            type="button"
            disabled
            aria-label="Enviar (no disponible)"
            className="flex h-10 w-10 shrink-0 cursor-not-allowed items-center justify-center rounded-xl bg-brand-600 text-white opacity-40"
          >
            <Send size={17} />
          </button>
        </div>
      </section>

      {/* --- Lo que si funciona --- */}
      <section>
        <h2 className="text-base font-semibold text-tinta-900">
          Mientras tanto, esto ya funciona
        </h2>
        <p className="mb-4 mt-1 text-sm text-tinta-500">
          Las capacidades reales sobre las que se construira el asistente.
        </p>

        <div className="grid gap-4 md:grid-cols-3">
          {CAPACIDADES.map(({ icono: Icono, titulo, a, accion }) => (
            <Link
              key={titulo}
              to={a}
              className="card group flex items-center gap-3.5 p-4 transition-colors hover:border-brand-300"
            >
              <span
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600"
                aria-hidden="true"
              >
                <Icono size={20} />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-tinta-900">{titulo}</p>
                <span className="mt-0.5 inline-flex items-center gap-1 text-xs font-medium text-brand-700">
                  {accion}
                  <ArrowRight size={12} aria-hidden="true" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
