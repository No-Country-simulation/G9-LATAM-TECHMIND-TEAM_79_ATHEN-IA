import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { iniciarSesion as iniciarSesionApi, registrarUsuario as registrarUsuarioApi } from '../services/api'
import { guardarSesion, leerSesion } from '../services/sesion'

/**
 * Contexto de sesion de AthenIA (Semana 5).
 *
 * Sustituye a `data/usuario.js` (`USUARIO_DEMO`) como fuente de verdad del
 * usuario actual — exactamente como anticipaba el comentario de ese archivo:
 * "cuando exista autenticacion, este modulo se sustituye por el contexto de
 * sesion (...) sin tocar los componentes que ya lo consumen". `Header` y
 * `Sidebar` siguen usando `iniciales()` / `nombreDePila()` de ese archivo,
 * solo que ahora reciben el nombre real en vez de "Luis Pérez".
 */

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [sesion, setSesion] = useState(() => leerSesion())
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  const limpiarError = useCallback(() => setError(''), [])

  const _completarSesion = useCallback((datos) => {
    const nuevaSesion = { token: datos.access_token, usuario: datos.usuario }
    setSesion(nuevaSesion)
    guardarSesion(nuevaSesion)
  }, [])

  const iniciarSesion = useCallback(
    async (email, password) => {
      setCargando(true)
      setError('')
      try {
        const datos = await iniciarSesionApi({ email, password })
        _completarSesion(datos)
        return true
      } catch (err) {
        setError(err.message)
        return false
      } finally {
        setCargando(false)
      }
    },
    [_completarSesion],
  )

  const registrarse = useCallback(
    async (email, password, nombre) => {
      setCargando(true)
      setError('')
      try {
        const datos = await registrarUsuarioApi({ email, password, nombre })
        _completarSesion(datos)
        return true
      } catch (err) {
        setError(err.message)
        return false
      } finally {
        setCargando(false)
      }
    },
    [_completarSesion],
  )

  const cerrarSesion = useCallback(() => {
    setSesion(null)
    guardarSesion(null)
  }, [])

  const valor = useMemo(
    () => ({
      usuario: sesion?.usuario ?? null,
      autenticado: Boolean(sesion?.token),
      cargando,
      error,
      iniciarSesion,
      registrarse,
      cerrarSesion,
      limpiarError,
    }),
    [sesion, cargando, error, iniciarSesion, registrarse, cerrarSesion, limpiarError],
  )

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

/** Hook de acceso a la sesion. Debe usarse dentro de `<AuthProvider>` (ver `App.jsx`). */
export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) {
    throw new Error('useAuth() debe usarse dentro de <AuthProvider>.')
  }
  return contexto
}
