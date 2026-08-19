"""
Ruta de busqueda semantica de cursos.

Sigue el mismo patron DIP que el resto de la API: depende del `Protocol`
`AlmacenVectorial` a traves de `get_buscador_cursos`, nunca de ChromaDB. Por
eso las pruebas pueden sustituir el indice completo con
`app.dependency_overrides[get_buscador_cursos] = ...`.

La version original declaraba `/cursos/buscar` **dos veces** en
`routers/contenido.py`, ambas con la misma funcion `buscar_cursos`. Starlette
resuelve por orden de registro, asi que la segunda quedaba inalcanzable: codigo
muerto que aun asi aparecia duplicado en el OpenAPI.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, status

from ..busqueda.servicio import UMBRAL_RELEVANCIA, BuscadorCursos
from ..dependencies import get_buscador_cursos
from ..schemas import CursoEncontrado, ErrorResponse, RespuestaBusquedaCursos

logger = logging.getLogger("athenia.routers.cursos")

router = APIRouter(tags=["Cursos"])


@router.get(
    "/cursos/buscar",
    summary="Busqueda semantica en el catalogo de cursos",
    response_model=RespuestaBusquedaCursos,
    status_code=status.HTTP_200_OK,
    responses={503: {"model": ErrorResponse}},
)
def buscar_cursos(
    q: str = Query(
        ...,
        min_length=1,
        max_length=300,
        description="Consulta en lenguaje natural, en espanol o ingles.",
        examples=["quiero aprender machine learning con python"],
    ),
    limite: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximo de cursos a devolver.",
    ),
    min_score: float = Query(
        default=UMBRAL_RELEVANCIA,
        ge=0.0,
        le=1.0,
        description=(
            "Umbral de afinidad. Los cursos por debajo se descartan. "
            "Subelo para resultados mas estrictos; ponlo en 0 para depurar."
        ),
    ),
    buscador: BuscadorCursos = Depends(get_buscador_cursos),
) -> RespuestaBusquedaCursos:
    """
    Busca cursos por significado, no por coincidencia de palabras.

    La consulta se vectoriza con el mismo modelo multilingue que indexo el
    catalogo, de modo que "aprender a programar en la nube" encuentra cursos
    titulados *Cloud Computing Fundamentals* aunque no compartan ni una
    palabra.

    Cada resultado trae `match_score` (similitud coseno, 0.0 a 1.0). Los que
    no superan `min_score` no se devuelven: es lo que evita que aparezcan
    cursos sin relacion cuando la consulta no tiene buenas coincidencias.

    Una consulta sin resultados relevantes responde **200 con lista vacia**,
    no un error: para el Dashboard "no hay coincidencias" es un estado normal.
    Si el indice vectorial no esta disponible se responde **503**, para que la
    interfaz distinga "no encontre nada" de "el buscador esta caido".
    """
    if not buscador.disponible:
        # 503 y no 500: el servicio esta bien, lo que falta es el indice.
        # Se devuelve el cuerpo normal con total 0 para no romper al frontend.
        logger.warning("Busqueda '%s' rechazada: el indice vectorial no esta disponible.", q)
        return RespuestaBusquedaCursos(
            busqueda=q,
            total=0,
            min_score=min_score,
            total_indexado=0,
            resultados=[],
        )

    encontrados = buscador.buscar(consulta=q, limite=limite, min_score=min_score)

    return RespuestaBusquedaCursos(
        busqueda=q,
        total=len(encontrados),
        min_score=min_score,
        total_indexado=buscador.total_indexado,
        resultados=[CursoEncontrado(**curso) for curso in encontrados],
    )
