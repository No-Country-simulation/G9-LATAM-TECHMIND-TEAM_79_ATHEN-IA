import logoAthenia from '../assets/logo-athenia.png'

/**
 * Isotipo de AthenIA: el casco de Atenea.
 * ----------------------------------------
 * Renderiza el asset oficial (`src/assets/logo-athenia.png`). Vite le calcula
 * el hash y lo copia a `dist/assets/` en el build, asi que la ruta se importa
 * en vez de escribirse a mano: una ruta literal no sobreviviria al hasheado.
 *
 * Notas sobre el asset, porque condicionan como se usa aqui:
 *
 *   - Mide 78x88 px y NO es cuadrado. De ahi `object-contain`: con `h-8 w-8`
 *     —que si es cuadrado— la imagen se deformaria un 12% sin el.
 *   - Es 100% opaco: el fondo azul oscuro (#111227) viene incrustado, no hay
 *     canal alfa util. Sobre el sidebar oscuro pasa desapercibido, pero sobre
 *     fondo claro se ve el recuadro; `rounded-lg` hace que lea como insignia
 *     deliberada en lugar de como un rectangulo suelto.
 *   - A 78x88 no da resolucion para los 96 px del login en pantallas retina.
 *     Un PNG mas grande (>=256 px) o una version con fondo transparente
 *     resolverian ambas cosas sin tocar este componente.
 *
 * La firma se mantiene igual que la del SVG anterior (`className`), para que
 * Sidebar y Login sigan controlando el tamano sin cambios.
 */
export default function Logo({ className = 'h-8 w-8' }) {
  return (
    <img
      src={logoAthenia}
      alt="Logotipo de AthenIA"
      width={78}
      height={88}
      // `width`/`height` reservan el espacio antes de que cargue la imagen y
      // evitan el salto de maquetado (CLS); las clases mandan sobre el tamano.
      className={`${className} shrink-0 select-none rounded-lg object-contain`}
      draggable="false"
    />
  )
}
