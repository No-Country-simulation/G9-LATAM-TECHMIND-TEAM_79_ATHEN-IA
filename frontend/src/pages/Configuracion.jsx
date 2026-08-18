import { useEffect, useState } from 'react'
import {
  Settings,
  Server,
  Cpu,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  History,
} from 'lucide-react'
import { Skeleton, Spinner } from '../components/Loaders'
import ConfirmDialog from '../components/ConfirmDialog'
import { limpiarHistorial, verificarSalud } from '../services/api'
import { useHistorialBusquedas } from '../hooks/useHistorialBusquedas'

/**
 * Vista "Configuracion".
 *
 * No es un placeholder: usa endpoints que ya existen (`GET /salud`,
 * `DELETE /contenidos`) y el `localStorage` del navegador. Muestra el estado
 * real del sistema y permite las dos acciones de mantenimiento que el equipo
 * necesita durante la demo:
 *
 *   - Vaciar el historial del servidor (para partir de cero ante el jurado).
 *   - Borrar las busquedas guardadas en este navegador.
 *
 * Las preferencias de usuario (tema, idioma, notificaciones) llegan despues
 * del MVP y no se simulan aqui: prometer un interruptor que no hace nada es
 * peor que no mostrarlo.
 */

/** Fila de dato del sistema. */
function Dato({ etiqueta, valor, destacado = false }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-linea py-2.5 last:border-0">
      <span className="text-sm text-tinta-600">{etiqueta}</span>
      <span
        className={`truncate text-sm font-medium ${
          destacado ? 'text-brand-700' : 'text-tinta-900'
        }`}
        title={String(valor)}
      >
        {valor}
      </span>
    </div>
  )
}

