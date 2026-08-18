import { useState } from 'react'
import { CheckCircle2, Inbox, BrainCircuit } from 'lucide-react'
import ContentForm from '../components/ContentForm'
import AnalysisResult from '../components/AnalysisResult'
import { Spinner } from '../components/Loaders'
import { analizarContenido } from '../services/api'

/**
 * Vista "Agregar Curso".
 *
 * Orquesta el flujo completo del MVP:
 *   formulario -> POST /contenido -> tarjeta de resultado.
 *
 * El backend guarda cada analisis en el historial, asi que el contenido
 * aparece inmediatamente en el Dashboard y en la vista Buscar.
 */
export default function AgregarContenido() {
  const [resultado, setResultado] = useState(null)
  const [tituloAnalizado, setTituloAnalizado] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [guardado, setGuardado] = useState(false)

  const manejarAnalisis = async ({ titulo, texto, origen, url }) => {
    setCargando(true)
    setError('')
    setResultado(null)
    setGuardado(false)

    try {
      const respuesta = await analizarContenido({ titulo, texto, origen, url })
      setResultado(respuesta)
      setTituloAnalizado(titulo)
    } catch (fallo) {
      // `services/api.js` ya devuelve el mensaje listo para mostrar.
      setError(fallo.message)
    } finally {
      setCargando(false)
    }
  }

  const limpiar = () => {
    setResultado(null)
    setTituloAnalizado('')
    setError('')
    setGuardado(false)
  }

  // El backend ya persistio el analisis al clasificarlo; este boton solo
  // confirma la accion al usuario. Al migrar a Oracle DB pasara a marcar el
  // contenido como parte de la biblioteca personal.
  const guardarCurso = () => setGuardado(true)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-mist-100">Agregar Contenido</h1>
        <p className="mt-1 text-sm text-mist-500">
          AthenIA analizara el texto, detectara la categoria y extraera las palabras clave.
        </p>
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-2">
        <ContentForm
          onAnalizar={manejarAnalisis}
          cargando={cargando}
          error={error}
          onLimpiar={limpiar}
        />

        <div className="space-y-4">
          {guardado && (
            <div
              role="status"
              className="flex items-center gap-2.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3.5"
            >
              <CheckCircle2 size={17} className="shrink-0 text-emerald-400" />
              <p className="text-sm text-emerald-200">
                Curso guardado en tu biblioteca. Ya aparece en el Dashboard.
              </p>
            </div>
          )}

          {cargando ? (
            <EstadoAnalizando />
          ) : resultado ? (
            <AnalysisResult
              resultado={resultado}
              titulo={tituloAnalizado}
              onGuardar={guardarCurso}
              guardado={guardado}
            />
          ) : (
            <EstadoVacio />
          )}
        </div>
      </div>
    </div>
  )
}

/** Estado de carga mientras el modelo procesa el contenido. */
function EstadoAnalizando() {
  const pasos = [
    'Normalizando el texto',
    'Detectando tecnologias',
    'Clasificando la categoria',
    'Calculando la confianza',
  ]

  return (
    <div className="card flex min-h-[320px] flex-col items-center justify-center p-8 text-center">
      <span className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600/20 text-brand-300">
        <BrainCircuit size={26} />
        <span className="absolute inset-0 animate-ping rounded-2xl bg-brand-500/20" />
      </span>

      <p className="mt-4 text-sm font-medium text-mist-100">
        AthenIA esta analizando tu contenido...
      </p>

      <ul className="mt-4 space-y-1.5">
        {pasos.map((paso, indice) => (
          <li
            key={paso}
            className="text-xs text-mist-400"
            // Escalona la aparicion de cada paso para dar sensacion de progreso.
            style={{ animation: `athenia-fade-up 0.4s ease-out ${indice * 0.35}s both` }}
          >
            {paso}
          </li>
        ))}
      </ul>

      <Spinner tamano={16} className="mt-5" />
    </div>
  )
}

/** Placeholder mostrado mientras no hay resultado que renderizar. */
function EstadoVacio() {
  return (
    <div className="card flex min-h-[320px] flex-col items-center justify-center p-8 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-ink-800 text-mist-500">
        <Inbox size={26} />
      </span>

      <p className="mt-4 text-sm font-medium text-mist-300">Sin analisis todavia</p>
      <p className="mt-1 max-w-xs text-sm text-mist-500">
        Completa el formulario y presiona "Analizar con IA" para ver la categoria y las
        palabras clave detectadas.
      </p>
    </div>
  )
}
