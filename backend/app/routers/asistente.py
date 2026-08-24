"""
Ruta del Asistente conversacional.

Sigue el mismo patron DIP que el resto de la API: depende de `AsistenteCursos`
via `get_asistente`, nunca de OpenAI ni de ChromaDB directamente. Por eso las
pruebas pueden sustituir el asistente completo con
`app.dependency_overrides[get_asistente] = ...`.

Nota sobre autenticacion: igual que `GET /cursos/buscar` y el resto de rutas
del catalogo, esta ruta NO exige sesion: solo consulta el catalogo publico de
cursos, el mismo dato que ya es publico en `/cursos/buscar`. Si el cliente
envia un JWT (por ejemplo porque el usuario ya inicio sesion en otra parte de
la app), el interceptor de axios lo adjunta igual, pero no es obligatorio.
Cuando el Asistente incorpore contenido propio de cada usuario (enlaces y
PDFs que adjunte, ver el checklist de "proximos pasos"), sera necesario
proteger esa parte con `Depends(get_usuario_actual)` para filtrar por
usuario; aqui todavia no hace falta.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from ..asistente.servicio import AsistenteCursos
from ..dependencies import get_asistente
from ..schemas import MensajeAsistenteInput, RespuestaAsistente

logger = logging.getLogger("athenia.routers.asistente")

router = APIRouter(prefix="/asistente", tags=["Asistente"])


@router.post(
    "/mensaje",
    summary="Conversar con el Asistente AthenIA sobre el catalogo de cursos",
    response_model=RespuestaAsistente,
    status_code=status.HTTP_200_OK,
)
def enviar_mensaje(
    payload: MensajeAsistenteInput,
    asistente: AsistenteCursos = Depends(get_asistente),
) -> RespuestaAsistente:
    """
    Responde una pregunta en lenguaje natural usando el catalogo de cursos
    como contexto (RAG): primero busca cursos reales por afinidad semantica,
    luego el modelo de lenguaje redacta la respuesta citando SOLO esos
    cursos. Los `cursos_relacionados` de la respuesta vienen del buscador,
    no del texto generado, para que los enlaces que muestre la interfaz sean
    siempre reales.

    Responde **200 incluso si el modelo de lenguaje no esta configurado**
    (sin `ATHENIA_OPENAI_API_KEY`): en ese caso `disponible` viaja en
    `false` y `respuesta` explica la situacion, pero `cursos_relacionados`
    sigue trayendo resultados utiles de la busqueda semantica. Igual que en
    `/cursos/buscar`, un problema de configuracion no debe tumbar la ruta.
    """
    resultado = asistente.responder(
        mensaje=payload.mensaje,
        historial=[turno.model_dump() for turno in payload.historial],
    )
    return RespuestaAsistente(**resultado)


@router.get(
    "/estado",
    summary="Diagnostico del Asistente conversacional",
    status_code=status.HTTP_200_OK,
)
def estado_del_asistente(asistente: AsistenteCursos = Depends(get_asistente)) -> dict:
    """
    Igual que `GET /cursos/estado`: permite distinguir "no hay API key
    configurada" de "el catalogo esta caido" sin leer el log del proceso a
    mano. Util para que el frontend decida si mostrar el chat activo o el
    aviso de "asistente no disponible".
    """
    return asistente.diagnostico()
