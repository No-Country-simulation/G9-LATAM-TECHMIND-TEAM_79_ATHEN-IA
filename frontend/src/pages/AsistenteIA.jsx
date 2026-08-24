import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bot, Send, AlertTriangle, Sparkles, Search, Library, ArrowRight } from 'lucide-react'
import { iniciales } from '../data/usuario'
import { useAuth } from '../hooks/useAuth'
import { enviarMensajeAsistente, obtenerEstadoAsistente } from '../services/api'

/**
 * Vista "Asistente IA" (pantalla 06 del mockup) — Fase 1: chat real + catalogo.
 *
 * Ya NO es una maqueta: cada mensaje llama a `POST /asistente/mensaje`, que
 * hace RAG contra el catalogo real (`BuscadorCursos`) y redacta con OpenAI.
 * Los cursos que se muestran bajo cada respuesta vienen SIEMPRE de la
 * busqueda semantica del backend, nunca del texto que redacta el modelo, asi
 * que los enlaces son reales aunque el modelo se equivoque en la prosa.
 *
 * Si el backend no tiene la API key de OpenAI configurada, `GET
 * /asistente/estado` lo informa (`disponible: false`) y se muestra un aviso
 * ambar en vez de romper la vista: el chat sigue aceptando mensajes, porque
 * la busqueda semantica funciona igual sin el modelo de lenguaje.
 */

function saludoInicial() {
  return {
    id: 'saludo-inicial',
    de: 'ia',
    texto:
      'Hola, soy el Asistente de AthenIA. Preguntame sobre los cursos del catalogo ' +
      '(por ejemplo "que cursos hay de Python" o "recomiendame algo de Docker") y te ' +
      'respondo citando cursos reales.',
    cursos: [],
    esSaludo: true,
  }
}

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

function horaActual() {
  return new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
}

