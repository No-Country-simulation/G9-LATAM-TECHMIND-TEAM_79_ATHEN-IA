"""
Motor de lenguaje natural del Asistente AthenIA, respaldado por OpenAI.
=========================================================================

Sigue el mismo patron de import perezoso que `busqueda/almacen.py` con
`sentence-transformers`: el paquete `openai` (y la API key) son OPCIONALES
para que el arranque de la API nunca dependa de ellos. Sin la dependencia
instalada o sin `ATHENIA_OPENAI_API_KEY` configurada, `disponible` queda en
False y `asistente.servicio` responde con un mensaje explicativo en vez de
un 500 — el mismo contrato de "nunca lanzar" que ya cumplen `Clasificador`
y `AlmacenVectorial`.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ..config import settings

logger = logging.getLogger("athenia.asistente.motor_openai")

#: Instrucciones que anclan al modelo al catalogo real. La restriccion clave
#: es "solo cursos de la lista": sin ella, un LLM generico completa con
#: gusto titulos, plataformas y enlaces plausibles pero inexistentes en
#: cuanto el contexto no trae una coincidencia perfecta.
SYSTEM_PROMPT = (
    "Eres el Asistente de AthenIA, una plataforma de cursos tecnicos. "
    "Respondes en espanol, de forma breve, concreta y amigable. "
    "SOLO puedes mencionar, recomendar o citar cursos que aparezcan en la "
    "lista de 'Cursos disponibles' que te llega en el mensaje: son los "
    "unicos verificados contra el catalogo real. Nunca inventes titulos, "
    "plataformas, enlaces ni cifras que no esten en esa lista. "
    "Si la lista viene vacia o ninguno de sus cursos responde a la "
    "pregunta, dilo explicitamente (por ejemplo: 'no tengo un curso asi en "
    "el catalogo ahora mismo') en vez de sugerir uno inventado. "
    "Cuando cites un curso, usa su titulo exacto tal como aparece en la "
    "lista, para que la interfaz pueda enlazarlo correctamente."
)


class ModeloLenguajeOpenAI:
    """Implementacion de `domain.protocols.ModeloLenguaje` sobre OpenAI."""

    nombre = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        modelo: Optional[str] = None,
        max_tokens: Optional[int] = None,
        base_url: Optional[str] = None,
    ):
        # Los parametros explicitos existen para que las pruebas construyan
        # una instancia sin depender de variables de entorno; en produccion
        # se leen de `settings`, igual que el resto de la configuracion.
        self._api_key = settings.OPENAI_API_KEY if api_key is None else api_key
        self._modelo = modelo or settings.OPENAI_MODEL
        self._max_tokens = settings.OPENAI_MAX_TOKENS if max_tokens is None else max_tokens
        self._cliente = None
        self._intentado = False
        self.ultimo_error: Optional[str] = None
        self._base_url = settings.OPENAI_BASE_URL if base_url is None else base_url
    @property
    def disponible(self) -> bool:
        """
        True solo si hay API key configurada Y el paquete `openai` se pudo
        importar e inicializar. No abre conexion de red: eso se paga en la
        primera llamada real a `responder()`, igual que `AlmacenChroma`
        retrasa la carga del modelo de embeddings hasta la primera consulta.
        """
        if not self._api_key:
            return False
        return self._cargar_cliente() is not None

    def _cargar_cliente(self):
        """
        Importa y construye el cliente de OpenAI de forma perezosa.

        Memoriza el intento (exito o fallo) para no reintentar el import ni
        reconstruir el cliente en cada peticion — el mismo motivo por el que
        `AlmacenChroma` recuerda si ya intento abrir el indice.
        """
        if self._cliente is not None or self._intentado:
            return self._cliente

        self._intentado = True
        try:
            from openai import OpenAI  # import perezoso: dependencia opcional
        except ImportError:
            logger.warning(
                "El paquete 'openai' no esta instalado: el asistente "
                "conversacional queda desactivado. Instalar con "
                "`pip install openai` (ver backend/requirements.txt) para "
                "habilitarlo."
            )
            self.ultimo_error = "El paquete 'openai' no esta instalado."
            return None

        try:
            self._cliente = OpenAI(api_key=self._api_key, base_url=self._base_url or None)
        except Exception as error:  # pragma: no cover - depende de la libreria
            logger.error("No se pudo inicializar el cliente de OpenAI: %s", error)
            self.ultimo_error = str(error)
            self._cliente = None

        return self._cliente

    def responder(
        self,
        mensaje: str,
        contexto: List[dict],
        historial: Optional[List[dict]] = None,
    ) -> str:
        cliente = self._cargar_cliente()
        if cliente is None:
            return (
                "El asistente conversacional todavia no esta configurado "
                "(falta la API key de OpenAI o el paquete no esta "
                "instalado). Mientras tanto puedes usar la busqueda y las "
                "recomendaciones del catalogo."
            )

        mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turno in historial or []:
            rol = "assistant" if turno.get("rol") == "asistente" else "user"
            mensajes.append({"role": rol, "content": turno.get("texto", "")})

        mensajes.append(
            {
                "role": "user",
                "content": f"{_formatear_contexto(contexto)}\n\nPregunta: {mensaje}",
            }
        )

        try:
            respuesta = cliente.chat.completions.create(
                model=self._modelo,
                messages=mensajes,
                max_tokens=self._max_tokens,
                temperature=0.3,
            )
            return respuesta.choices[0].message.content.strip()
        except Exception as error:
            # Nunca se propaga: una cuota agotada, una key invalida o un
            # corte de red no deben tumbar `/asistente/mensaje` con un 500.
            logger.error("Fallo al consultar OpenAI: %s", error)
            self.ultimo_error = str(error)
            return (
                "No pude generar una respuesta en este momento (hubo un "
                "problema al consultar el modelo). Intenta de nuevo en unos "
                "segundos."
            )


def _formatear_contexto(contexto: List[dict]) -> str:
    """
    Convierte los cursos recuperados en el bloque de texto que ve el modelo.

    Se arma aqui y no en `asistente/servicio.py` porque el formato exacto
    (que campos, en que orden, en prosa o en JSON) es un detalle de como
    ESTE proveedor entiende mejor el contexto — otro `ModeloLenguaje` podria
    preferir un formato distinto sin que el servicio cambie.
    """
    if not contexto:
        return "Cursos disponibles: (ninguno encontrado para esta pregunta)."

    lineas = ["Cursos disponibles (usa SOLO estos, con su titulo exacto):"]
    for curso in contexto:
        titulo = curso.get("title") or curso.get("titulo") or "Sin titulo"
        categoria = curso.get("category") or curso.get("categoria") or ""
        descripcion = curso.get("description") or curso.get("descripcion") or ""
        url = curso.get("url") or ""
        lineas.append(f"- {titulo} | {categoria} | {descripcion} | {url}")
    return "\n".join(lineas)
