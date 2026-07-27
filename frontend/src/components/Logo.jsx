/**
 * Isotipo de AthenIA: casco de Atenea trazado en SVG.
 * Se dibuja inline para no depender de un asset externo y poder heredar el
 * color desde Tailwind (`currentColor`).
 */
export default function Logo({ className = 'h-8 w-8' }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Logotipo de AthenIA"
    >
      {/* Cresta del casco */}
      <path
        d="M14 14c0-5 4-9 10-9s10 4 10 9v3c3 1 5 3 5 6 0 4-4 6-8 6"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* Perfil / mascara */}
      <path
        d="M14 14v14c0 6 4 11 10 14 6-3 10-8 10-14V14"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      {/* Visor */}
      <path d="M19 22h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      {/* Nasal */}
      <path d="M24 22v10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}
