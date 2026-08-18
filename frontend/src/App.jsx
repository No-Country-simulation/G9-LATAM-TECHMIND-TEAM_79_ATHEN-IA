import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, Outlet } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import MisCursos from './pages/MisCursos'
import AgregarContenido from './pages/AgregarContenido'
import BuscarContenidos from './pages/BuscarContenidos'
import Categorias from './pages/Categorias'
import Recomendaciones from './pages/Recomendaciones'
import AsistenteIA from './pages/AsistenteIA'
import Configuracion from './pages/Configuracion'

/** Pantalla 404. */
function NoEncontrado() {
  return (
    <div className="card flex flex-col items-center justify-center p-12 text-center">
      <p className="text-4xl font-bold text-brand-600">404</p>
      <p className="mt-2 text-sm text-tinta-700">Esta pagina no existe.</p>
      <Link to="/" className="btn-primary mt-6">
        Volver al inicio
      </Link>
    </div>
  )
}

/**
 * Shell de la aplicacion: Sidebar oscuro + Header claro, contenido enrutado.
 *
 * El estado del drawer movil vive aqui porque lo comparten Sidebar y Header.
 * `Outlet` renderiza la ruta hija, de modo que `/login` pueda quedar FUERA de
 * este shell: esa pantalla ocupa el viewport completo y no lleva navegacion.
 */
function LayoutPrincipal() {
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <div className="flex min-h-screen bg-lienzo">
      <Sidebar abierto={menuAbierto} onCerrar={() => setMenuAbierto(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header onAbrirMenu={() => setMenuAbierto(true)} />

        <main className="flex-1 px-4 py-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Fuera del shell: pantalla completa, sin sidebar ni header. */}
        <Route path="/login" element={<Login />} />

        <Route element={<LayoutPrincipal />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/mis-cursos" element={<MisCursos />} />
          <Route path="/agregar" element={<AgregarContenido />} />
          <Route path="/buscar" element={<BuscarContenidos />} />
          <Route path="/categorias" element={<Categorias />} />
          <Route path="/recomendaciones" element={<Recomendaciones />} />
          <Route path="/asistente" element={<AsistenteIA />} />
          <Route path="/configuracion" element={<Configuracion />} />
          <Route path="*" element={<NoEncontrado />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
