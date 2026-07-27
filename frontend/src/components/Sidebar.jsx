import { NavLink } from 'react-router-dom'
import {
  Home,
  PlusCircle,
  Search,
  LayoutGrid,
  Sparkles,
  LogOut,
  X,
} from 'lucide-react'
import Logo from './Logo'

/** Rutas de la navegacion principal. */
const NAVEGACION = [
  { to: '/', etiqueta: 'Inicio', icono: Home, exacto: true },
  { to: '/agregar', etiqueta: 'Agregar Curso', icono: PlusCircle },
  { to: '/buscar', etiqueta: 'Buscar', icono: Search },
  { to: '/categorias', etiqueta: 'Categorias', icono: LayoutGrid },
]

/**
 * Navegacion lateral de AthenIA.
 *
 * En pantallas < lg se comporta como drawer: se despliega sobre el contenido
 * y `onCerrar` lo oculta al navegar o al tocar el fondo.
 */
export default function Sidebar({ abierto = false, onCerrar = () => {} }) {
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
          'border-r border-ink-700 bg-ink-900 p-4',
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
              <p className="text-lg font-bold tracking-tight">
                Athen<span className="text-brand-400">IA</span>
              </p>
              <p className="text-[10px] uppercase tracking-widest text-mist-500">
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
        <nav className="flex flex-col gap-1">
          {NAVEGACION.map(({ to, etiqueta, icono: Icono, exacto }) => (
            <NavLink key={to} to={to} end={exacto} className={claseEnlace} onClick={onCerrar}>
              <Icono size={18} strokeWidth={2} />
              {etiqueta}
            </NavLink>
          ))}
        </nav>

        {/* --- Aviso de estado del MVP --- */}
        <div className="mt-auto space-y-3">
          <div className="rounded-xl border border-ink-700 bg-ink-850 p-3.5">
            <div className="mb-1.5 flex items-center gap-2 text-brand-300">
              <Sparkles size={15} />
              <span className="text-xs font-semibold">MVP Semana 1-2</span>
            </div>
            <p className="text-[11px] leading-relaxed text-mist-500">
              El modelo de IA responde con datos simulados. La integracion real
              llega en la Semana 3.
            </p>
          </div>

          <button
            type="button"
            className="flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-mist-500 transition-colors hover:bg-ink-800 hover:text-mist-100"
          >
            <LogOut size={18} />
            Cerrar sesion
          </button>
        </div>
      </aside>
    </>
  )
}
