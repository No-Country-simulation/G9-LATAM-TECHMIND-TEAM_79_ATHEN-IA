import { useState } from 'react'
import { Sparkles, Loader2, AlertCircle, RotateCcw } from 'lucide-react'

const LIMITE_TEXTO = 3000

const ORIGENES = [
  'Alura',
  'Oracle Next Education',
  'Documentacion oficial',
  'Blog / Articulo',
  'Video / Curso externo',
  'Otro',
]

/**
 * Formulario de ingreso de contenido tecnico.
 *
 * No conoce el backend: recibe `onAnalizar` desde la pagina, que es quien
 * hace la llamada HTTP. Asi el componente se puede probar de forma aislada.
 *
 * @param {Function} onAnalizar  async ({titulo, texto, origen, url}) => void
 * @param {boolean}  cargando    Deshabilita el formulario durante el analisis.
 * @param {string}   error       Mensaje de error a mostrar (o vacio).
 * @param {Function} onLimpiar   Reinicia el formulario y el resultado previo.
 */
export default function ContentForm({
  onAnalizar,
  cargando = false,
  error = '',
  onLimpiar = () => {},
}) {
  const [formulario, setFormulario] = useState({
    titulo: '',
    texto: '',
    origen: '',
    url: '',
  })
  // Errores de validacion en cliente, para no gastar una llamada al backend.
  const [errores, setErrores] = useState({})

  const actualizar = (campo) => (evento) => {
    setFormulario((previo) => ({ ...previo, [campo]: evento.target.value }))
    setErrores((previo) => ({ ...previo, [campo]: '' }))
  }

  const validar = () => {
    const nuevos = {}
    if (!formulario.titulo.trim()) nuevos.titulo = 'El titulo es obligatorio.'
    if (!formulario.texto.trim()) nuevos.texto = 'El contenido es obligatorio.'
    else if (formulario.texto.trim().length < 20)
      nuevos.texto = 'Ingresa al menos 20 caracteres para que la IA pueda analizarlo.'
    setErrores(nuevos)
    return Object.keys(nuevos).length === 0
  }

  const enviar = (evento) => {
    evento.preventDefault()
    if (!validar()) return
    onAnalizar({
      titulo: formulario.titulo.trim(),
      texto: formulario.texto.trim(),
      origen: formulario.origen,
      url: formulario.url.trim(),
    })
  }

  const limpiar = () => {
    setFormulario({ titulo: '', texto: '', origen: '', url: '' })
    setErrores({})
    onLimpiar()
  }

  const caracteres = formulario.texto.length

  return (
    <form onSubmit={enviar} className="card p-6" noValidate>
      <h2 className="text-lg font-semibold text-tinta-900">Agregar Nuevo Curso</h2>
      <p className="mt-1 text-sm text-tinta-500">
        Ingresa la informacion del contenido tecnico que deseas analizar.
      </p>

      <div className="mt-6 space-y-5">
        {/* --- Titulo --- */}
        <div>
          <label htmlFor="titulo" className="mb-1.5 block text-sm font-medium text-tinta-700">
            Titulo del curso o contenido <span className="text-brand-600">*</span>
          </label>
          <input
            id="titulo"
            type="text"
            value={formulario.titulo}
            onChange={actualizar('titulo')}
            disabled={cargando}
            maxLength={300}
            placeholder="Ej: Introduccion a Spring Boot"
            aria-invalid={Boolean(errores.titulo)}
            aria-describedby={errores.titulo ? 'error-titulo' : undefined}
            className={`input-base ${errores.titulo ? 'border-rose-400' : ''}`}
          />
          {errores.titulo && (
            <p id="error-titulo" className="mt-1.5 text-xs text-rose-600">
              {errores.titulo}
            </p>
          )}
        </div>

        {/* --- Texto / Descripcion --- */}
        <div>
          <div className="mb-1.5 flex items-baseline justify-between">
            <label htmlFor="texto" className="text-sm font-medium text-tinta-700">
              Descripcion / Contenido <span className="text-brand-600">*</span>
            </label>
            <span
              className={`text-xs ${
                caracteres > LIMITE_TEXTO ? 'text-rose-600' : 'text-tinta-500'
              }`}
            >
              {caracteres}/{LIMITE_TEXTO}
            </span>
          </div>
          <textarea
            id="texto"
            rows={7}
            value={formulario.texto}
            onChange={actualizar('texto')}
            disabled={cargando}
            maxLength={LIMITE_TEXTO}
            placeholder="Escribe o pega aqui la descripcion, temario o contenido del curso..."
            aria-invalid={Boolean(errores.texto)}
            aria-describedby={errores.texto ? 'error-texto' : undefined}
            className={`input-base resize-y leading-relaxed ${
              errores.texto ? 'border-rose-400' : ''
            }`}
          />
          {errores.texto && (
            <p id="error-texto" className="mt-1.5 text-xs text-rose-600">
              {errores.texto}
            </p>
          )}
        </div>

        {/* --- Metadatos opcionales --- */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="origen" className="mb-1.5 block text-sm font-medium text-tinta-700">
              Origen del contenido{' '}
              <span className="font-normal text-tinta-500">(opcional)</span>
            </label>
            <select
              id="origen"
              value={formulario.origen}
              onChange={actualizar('origen')}
              disabled={cargando}
              className="input-base"
            >
              <option value="">Selecciona el origen</option>
              {ORIGENES.map((origen) => (
                <option key={origen} value={origen}>
                  {origen}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="url" className="mb-1.5 block text-sm font-medium text-tinta-700">
              URL <span className="font-normal text-tinta-500">(si aplica)</span>
            </label>
            <input
              id="url"
              type="url"
              value={formulario.url}
              onChange={actualizar('url')}
              disabled={cargando}
              placeholder="https://..."
              className="input-base"
            />
          </div>
        </div>
      </div>

      {/* --- Error devuelto por el backend --- */}
      {error && (
        <div
          role="alert"
          className="mt-5 flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5"
        >
          <AlertCircle size={17} className="mt-0.5 shrink-0 text-rose-600" />
          <p className="text-sm text-rose-700">{error}</p>
        </div>
      )}

      {/* --- Acciones --- */}
      <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
        <button type="button" onClick={limpiar} disabled={cargando} className="btn-ghost">
          <RotateCcw size={16} />
          Limpiar
        </button>

        <button type="submit" disabled={cargando} className="btn-primary">
          {cargando ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Analizando...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Analizar con IA
            </>
          )}
        </button>
      </div>
    </form>
  )
}
