import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Dashboard from './pages/Dashboard'
import AgregarContenido from './pages/AgregarContenido'
import BuscarContenidos from './pages/BuscarContenidos'
import Categorias from './pages/Categorias'

/** Pantalla 404. */
function NoEncontrado() {
  return (
    <div className="card flex flex-col items-center justify-center p-12 text-center">
      <p className="text-4xl font-bold text-brand-400">404</p>
      <p className="mt-2 text-sm text-mist-300">Esta pagina no existe.</p>
      <Link to="/" className="btn-primary mt-6">
        Volver al inicio
      </Link>
    </div>
  )
}

/**
 * Shell de la aplicacion: Sidebar + Header fijos, contenido enrutado.
 * El estado del drawer movil vive aqui porque lo comparten Sidebar y Header.
 */
export default function App() {
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-ink-950">
        <Sidebar abierto={menuAbierto} onCerrar={() => setMenuAbierto(false)} />

        <div className="flex min-w-0 flex-1 flex-col">
          <Header onAbrirMenu={() => setMenuAbierto(true)} />

          <main className="flex-1 px-4 py-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/agregar" element={<AgregarContenido />} />
                <Route path="/buscar" element={<BuscarContenidos />} />
                <Route path="/categorias" element={<Categorias />} />
                <Route path="*" element={<NoEncontrado />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
