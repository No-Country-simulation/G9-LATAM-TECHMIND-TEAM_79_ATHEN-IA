import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  Home,
  Library,
  PlusCircle,
  Search,
  LayoutGrid,
  Sparkles,
  Bot,
  Settings,
  LogOut,
  X,
} from 'lucide-react'
import Logo from './Logo'
import ConfirmDialog from './ConfirmDialog'
import { limpiarHistorialBusquedas } from '../hooks/useHistorialBusquedas'

/**
 * Navegacion principal, en el orden del diseno de referencia.
 *
 * `Asistente IA` esta marcado como `enConstruccion`: la ruta existe y la vista
 * explica con honestidad que la funcionalidad llega despues del MVP. Se deja
 * visible —en vez de ocultarla— porque forma parte de la propuesta de producto,
 * pero se distingue del resto para no prometer lo que aun no responde.
 */
const NAVEGACION = [
  { to: '/', etiqueta: 'Inicio', icono: Home, exacto: true },
  { to: '/mis-cursos', etiqueta: 'Mis Cursos', icono: Library },
  { to: '/agregar', etiqueta: 'Agregar Curso', icono: PlusCircle },
  { to: '/buscar', etiqueta: 'Buscar', icono: Search },
  { to: '/categorias', etiqueta: 'Categorias', icono: LayoutGrid },
  { to: '/recomendaciones', etiqueta: 'Recomendaciones', icono: Sparkles },
  { to: '/asistente', etiqueta: 'Asistente IA', icono: Bot, enConstruccion: true },
  { to: '/configuracion', etiqueta: 'Configuracion', icono: Settings },
]

/**
 * Navegacion lateral de AthenIA.
 *
 * En pantallas < lg se comporta como drawer: se despliega sobre el contenido
 * y `onCerrar` lo oculta al navegar o al tocar el fondo.
 */
export default function Sidebar({ abierto = false, onCerrar = () => {} }) {
  const navegar = useNavigate()
  const [confirmandoSalida, setConfirmandoSalida] = useState(false)

  /**
   * Cierre de sesion.
   *
   * Todavia no hay autenticacion (llega despues del MVP), asi que no hay token
   * que invalidar. Lo que si existe son datos locales del usuario: el historial
   * de busquedas en `localStorage`. Se borran de verdad y se vuelve al inicio.
   *
   * Cuando exista login, este mismo handler sumara la invalidacion del token y
   * la redireccion a `/login`, sin cambiar nada del resto del Sidebar.
   */
  const cerrarSesion = () => {
    limpiarHistorialBusquedas()
    setConfirmandoSalida(false)
    onCerrar() // repliega el drawer en movil
    navegar('/')
  }

  const claseEnlace = ({ isActive }) =>
    [
      'flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors',
      isActive
        ? 'bg-brand-600 text-white shadow-lg shadow-brand-700/25'
        : 'text-mist-300 hover:bg-ink-800 hover:text-mist-100',
    ].join(' ')

  return (
    <>
      {/* Fondo oscurecido en movil */}
      {abierto && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onCerrar}
          aria-hidden="true"
        />
      )}

      <aside
        className={[
          'fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col',
          'border-r border-ink-700 bg-ink-900 p-4 text-mist-300',
          'transition-transform duration-300 lg:static lg:translate-x-0',
          abierto ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
        aria-label="Navegacion principal"
      >
        {/* --- Marca --- */}
        <div className="mb-8 flex items-center justify-between px-1.5 pt-1.5">
          <div className="flex items-center gap-2.5">
            <Logo className="h-9 w-9 text-brand-400" />
            <div className="leading-tight">
              {/* Color explicito: sin el hereda del <body>, que en el tema
                  claro es texto oscuro y aqui quedaria invisible. */}
              <p className="text-lg font-bold tracking-tight text-mist-100">
                Athen<span className="text-brand-400">IA</span>
              </p>
              <p className="text-[10px] uppercase tracking-widest text-mist-400">
                Conocimiento Tecnico
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onCerrar}
            className="rounded-lg p-1 text-mist-500 hover:text-mist-100 lg:hidden"
            aria-label="Cerrar menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* --- Enlaces --- */}
        <nav className="flex flex-col gap-1" aria-label="Secciones">
          {NAVEGACION.map(({ to, etiqueta, icono: Icono, exacto, enConstruccion }) => (
            <NavLink key={to} to={to} end={exacto} className={claseEnlace} onClick={onCerrar}>
              <Icono size={18} strokeWidth={2} aria-hidden="true" />
              <span className="flex-1 truncate">{etiqueta}</span>
              {enConstruccion && (
                <span
                  className="rounded border border-ink-600 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-mist-400"
                  title="Funcionalidad posterior al MVP"
                >
                  Pronto
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* --- Estado del proyecto ---
            Esta tarjeta anunciaba "datos simulados / integracion real en la
            Semana 3". Desde la Semana 3 el modelo entrenado esta activo, asi
            que el texto era FALSO: un jurado leyendolo en el Demo Day habria
            creido que la clasificacion es de mentira. El estado del motor en
            vivo lo muestra el badge del Header ("Modelo IA" / "Reglas"), que
            se alimenta de `GET /salud`. */}
        <div className="mt-auto space-y-3">
          <div className="rounded-xl border border-ink-700 bg-ink-850 p-3.5">
            <div className="mb-1.5 flex items-center gap-2 text-brand-300">
              <Sparkles size={15} />
              <span className="text-xs font-semibold">MVP Semana 5 · Demo Day</span>
            </div>
            <p className="text-[11px] leading-relaxed text-mist-400">
              Modelo de IA entrenado, recomendaciones y analiticas activas.
              El indicador del encabezado muestra que motor responde ahora mismo.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setConfirmandoSalida(true)}
            className="flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-mist-500 transition-colors hover:bg-ink-800 hover:text-mist-100"
          >
            <LogOut size={18} />
            Cerrar sesion
          </button>
        </div>
      </aside>

      <ConfirmDialog
        abierto={confirmandoSalida}
        titulo="¿Cerrar sesion?"
        mensaje="Se borrara tu historial de busquedas guardado en este navegador. El contenido analizado se conserva en el servidor."
        textoConfirmar="Cerrar sesion"
        onConfirmar={cerrarSesion}
        onCancelar={() => setConfirmandoSalida(false)}
      />
    </>
  )
}
