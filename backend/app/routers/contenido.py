"""
Rutas de contenido e historial.

Cada endpoint depende de `Clasificador` / `RepositorioContenidos` — los
`Protocol` de `domain.protocols` — via `Depends`, nunca de `ClasificadorML`,
`ClasificadorReglas` ni `RepositorioMemoria` directamente. Es el mismo
patron en las 5 rutas: eso es DIP aplicado de forma consistente, no un caso
aislado.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import services
from ..dependencies import get_clasificador, get_recomendador, get_repositorio
from ..domain.protocols import Clasificador, MotorRecomendaciones, RepositorioContenidos
from ..schemas import (
    AnalisisOutput,
    ContenidoAlmacenado,
    ContenidoInput,
    ErrorResponse,
    ListaContenidos,
    ListaRecomendaciones,
    MetricasOutput,
    RecomendacionItem,
)
logger = logging.getLogger("athenia.routers.contenido")

router = APIRouter(tags=["Contenido"])


@router.post(
    "/contenido",
    tags=["Contenido"],
    summary="Clasificar contenido tecnico",
    response_model=AnalisisOutput,
    status_code=status.HTTP_200_OK,
    responses={422: {"model": ErrorResponse}},
)
def analizar_contenido(
    payload: ContenidoInput,
    clasificador: Clasificador = Depends(get_clasificador),
    repositorio: RepositorioContenidos = Depends(get_repositorio),
) -> AnalisisOutput:
    """
    **Endpoint oficial del Hackathon ONE Alura + Oracle.**

    Recibe un titulo y un texto tecnico, y devuelve:

    - `categoria`             categoria principal detectada
    - `probabilidad`          confianza del modelo (0.0 - 1.0)
    - `informacion_adicional` palabras clave / tecnologias detectadas

    El analisis queda guardado en el historial y es consultable en
    `GET /contenidos/{id}`.

    La validacion de campos vacios ocurre en `ContenidoInput`, por lo que un
    payload invalido responde 422 automaticamente.
    """
    registro = services.analizar_y_guardar(
        payload.model_dump(),
        motor=clasificador,
        historial=repositorio,
    )
    return AnalisisOutput(**registro)


@router.get(
    "/contenidos",
    tags=["Historial"],
    summary="Historial de analisis",
    response_model=ListaContenidos,
)
def listar_contenidos(
    categoria: str | None = Query(
        default=None,
        description="Filtra por categoria exacta. Ej: 'Backend'.",
    ),
    buscar: str | None = Query(
        default=None,
        description="Busqueda parcial en titulo, texto, categoria y palabras clave.",
    ),
    limite: int | None = Query(
        default=None,
        ge=1,
        le=500,
        description="Maximo de items a devolver.",
    ),
    repositorio: RepositorioContenidos = Depends(get_repositorio),
) -> ListaContenidos:
    """
    Devuelve los analisis realizados, del mas reciente al mas antiguo.

    Alimenta el Dashboard y la vista "Buscar Contenidos" del frontend.
    """
    items = repositorio.listar(categoria=categoria, buscar=buscar, limite=limite)
    return ListaContenidos(
        total=len(items),
        items=[ContenidoAlmacenado(**item) for item in items],
    )


@router.get(
    "/contenidos/{contenido_id}",
    tags=["Historial"],
    summary="Detalle de un analisis",
    response_model=ContenidoAlmacenado,
    responses={404: {"model": ErrorResponse}},
)
def obtener_contenido(
    contenido_id: int,
    repositorio: RepositorioContenidos = Depends(get_repositorio),
) -> ContenidoAlmacenado:
    """Devuelve un analisis por su identificador, o 404 si no existe."""
    item = repositorio.obtener(contenido_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un contenido con id {contenido_id}.",
        )
    return ContenidoAlmacenado(**item)


@router.get(
    "/contenidos/{contenido_id}/recomendaciones",
    tags=["Recomendaciones"],
    summary="Contenido relacionado",
    response_model=ListaRecomendaciones,
    responses={404: {"model": ErrorResponse}},
)
def recomendaciones_de_contenido(
    contenido_id: int,
    limite: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximo de recomendaciones a devolver.",
    ),
    repositorio: RepositorioContenidos = Depends(get_repositorio),
    recomendador: MotorRecomendaciones = Depends(get_recomendador),
) -> ListaRecomendaciones:
    """
    Devuelve los contenidos del historial mas parecidos al indicado.

    La relevancia combina la similitud de palabras clave (indice de Jaccard,
    75% del puntaje) con la coincidencia de categoria (25%). Cada
    recomendacion incluye `palabras_compartidas`, para que la interfaz pueda
    explicar *por que* se sugirio en vez de mostrar solo un numero.

    Un contenido sin coincidencias devuelve `total: 0` con lista vacia —no es
    un error—, y un id inexistente devuelve 404.
    """
    referencia = repositorio.obtener(contenido_id)
    if referencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un contenido con id {contenido_id}.",
        )

    sugerencias = recomendador.recomendar(
        referencia,
        repositorio.listar(),
        limite=limite,
    )

    return ListaRecomendaciones(
        contenido_id=contenido_id,
        titulo=referencia.get("titulo", ""),
        estrategia=recomendador.nombre,
        total=len(sugerencias),
        items=[RecomendacionItem(**s) for s in sugerencias],
    )


@router.delete(
    "/contenidos",
    tags=["Historial"],
    summary="Vaciar el historial (utilidad para QA)",
    status_code=status.HTTP_200_OK,
)
def limpiar_contenidos(
    repositorio: RepositorioContenidos = Depends(get_repositorio),
) -> dict:
    """
    Vacia el historial en memoria.

    Pensado para que QA parta de un estado limpio entre sesiones de prueba
    manual sin reiniciar el servidor.
    """
    eliminados = repositorio.total()
    repositorio.limpiar()
    logger.info("Historial vaciado (%d items).", eliminados)
    return {"eliminados": eliminados, "mensaje": "Historial vaciado."}


@router.get(
    "/metricas",
    tags=["Historial"],
    summary="Metricas agregadas del historial",
    response_model=MetricasOutput,
)
def metricas(
    repositorio: RepositorioContenidos = Depends(get_repositorio),
) -> MetricasOutput:
    """Agregados que alimentan las tarjetas y el grafico del Dashboard."""
    return MetricasOutput(**services.calcular_metricas(repositorio.listar()))

