import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, Menu } from 'lucide-react'
import { verificarSalud } from '../services/api'
import { USUARIO_DEMO, iniciales } from '../data/usuario'

/**
 * Indicador de conexion con el backend.
 * Consulta `GET /salud` al montar; es la primera senal visual para QA de que
 * el servidor esta arriba (y de si corre con modelo real o mock).
 */
function EstadoBackend() {
  const [estado, setEstado] = useState('verificando')
  const [salud, setSalud] = useState(null)

  useEffect(() => {
    let vigente = true

    verificarSalud()
      .then((datos) => {
        if (!vigente) return
        setSalud(datos)
        setEstado('ok')
      })
      .catch(() => {
        if (!vigente) return
        setEstado('error')
      })

    // Evita actualizar el estado si el componente se desmonta antes.
    return () => {
      vigente = false
    }
  }, [])

  const colores = {
    verificando: 'bg-tinta-500',
    ok: 'bg-emerald-400',
    error: 'bg-rose-500',
  }

  const etiquetas = {
    verificando: 'Verificando',
    ok: 'API conectada',
    error: 'API caida',
  }

  const usaModeloReal = salud?.motor === 'modelo_ml_real'

  const detalle =
    estado === 'error'
      ? 'Backend sin conexion (puerto 8000)'
      : salud
        ? `API v${salud.version} · motor: ${salud.motor} · artefacto: ${salud.modelo_cargado}`
        : 'Verificando conexion...'

  return (
    <div className="hidden items-center gap-2 md:flex" title={detalle}>
      <div className="flex items-center gap-2 rounded-full border border-linea bg-panel px-3 py-1.5">
        <span className={`h-2 w-2 rounded-full ${colores[estado]}`} />
        <span className="text-xs text-tinta-600">{etiquetas[estado]}</span>
      </div>

      {/* Distingue de un vistazo si responde el modelo entrenado o el fallback. */}
      {estado === 'ok' && salud && (
        <span
          className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
            usaModeloReal
              ? 'border-brand-500/50 bg-brand-50 text-brand-600'
              : 'border-amber-200 bg-amber-50 text-amber-800'
          }`}
        >
          {usaModeloReal ? 'Modelo IA' : 'Reglas'}
        </span>
      )}
    </div>
  )
}

/**
 * Barra superior: buscador rapido, estado de la API y perfil de usuario.
 * `onAbrirMenu` despliega el Sidebar en pantallas pequenas.
 */
export default function Header({ onAbrirMenu = () => {}, usuario = USUARIO_DEMO.nombre }) {
  const navegar = useNavigate()
  const [consulta, setConsulta] = useState('')

  const buscar = (evento) => {
    evento.preventDefault()
    const termino = consulta.trim()
    if (!termino) return
    // La vista Buscar lee el termino desde la query string.
    navegar(`/buscar?q=${encodeURIComponent(termino)}`)
  }

  const avatar = iniciales(usuario)

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-linea bg-panel/90 px-4 py-3 backdrop-blur-md lg:px-8">
      <button
        type="button"
        onClick={onAbrirMenu}
        className="rounded-lg p-2 text-tinta-700 hover:bg-lienzo lg:hidden"
        aria-label="Abrir menu"
      >
        <Menu size={20} />
      </button>

      {/* Buscador rapido */}
      <form onSubmit={buscar} className="relative flex-1 max-w-md" role="search">
        <Search
          size={16}
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-tinta-500"
        />
        <input
          type="search"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder="Buscar cursos, temas o tecnologias..."
          aria-label="Buscador rapido"
          className="input-base pl-10"
        />
      </form>

      <div className="ml-auto flex items-center gap-3">
        <EstadoBackend />

        {/* Notificaciones: fuera del alcance del MVP. Se marca como
            deshabilitado en vez de dejar un boton que no responde al clic, y
            se quito el punto de "no leidas" porque anunciaba avisos que no
            existen — en la demo, un jurado que lo pulse no veria nada. */}
        <button
          type="button"
          disabled
          title="Notificaciones (proximamente)"
          className="relative rounded-lg p-2 text-tinta-500 opacity-50 transition-colors"
          aria-label="Notificaciones (proximamente)"
        >
          <Bell size={19} />
        </button>

        {/* Perfil */}
        <div className="flex items-center gap-2.5 rounded-xl border border-linea bg-panel px-2.5 py-1.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-xs font-bold text-white">
            {avatar}
          </span>
          <div className="hidden leading-tight sm:block">
            <p className="text-xs font-semibold text-tinta-900">{usuario}</p>
            <p className="text-[10px] text-tinta-600">{USUARIO_DEMO.rol}</p>
          </div>
        </div>
      </div>
    </header>
  )
}
