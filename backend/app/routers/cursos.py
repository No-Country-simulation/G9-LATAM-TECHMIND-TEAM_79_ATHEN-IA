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
from ..schemas import (
    CategoriaCatalogo,
    CursoEncontrado,
    ErrorResponse,
    RespuestaBusquedaCursos,
    RespuestaCatalogoCursos,
    RespuestaCategoriasCatalogo,
)

logger = logging.getLogger("athenia.routers.cursos")

router = APIRouter(tags=["Cursos"])


# NOTA DE ORDEN: `/cursos/buscar` y `/cursos/categorias` se declaran ANTES que
# cualquier `/cursos/{algo}`. Starlette resuelve por orden de registro, asi que
# una ruta con parametro declarada antes capturaria "buscar" como si fuera un id.


@router.get(
    "/cursos",
    summary="Navegar el catalogo de cursos",
    response_model=RespuestaCatalogoCursos,
    status_code=status.HTTP_200_OK,
)
def listar_cursos(
    categoria: str | None = Query(
        default=None,
        description="Filtra por categoria exacta. Usa `GET /cursos/categorias` para el catalogo.",
        examples=["Ciencia de Datos y Analitica"],
    ),
    limite: int = Query(default=24, ge=1, le=100, description="Cursos por pagina."),
    desplazamiento: int = Query(default=0, ge=0, description="Cursos a omitir (paginacion)."),
    buscador: BuscadorCursos = Depends(get_buscador_cursos),
) -> RespuestaCatalogoCursos:
    """
    Devuelve cursos del catalogo **sin** consulta semantica.

    Existe porque el Dashboard necesita mostrar cursos reales nada mas cargar,
    antes de que el usuario escriba nada. Hasta ahora la unica via al catalogo
    era `/cursos/buscar`, que exige un texto; sin el, la interfaz caia a
    `GET /contenidos` —el historial de analisis, con 8 registros de demo— y
    parecia que el catalogo de +8.000 cursos no estuviera conectado.

    No calcula distancias ni carga el modelo de embeddings: filtra por
    metadatos, asi que responde en milisegundos. Cada curso trae
    `match_score: null`, porque sin consulta no hay afinidad que medir.
    """
    items = buscador.listar(
        categoria=categoria,
        limite=limite,
        desplazamiento=desplazamiento,
    )
    return RespuestaCatalogoCursos(
        total=len(items),
        total_indexado=buscador.total_indexado,
        categoria=categoria,
        desplazamiento=desplazamiento,
        items=[CursoEncontrado(**curso) for curso in items],
    )


@router.get(
    "/cursos/categorias",
    summary="Categorias del catalogo con su conteo",
    response_model=RespuestaCategoriasCatalogo,
    status_code=status.HTTP_200_OK,
)
def categorias_del_catalogo(
    buscador: BuscadorCursos = Depends(get_buscador_cursos),
) -> RespuestaCategoriasCatalogo:
    """
    Categorias reales del catalogo, con cuantos cursos tiene cada una.

    Distinto de `GET /categorias`, que devuelve las clases del **clasificador**
    (`clasificador_cursos.pkl`). Son dos catalogos distintos: filtrar el
    catalogo por una categoria que solo existe en el clasificador devolveria
    siempre cero resultados.
    """
    items = buscador.categorias()
    return RespuestaCategoriasCatalogo(
        total=len(items),
        items=[CategoriaCatalogo(**c) for c in items],
    )


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
