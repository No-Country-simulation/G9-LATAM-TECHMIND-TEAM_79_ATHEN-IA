import { Link } from 'react-router-dom'
import { BrainCircuit, Tag, Save, FolderOpen, Check, AlertTriangle } from 'lucide-react'
import CategoryBadge, { KeywordBadge } from './CategoryBadge'
import { Spinner } from './Loaders'
import { aPorcentaje, colorDeCategoria, estilosDeCategoria } from '../data/categorias'

/** Barra de confianza del modelo. */
function BarraConfianza({ probabilidad, color }) {
  const porcentaje = aPorcentaje(probabilidad)

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-mist-500">
          Confianza del modelo
        </span>
        <span className="text-sm font-bold text-mist-100">{porcentaje}%</span>
      </div>

      <div
        className="h-2 w-full overflow-hidden rounded-full bg-ink-800"
        role="progressbar"
        aria-valuenow={porcentaje}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Confianza del modelo"
      >
        <div
          className="h-full rounded-full transition-[width] duration-700 ease-out"
          style={{ width: `${porcentaje}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

/**
 * Tarjeta de resultado del analisis de IA.
 *
 * Consume la respuesta cruda de `POST /contenido`. Los campos extra
 * (`resumen`, `categorias_relacionadas`) son opcionales: si el modelo real no
 * los devuelve, la tarjeta simplemente no los renderiza.
 *
 * @param {object}   resultado  Respuesta del backend.
 * @param {string}   titulo     Titulo enviado, para dar contexto.
 * @param {Function} onGuardar  Accion del boton "Guardar Curso".
 * @param {boolean}  guardando  Muestra el spinner en el boton.
 * @param {boolean}  guardado   Cambia el boton a estado confirmado.
 */
export default function AnalysisResult({
  resultado,
  titulo = '',
  onGuardar,
  guardando = false,
  guardado = false,
}) {
  if (!resultado) return null

  const {
    categoria,
    probabilidad,
    informacion_adicional: palabrasClave = [],
    resumen,
    categorias_relacionadas: relacionadas = [],
    modelo,
    id,
    nivel_confianza: nivelConfianza,
  } = resultado

  const color = colorDeCategoria(categoria)

  return (
    <section className="card animate-fade-up overflow-hidden" aria-live="polite">
      {/* --- Encabezado --- */}
      <div className="flex items-start gap-3 border-b border-ink-700 bg-ink-800/40 p-5">
        <span
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
          style={estilosDeCategoria(categoria)}
        >
          <BrainCircuit size={20} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-mist-100">Resultado del Analisis</h2>
          <p className="truncate text-sm text-mist-500">
            {titulo ? `"${titulo}"` : 'Analisis generado por AthenIA'}
          </p>
        </div>
        {id != null && (
          <span className="shrink-0 rounded-lg border border-ink-700 px-2 py-1 text-[11px] text-mist-500">
            #{id}
          </span>
        )}
      </div>

      <div className="space-y-6 p-5">
        {/* --- Aviso de confianza baja ---
            El modelo siempre devuelve una categoria: es un clasificador, no
            tiene la opcion de "no se". Ante texto sin senal cae a su suelo
            (~37%) y, sin este aviso, la interfaz pintaba ese resultado con la
            misma autoridad visual que uno del 93%. */}
        {nivelConfianza === 'baja' && (
          <div
            role="status"
            className="flex items-start gap-2.5 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3.5"
          >
            <AlertTriangle size={17} className="mt-0.5 shrink-0 text-amber-400" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-amber-100">Confianza baja</p>
              <p className="mt-0.5 text-xs leading-relaxed text-amber-200/80">
                El modelo no encontro senales claras en este texto. Revisa la
                categoria antes de darla por buena, o agrega mas detalle tecnico
                al contenido.
              </p>
            </div>
          </div>
        )}

        {/* --- Categoria principal + confianza --- */}
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-mist-500">
              Categoria principal
            </p>
            <CategoryBadge categoria={categoria} tamano="lg" conIcono />
          </div>

          <div className="flex items-end">
            <div className="w-full">
              <BarraConfianza probabilidad={probabilidad} color={color} />
            </div>
          </div>
        </div>

        {/* --- Palabras clave --- */}
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-mist-500">
            <Tag size={13} />
            Palabras clave detectadas
          </p>

          {palabrasClave.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              {palabrasClave.map((palabra) => (
                <li key={palabra}>
                  <KeywordBadge>{palabra}</KeywordBadge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-mist-500">
              No se detectaron tecnologias conocidas en este contenido.
            </p>
          )}
        </div>

        {/* --- Resumen --- */}
        {resumen && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-mist-500">
              Descripcion analizada
            </p>
            <p className="rounded-xl border border-ink-700 bg-ink-900 p-3.5 text-sm leading-relaxed text-mist-300">
              {resumen}
            </p>
          </div>
        )}

        {/* --- Categorias relacionadas --- */}
        {relacionadas.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-mist-500">
              Categorias relacionadas
            </p>
            <ul className="flex flex-wrap gap-2">
              {relacionadas.map((otra) => (
                <li key={otra}>
                  <CategoryBadge categoria={otra} tamano="sm" />
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* --- Acciones --- */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-700 pt-5">
          <p className="text-[11px] text-mist-500">
            Procesado por <span className="text-mist-300">{modelo ?? 'AthenIA'}</span>
          </p>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="btn-ghost"
              onClick={onGuardar}
              disabled={guardando || guardado}
            >
              {guardando ? (
                <Spinner tamano={16} />
              ) : guardado ? (
                <Check size={16} className="text-emerald-400" />
              ) : (
                <Save size={16} />
              )}
              {guardado ? 'Guardado' : 'Guardar Curso'}
            </button>

            <Link to="/buscar" className="btn-primary">
              <FolderOpen size={16} />
              Ver en Mis Cursos
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
