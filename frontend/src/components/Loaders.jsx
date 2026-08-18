import { Loader2 } from 'lucide-react'

/**
 * Estados de carga reutilizables.
 *
 * Los esqueletos replican la forma del contenido final para evitar saltos de
 * layout cuando llegan los datos.
 */

/** Spinner simple con etiqueta opcional. */
export function Spinner({ tamano = 18, etiqueta = '', className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2 text-tinta-500 ${className}`} role="status">
      <Loader2 size={tamano} className="animate-spin text-brand-600" />
      {etiqueta && <span className="text-sm">{etiqueta}</span>}
      <span className="sr-only">Cargando</span>
    </span>
  )
}

/** Bloque gris con pulso, base de todos los esqueletos. */
export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-lg bg-lienzo ${className}`} aria-hidden="true" />
}

/** Esqueleto de una tarjeta de metrica del Dashboard. */
export function SkeletonStat() {
  return (
    <div className="card p-5">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-3 h-8 w-16" />
      <Skeleton className="mt-2 h-3 w-20" />
    </div>
  )
}

/** Esqueleto de una tarjeta de contenido del catalogo. */
export function SkeletonCard() {
  return (
    <div className="card p-5">
      <div className="flex items-start gap-3">
        <Skeleton className="h-10 w-10 shrink-0 rounded-xl" />
        <div className="flex-1">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="mt-2 h-3 w-1/3" />
        </div>
      </div>
      <Skeleton className="mt-4 h-3 w-full" />
      <Skeleton className="mt-2 h-3 w-5/6" />
      <div className="mt-4 flex gap-1.5">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-14" />
        <Skeleton className="h-5 w-20" />
      </div>
    </div>
  )
}

/** Rejilla de esqueletos de tarjetas. */
export function SkeletonGrid({ cantidad = 6 }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: cantidad }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}
