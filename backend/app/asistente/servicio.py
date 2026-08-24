"""
Caso de uso del Asistente conversacional de AthenIA.
=====================================================

Orquesta busqueda + generacion siguiendo el patron RAG (Retrieval-Augmented
Generation), que es lo que evita que el modelo de lenguaje invente cursos:

  1. `BuscadorCursos.buscar()` recupera cursos REALES del catalogo indexado
     (el mismo motor que usa `GET /cursos/buscar`).
  2. Esos cursos se pasan como contexto al `ModeloLenguaje`, que solo puede
     citarlos a ellos (ver el `SYSTEM_PROMPT` en `motor_openai.py`).
  3. La lista de `cursos_relacionados` que ve el frontend sale DIRECTO del
     paso 1, no del texto que redacto el modelo: aunque el modelo se
     equivocara en el texto, los enlaces que se muestran en la interfaz
     siguen siendo datos reales del catalogo.

Depende de `BuscadorCursos` (que a su vez depende del `Protocol`
`AlmacenVectorial`) y del `Protocol` `ModeloLenguaje`, nunca de ChromaDB ni
de OpenAI directamente: las pruebas inyectan dobles de ambos y corren sin
red, sin base vectorial y sin gastar tokens.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from ..busqueda.servicio import BuscadorCursos
from ..domain.protocols import ModeloLenguaje

logger = logging.getLogger("athenia.asistente.servicio")

#: Cuantos cursos como maximo se pasan de contexto al modelo. Mas que esto
#: infla el prompt (mas costo, mas latencia) sin mejorar la respuesta: la
#: busqueda semantica ya los trae ordenados por afinidad, y el umbral de
#: relevancia (`UMBRAL_RELEVANCIA` en `busqueda.servicio`) ya descarta lo
#: irrelevante antes de llegar aqui.
MAXIMO_CURSOS_DE_CONTEXTO = 6

#: Se piden de mas al buscador (antes del filtro de calidad de abajo) para
#: que, si algunos candidatos son filas corruptas del catalogo, todavia
#: queden MAXIMO_CURSOS_DE_CONTEXTO cursos validos en vez de menos.
_MULTIPLICADOR_CANDIDATOS = 3

#: Caracteres que SI se esperan en un titulo de curso real (letras con o sin
#: acento, digitos, espacios y puntuacion comun). Todo lo demas cuenta como
#: "caracter raro" para `_titulo_parece_valido`.
_CARACTERES_RAROS = re.compile(r"[^A-Za-zÀ-ÿ0-9\s\-:,.()&'!¿?/+#%]")


def _titulo_parece_valido(titulo: Optional[str]) -> bool:
    """
    Filtro heuristico de calidad de datos, NO de relevancia.

    El catalogo de +8.000 cursos tiene algunas filas corruptas (titulos como
    '"Bob"', 'briefs', o texto con la codificacion rota) que la busqueda
    semantica a veces trae como candidatos validos. No es una limpieza
    definitiva del dataset —eso vive en el pipeline de datos, no aqui— pero
    evita que el Asistente las cite o las muestre en la demo.
    """
    titulo = (titulo or "").strip().strip("\"'").strip()
    if len(titulo) < 8:
        return False
    proporcion_rara = len(_CARACTERES_RAROS.findall(titulo)) / len(titulo)
    return proporcion_rara <= 0.15


class AsistenteCursos:
    """
    Asistente conversacional sobre el catalogo de cursos.

    Es sin estado entre peticiones: no guarda historial en el servidor. El
    cliente reenvia el historial de la conversacion en cada mensaje
    (`payload.historial` de `MensajeAsistenteInput`), igual que cualquier
    integracion simple con un chat de OpenAI. Persistir conversaciones en un
    repositorio queda fuera de esta primera fase — ver el checklist de
    "proximos pasos" del asistente.
    """

    def __init__(self, buscador: BuscadorCursos, modelo: ModeloLenguaje):
        self._buscador = buscador
        self._modelo = modelo

    @property
    def disponible(self) -> bool:
        """
        True solo si el modelo de lenguaje esta configurado. La busqueda
        semantica puede seguir funcionando (y de hecho se usa) aunque el
        modelo no lo este: `responder()` degrada a devolver solo los cursos
        encontrados, sin redaccion — nunca lanza ni responde vacio.
        """
        return self._modelo.disponible

    def diagnostico(self) -> dict:
        """Para `GET /asistente/estado`, mismo espiritu que `GET /cursos/estado`."""
        return {
            "modelo": self._modelo.nombre,
            "disponible": self._modelo.disponible,
            "catalogo_disponible": self._buscador.disponible,
            "total_indexado": self._buscador.total_indexado,
        }

    def responder(
        self,
        mensaje: str,
        historial: Optional[List[dict]] = None,
    ) -> dict:
        """
        Devuelve un dict compatible con `schemas.RespuestaAsistente`:
        `{"respuesta": str, "cursos_relacionados": [...], "motor": str,
        "disponible": bool}`.

        Nunca lanza: un mensaje vacio, un catalogo caido o un modelo sin
        configurar producen una respuesta valida y explicativa, no un error.
        Es el mismo contrato de "no debe lanzar" de `Clasificador.clasificar`.
        """
        mensaje = (mensaje or "").strip()
        if not mensaje:
            return {
                "respuesta": "Escribe una pregunta para que pueda ayudarte.",
                "cursos_relacionados": [],
                "motor": self._modelo.nombre,
                "disponible": self._modelo.disponible,
            }

        # Si el catalogo no esta disponible, `buscar()` ya devuelve `[]` sin
        # lanzar (ver `BuscadorCursos.buscar`): el asistente sigue
        # respondiendo, solo que sin cursos que citar.
        #
        # Se piden mas de MAXIMO_CURSOS_DE_CONTEXTO y se filtran las filas de
        # baja calidad ANTES de recortar: si se recortara primero, una fila
        # corrupta entre los primeros resultados dejaria menos de
        # MAXIMO_CURSOS_DE_CONTEXTO cursos utiles en vez de reponerla.
        bruto = self._buscador.buscar(
            mensaje, limite=MAXIMO_CURSOS_DE_CONTEXTO * _MULTIPLICADOR_CANDIDATOS
        )
        candidatos = [
            curso
            for curso in bruto
            if _titulo_parece_valido(curso.get("title") or curso.get("titulo"))
        ][:MAXIMO_CURSOS_DE_CONTEXTO]

        texto = self._modelo.responder(
            mensaje=mensaje,
            contexto=candidatos,
            historial=historial,
        )

        return {
            "respuesta": texto,
            "cursos_relacionados": candidatos,
            "motor": self._modelo.nombre,
            "disponible": self._modelo.disponible,
        }
