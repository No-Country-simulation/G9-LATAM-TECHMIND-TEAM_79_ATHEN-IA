import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Info, Loader2 } from 'lucide-react'
import Logo from '../components/Logo'
import { useAuth } from '../hooks/useAuth'

/**
 * Pantalla de acceso (pantalla 01 del mockup).
 *
 * Autenticacion real (Semana 5): valida contra `POST /auth/login` /
 * `POST /auth/registro` y guarda el JWT devuelto (ver `hooks/useAuth.js`).
 * El resto de la aplicacion queda detras de `RutaProtegida` (`App.jsx`): sin
 * sesion, cualquier ruta redirige aqui.
 *
 * El primer usuario que se registra en una instalacion nueva de AthenIA
 * recibe el rol 'admin' automaticamente (ver `domain.usuarios.rol_por_defecto`
 * en el backend); el resto entra como 'estudiante'.
 */
export default function Login() {
  const navegar = useNavigate()
  const ubicacion = useLocation()
  const { iniciarSesion, registrarse, cargando, error, limpiarError } = useAuth()

  const [modo, setModo] = useState('login') // 'login' | 'registro'
  const [correo, setCorreo] = useState('')
  const [clave, setClave] = useState('')
  const [nombre, setNombre] = useState('')
  const [verClave, setVerClave] = useState(false)

  const destino = ubicacion.state?.desde?.pathname || '/'

  const cambiarModo = (nuevoModo) => {
    setModo(nuevoModo)
    limpiarError()
  }

  const enviar = async (evento) => {
    evento.preventDefault()

    const exito =
      modo === 'login' ? await iniciarSesion(correo, clave) : await registrarse(correo, clave, nombre)

    if (exito) {
      navegar(destino, { replace: true })
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* --- Panel de marca (oscuro) --- */}
      <aside className="relative hidden w-1/2 flex-col items-center justify-center bg-ink-900 p-12 text-center lg:flex">
        <Logo className="h-24 w-24" />

        <h1 className="mt-6 text-4xl font-bold tracking-tight text-mist-100">
          Athen<span className="text-brand-400">IA</span>
        </h1>

        <p className="mt-4 max-w-xs text-sm leading-relaxed text-mist-300">
          Tu asistente inteligente para organizar y potenciar tu conocimiento
          tecnico.
        </p>

        <figure className="absolute bottom-12 left-12 right-12">
          <blockquote className="text-xs italic leading-relaxed text-mist-400">
            &ldquo;El conocimiento es como un jardin: si no se cultiva, no puede
            ser cosechado.&rdquo;
          </blockquote>
          <figcaption className="mt-2 text-xs text-mist-500">— Platon</figcaption>
        </figure>
      </aside>

      {/* --- Formulario (claro) --- */}
      <main className="flex w-full flex-col items-center justify-center bg-panel px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          {/* Marca compacta, solo en movil donde el panel lateral se oculta. */}
          <div className="mb-8 flex items-center justify-center gap-2.5 lg:hidden">
            <Logo className="h-10 w-10" />
            <span className="text-2xl font-bold tracking-tight text-tinta-900">
              Athen<span className="text-brand-600">IA</span>
            </span>
          </div>

          <h2 className="text-center text-2xl font-bold tracking-tight text-tinta-900">
            {modo === 'login' ? 'Bienvenido de nuevo' : 'Crea tu cuenta'}
          </h2>
          <p className="mt-1.5 text-center text-sm text-tinta-500">
            {modo === 'login' ? 'Inicia sesion para continuar' : 'Un minuto y estas dentro'}
          </p>

          {/* El primer registro de una instalacion nueva queda como admin. */}
          {modo === 'registro' && (
            <div
              role="status"
              className="mt-6 flex items-start gap-2.5 rounded-xl border border-brand-100 bg-brand-50 p-3"
            >
              <Info size={15} className="mt-0.5 shrink-0 text-brand-600" aria-hidden="true" />
              <p className="text-xs leading-relaxed text-brand-700">
                Si eres la primera persona en registrarse en este AthenIA, tu
                cuenta queda como administradora automaticamente.
              </p>
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700"
            >
              {error}
            </div>
          )}

          <form onSubmit={enviar} className="mt-6 space-y-4">
            {modo === 'registro' && (
              <div>
                <label htmlFor="nombre" className="mb-1.5 block text-sm font-medium text-tinta-700">
                  Nombre
                </label>
                <input
                  id="nombre"
                  type="text"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Tu nombre"
                  autoComplete="name"
                  required
                  className="input-base"
                />
              </div>
            )}

            <div>
              <label htmlFor="correo" className="mb-1.5 block text-sm font-medium text-tinta-700">
                Correo electronico
              </label>
              <input
                id="correo"
                type="email"
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
                placeholder="ejemplo@correo.com"
                autoComplete="username"
                required
                className="input-base"
              />
            </div>

            <div>
              <label htmlFor="clave" className="mb-1.5 block text-sm font-medium text-tinta-700">
                Contrasena
              </label>
              <div className="relative">
                <input
                  id="clave"
                  type={verClave ? 'text' : 'password'}
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  placeholder="••••••••"
                  autoComplete={modo === 'login' ? 'current-password' : 'new-password'}
                  minLength={modo === 'registro' ? 8 : undefined}
                  required
                  className="input-base pr-11"
                />
                <button
                  type="button"
                  onClick={() => setVerClave((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-tinta-500 transition-colors hover:text-tinta-900"
                  aria-label={verClave ? 'Ocultar contrasena' : 'Mostrar contrasena'}
                >
                  {verClave ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              {modo === 'registro' && (
                <p className="mt-1.5 text-xs text-tinta-500">Minimo 8 caracteres.</p>
              )}
            </div>

            <button type="submit" disabled={cargando} className="btn-primary w-full">
              {cargando ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 size={16} className="animate-spin" />
                  {modo === 'login' ? 'Ingresando...' : 'Creando cuenta...'}
                </span>
              ) : modo === 'login' ? (
                'Iniciar sesion'
              ) : (
                'Crear cuenta'
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-tinta-500">
            {modo === 'login' ? (
              <>
                ¿No tienes una cuenta?{' '}
                <button
                  type="button"
                  onClick={() => cambiarModo('registro')}
                  className="font-semibold text-brand-600 hover:underline"
                >
                  Registrate
                </button>
              </>
            ) : (
              <>
                ¿Ya tienes cuenta?{' '}
                <button
                  type="button"
                  onClick={() => cambiarModo('login')}
                  className="font-semibold text-brand-600 hover:underline"
                >
                  Inicia sesion
                </button>
              </>
            )}
          </p>
        </div>
      </main>
    </div>
  )
}
