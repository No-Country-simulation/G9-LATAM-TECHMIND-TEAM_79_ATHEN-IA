import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Library, AlertCircle, Sparkles, Search } from 'lucide-react'
import CourseCard from '../components/CourseCard'
import ContentDetail from '../components/ContentDetail'
import { SkeletonGrid } from '../components/Loaders'
import { useContenidos } from '../hooks/useContenidos'

/**
 * Vista "Mis Cursos" — la biblioteca completa.
 *
 * Se diferencia de "Buscar" en el proposito: aqui se **navega** todo el
 * contenido analizado, ordenado del mas reciente al mas antiguo, sin filtros
 * de por medio. Buscar existe para localizar algo concreto.
 *
 * Comparte `CourseCard` y `ContentDetail` con esa vista, asi que la tarjeta y
 * el panel de detalle se comportan igual en ambas.
 */
export default function MisCursos() {
  const { items, total, cargando, error } = useContenidos({ debounceMs: 0 })
  const [seleccionado, setSeleccionado] = useState(null)

  return (
    <div className="space-y-6">
      {/* --- Encabezado --- */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-2xl font-bold tracking-tight text-tinta-900">
            <Library size={24} className="text-brand-600" aria-hidden="true" />
            Mis Cursos
          </h1>
          <p className="mt-1 text-sm text-tinta-600">
            {cargando
              ? 'Cargando tu biblioteca…'
              : `${total} contenido${total === 1 ? '' : 's'} analizado${total === 1 ? '' : 's'}`}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Link to="/buscar" className="btn-ghost">
            <Search size={16} aria-hidden="true" />
            Buscar
          </Link>
          <Link to="/agregar" className="btn-primary">
            <Sparkles size={16} aria-hidden="true" />
            Analizar contenido
          </Link>
        </div>
      </div>

      {/* --- Error de conexion --- */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5"
        >
          <AlertCircle size={17} className="mt-0.5 shrink-0 text-rose-600" aria-hidden="true" />
          <p className="text-sm text-rose-700">{error}</p>
        </div>
      )}

      {/* --- Biblioteca --- */}
      {cargando ? (
        <SkeletonGrid cantidad={6} />
      ) : items.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((contenido) => (
            <CourseCard key={contenido.id} contenido={contenido} onVer={setSeleccionado} />
          ))}
        </div>
      ) : (
        !error && (
          <div className="card flex flex-col items-center justify-center p-12 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-lienzo text-tinta-600">
              <Library size={26} aria-hidden="true" />
            </span>
            <p className="mt-4 text-sm font-medium text-mist-200">Tu biblioteca esta vacia</p>
            <p className="mt-1 max-w-sm text-sm text-tinta-600">
              Analiza tu primer contenido tecnico y aparecera aqui, clasificado y
              con sus tecnologias detectadas.
            </p>
            <Link to="/agregar" className="btn-primary mt-6">
              <Sparkles size={16} aria-hidden="true" />
              Analizar contenido
            </Link>
          </div>
        )
      )}

      <ContentDetail
        contenido={seleccionado}
        onCerrar={() => setSeleccionado(null)}
        onAbrirOtro={(recomendado) =>
          setSeleccionado(items.find((i) => i.id === recomendado.id) ?? recomendado)
        }
      />
    </div>
  )
}