export default function AsistenteIA() {
  const { usuario } = useAuth()
  const [mensajes, setMensajes] = useState(() => [saludoInicial()])
  const [entrada, setEntrada] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [estado, setEstado] = useState(null)
  const finRef = useRef(null)

  // Diagnostico al montar: permite distinguir "sin API key" de "catalogo
  // caido" antes de que el usuario escriba nada.
  useEffect(() => {
    const controlador = new AbortController()
    obtenerEstadoAsistente(controlador.signal)
      .then(setEstado)
      .catch(() => setEstado({ disponible: false, catalogo_disponible: false }))
    return () => controlador.abort()
  }, [])

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [mensajes])

  async function enviarTexto(texto) {
    const contenido = texto.trim()
    if (!contenido || enviando) return

    const mensajeUsuario = {
      id: `u-${Date.now()}`,
      de: 'usuario',
      texto: contenido,
      hora: horaActual(),
    }
    setMensajes((previos) => [...previos, mensajeUsuario])
    setEntrada('')
    setEnviando(true)

    // El backend es sin estado: reenviamos el historial (sin el saludo, que
    // nunca fue parte de la conversacion real) en cada mensaje.
    const historial = mensajes
      .filter((m) => !m.esSaludo)
      .map((m) => ({ rol: m.de === 'usuario' ? 'usuario' : 'asistente', texto: m.texto }))

    try {
      const respuesta = await enviarMensajeAsistente(contenido, historial)
      setMensajes((previos) => [
        ...previos,
        {
          id: `ia-${Date.now()}`,
          de: 'ia',
          texto: respuesta.respuesta,
          cursos: respuesta.cursosRelacionados,
          hora: horaActual(),
        },
      ])
      setEstado((previo) => ({ ...previo, disponible: respuesta.disponible }))
    } catch (error) {
      setMensajes((previos) => [
        ...previos,
        {
          id: `error-${Date.now()}`,
          de: 'ia',
          texto: error.message || 'No pude conectarme con el asistente. Intenta de nuevo.',
          cursos: [],
          esError: true,
          hora: horaActual(),
        },
      ])
    } finally {
      setEnviando(false)
    }
  }

  function alEnviarFormulario(evento) {
    evento.preventDefault()
    enviarTexto(entrada)
  }

  const noDisponible = estado?.disponible === false

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

      {/* --- Aviso: modelo de lenguaje sin configurar --- */}
      {noDisponible && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4"
        >
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-600" aria-hidden="true" />
          <p className="text-sm leading-relaxed text-amber-800">
            <span className="font-semibold">El modelo de lenguaje no esta configurado.</span> Puedes
            seguir escribiendo: el asistente sigue trayendo cursos reales del catalogo, solo que sin
            redactar una respuesta en prosa.
          </p>
        </div>
      )}

      {/* --- Ventana de chat --- */}
      <section
        className="card flex h-[28rem] flex-col overflow-hidden"
        aria-label="Conversacion con el asistente"
      >
        <div className="flex-1 space-y-4 overflow-y-auto bg-panel-suave p-5">
          {mensajes.map((mensaje) =>
            mensaje.de === 'usuario' ? (
              <div key={mensaje.id} className="flex justify-end gap-2.5">
                <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 shadow-sm">
                  <p className="text-sm text-white">{mensaje.texto}</p>
                  <p className="mt-1 text-right text-[10px] text-brand-100">{mensaje.hora}</p>
                </div>
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-tinta-700 text-[11px] font-bold text-white">
                  {iniciales(usuario?.nombre)}
                </span>
              </div>
            ) : (
              <div key={mensaje.id} className="flex gap-2.5">
                <span
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600"
                  aria-hidden="true"
                >
                  <Bot size={16} />
                </span>
                <div
                  className={[
                    'max-w-[75%] rounded-2xl rounded-tl-sm border px-4 py-2.5 shadow-sm',
                    mensaje.esError
                      ? 'border-red-200 bg-red-50'
                      : 'border-linea bg-panel',
                  ].join(' ')}
                >
                  <p className="whitespace-pre-line text-sm text-tinta-700">{mensaje.texto}</p>

                  {mensaje.cursos?.length > 0 && (
                    <ul className="mt-2.5 space-y-1.5 border-t border-linea pt-2.5">
                      {mensaje.cursos.map((curso) => (
                        <li key={curso.id}>
                          <a
                            href={curso.url || undefined}
                            target="_blank"
                            rel="noreferrer"
                            className={[
                              'flex items-start gap-1.5 text-sm',
                              curso.url
                                ? 'text-brand-700 hover:underline'
                                : 'cursor-default text-tinta-700',
                            ].join(' ')}
                          >
                            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-500" />
                            <span>
                              {curso.titulo}
                              {curso.origen && (
                                <span className="text-tinta-500"> · {curso.origen}</span>
                              )}
                            </span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  )}

                  {mensaje.hora && <p className="mt-1 text-[10px] text-tinta-500">{mensaje.hora}</p>}
                </div>
              </div>
            ),
          )}

          {enviando && (
            <div className="flex gap-2.5">
              <span
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600"
                aria-hidden="true"
              >
                <Bot size={16} />
              </span>
              <div className="rounded-2xl rounded-tl-sm border border-linea bg-panel px-4 py-2.5 shadow-sm">
                <p className="text-sm text-tinta-500">Pensando…</p>
              </div>
            </div>
          )}

          <div ref={finRef} />
        </div>

        {/* --- Sugerencias --- */}
        <div className="flex flex-wrap gap-2 border-t border-linea bg-panel px-5 py-3">
          {SUGERENCIAS.map((sugerencia) => (
            <button
              key={sugerencia}
              type="button"
              onClick={() => enviarTexto(sugerencia)}
              disabled={enviando}
              className="rounded-lg border border-linea bg-panel-suave px-2.5 py-1 text-xs text-tinta-600 transition-colors hover:border-brand-300 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sugerencia}
            </button>
          ))}
        </div>

        {/* --- Entrada --- */}
        <form
          onSubmit={alEnviarFormulario}
          className="flex items-center gap-2.5 border-t border-linea bg-panel p-4"
        >
          <input
            type="text"
            value={entrada}
            onChange={(evento) => setEntrada(evento.target.value)}
            placeholder="Escribe tu pregunta sobre el catalogo de cursos…"
            aria-label="Escribe tu pregunta"
            className="input-base"
            disabled={enviando}
          />
          <button
            type="submit"
            disabled={enviando || !entrada.trim()}
            aria-label="Enviar"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send size={17} />
          </button>
        </form>
      </section>

      {/* --- Lo que si funciona --- */}
      <section>
        <h2 className="text-base font-semibold text-tinta-900">
          Mientras tanto, esto ya funciona
        </h2>
        <p className="mb-4 mt-1 text-sm text-tinta-500">
          Las capacidades reales sobre las que se construyo el asistente.
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