export default function Configuracion() {
  const [salud, setSalud] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [recarga, setRecarga] = useState(0)

  const historialBusquedas = useHistorialBusquedas()

  const [confirmando, setConfirmando] = useState(false)
  const [limpiando, setLimpiando] = useState(false)
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    const controlador = new AbortController()
    setCargando(true)

    verificarSalud()
      .then((datos) => {
        if (controlador.signal.aborted) return
        setSalud(datos)
        setError('')
      })
      .catch((fallo) => {
        if (controlador.signal.aborted) return
        setError(fallo.message)
        setSalud(null)
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false)
      })

    return () => controlador.abort()
  }, [recarga])

  const vaciarHistorialServidor = async () => {
    setLimpiando(true)
    setAviso('')
    try {
      const resultado = await limpiarHistorial()
      setAviso(`Historial vaciado: ${resultado.eliminados} contenido(s) eliminado(s).`)
      setRecarga((n) => n + 1) // refresca el contador de /salud
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setLimpiando(false)
      setConfirmando(false)
    }
  }

  const usaModeloReal = salud?.motor === 'modelo_ml_real'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-tinta-900">
          <Settings size={24} className="text-brand-600" aria-hidden="true" />
          Configuracion
        </h1>
        <p className="mt-1 text-sm text-tinta-600">
          Estado del sistema y mantenimiento de datos.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5"
        >
          <AlertCircle size={17} className="mt-0.5 shrink-0 text-rose-600" aria-hidden="true" />
          <p className="text-sm text-rose-700">{error}</p>
        </div>
      )}

      {aviso && (
        <div
          role="status"
          className="flex items-start gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5"
        >
          <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-emerald-600" aria-hidden="true" />
          <p className="text-sm text-emerald-700">{aviso}</p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* --- Estado del servicio --- */}
        <section className="card p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-base font-semibold text-tinta-900">
              <Server size={16} className="text-brand-600" aria-hidden="true" />
              Servicio
            </h2>
            <button
              type="button"
              onClick={() => setRecarga((n) => n + 1)}
              className="rounded-lg p-1.5 text-tinta-600 transition-colors hover:bg-lienzo hover:text-tinta-900"
              aria-label="Actualizar estado del servicio"
            >
              <RefreshCw size={15} className={cargando ? 'animate-spin' : ''} />
            </button>
          </div>

          {cargando ? (
            <Skeleton className="h-32 w-full rounded-xl" />
          ) : salud ? (
            <div>
              <Dato etiqueta="Estado" valor={salud.estado === 'ok' ? 'Operativo' : salud.estado} />
              <Dato etiqueta="Version de la API" valor={`v${salud.version}`} />
              <Dato etiqueta="Entorno" valor={salud.entorno} />
              <Dato
                etiqueta="Contenidos en el historial"
                valor={salud.contenidos_en_historial}
              />
            </div>
          ) : (
            <p className="text-sm text-tinta-600">Sin conexion con el servicio.</p>
          )}
        </section>

        {/* --- Motor de IA --- */}
        <section className="card p-6">
          <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-tinta-900">
            <Cpu size={16} className="text-brand-600" aria-hidden="true" />
            Motor de clasificacion
          </h2>

          {cargando ? (
            <Skeleton className="h-32 w-full rounded-xl" />
          ) : salud ? (
            <div>
              <Dato
                etiqueta="Motor activo"
                valor={usaModeloReal ? 'Modelo entrenado' : 'Clasificador por reglas'}
                destacado={usaModeloReal}
              />
              <Dato etiqueta="Artefacto" valor={salud.modelo_cargado} />
              <Dato etiqueta="Tipo" valor={salud.detalle_modelo || '—'} />

              {!usaModeloReal && (
                <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs leading-relaxed text-amber-800">
                  El modelo entrenado no esta disponible. La API responde con el
                  clasificador por reglas: sigue funcionando, pero con menor
                  precision.
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-tinta-600">Sin conexion con el servicio.</p>
          )}
        </section>
      </div>

      {/* --- Mantenimiento --- */}
      <section className="card p-6">
        <h2 className="text-base font-semibold text-tinta-900">Mantenimiento de datos</h2>
        <p className="mb-5 mt-1 text-sm text-tinta-600">
          Acciones utiles para dejar el entorno limpio antes de una demostracion.
        </p>

        <div className="space-y-3">
          {/* Historial del servidor */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-linea bg-panel-suave p-4">
            <div className="min-w-0">
              <p className="text-sm font-medium text-tinta-900">Historial de contenidos</p>
              <p className="mt-0.5 text-xs text-tinta-600">
                Borra del servidor todos los analisis guardados.
                {salud && ` Ahora hay ${salud.contenidos_en_historial}.`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setConfirmando(true)}
              disabled={limpiando || !salud}
              className="btn-ghost shrink-0"
            >
              {limpiando ? <Spinner tamano={16} /> : <Trash2 size={16} aria-hidden="true" />}
              Vaciar
            </button>
          </div>

          {/* Historial local */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-linea bg-panel-suave p-4">
            <div className="min-w-0">
              <p className="text-sm font-medium text-tinta-900">Busquedas recientes</p>
              <p className="mt-0.5 text-xs text-tinta-600">
                Guardadas solo en este navegador.{' '}
                {historialBusquedas.entradas.length > 0
                  ? `Hay ${historialBusquedas.entradas.length}.`
                  : 'No hay ninguna.'}
              </p>
            </div>
            <button
              type="button"
              onClick={historialBusquedas.limpiar}
              disabled={historialBusquedas.entradas.length === 0}
              className="btn-ghost shrink-0"
            >
              <History size={16} aria-hidden="true" />
              Limpiar
            </button>
          </div>
        </div>

        <p className="mt-5 text-xs leading-relaxed text-tinta-600">
          Las preferencias de usuario (tema, idioma y notificaciones) llegan
          despues del MVP. No se muestran aqui porque todavia no tendrian efecto.
        </p>
      </section>

      <ConfirmDialog
        abierto={confirmando}
        titulo="¿Vaciar el historial?"
        mensaje="Se eliminaran del servidor todos los contenidos analizados. Esta accion no se puede deshacer."
        textoConfirmar="Vaciar historial"
        onConfirmar={vaciarHistorialServidor}
        onCancelar={() => setConfirmando(false)}
      />
    </div>
  )
}
