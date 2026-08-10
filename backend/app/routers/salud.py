"""
Rutas de meta-informacion: raiz, health check y catalogo de categorias.

Extraidas de `main.py` (SRP): antes 8 endpoints de dos areas distintas
(salud/meta y contenido/historial) vivian en el mismo archivo que el
`lifespan`, el CORS y los exception handlers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import settings
from ..dependencies import get_clasificador, get_repositorio
from ..domain.protocols import Clasificador, RepositorioContenidos
from ..schemas import SaludOutput

router = APIRouter(tags=["Meta"])


@router.get("/", summary="Informacion de la API")
def root(clasificador: Clasificador = Depends(get_clasificador)) -> dict:
    """Punto de entrada informativo. Verifica de un vistazo que el deploy vive."""
    return {
        "nombre": settings.APP_NAME,
        "version": settings.VERSION,
        "entorno": settings.ENV,
        "motor": clasificador.motor,
        "modelo": clasificador.nombre,
        "docs": "/docs",
        "endpoints": [
            "POST /contenido",
            "GET /contenidos",
            "GET /contenidos/{id}",
            "GET /contenidos/{id}/recomendaciones",
            "GET /metricas",
            "GET /analiticas",
            "GET /categorias",
            "GET /salud",
        ],
    }


@router.get(
    "/salud",
    summary="Health check para QA / uptime",
    response_model=SaludOutput,
)
def salud(
    clasificador: Clasificador = Depends(get_clasificador),
    repositorio: RepositorioContenidos = Depends(get_repositorio),
) -> SaludOutput:
    """
    Verificacion de uptime usada por QA y por el monitoreo de OCI.

    Responde 200 mientras el proceso este vivo e informa que motor de
    clasificacion esta en uso:

    - `motor: "modelo_ml_real"`      -> artefacto entrenado cargado y verificado
    - `motor: "clasificador_reglas"` -> fallback por taxonomia de palabras clave
    """
    return SaludOutput(
        estado="ok",
        version=settings.VERSION,
        entorno=settings.ENV,
        motor=clasificador.motor,
        modelo_cargado=clasificador.nombre,
        detalle_modelo=clasificador.detalle,
        es_mock=clasificador.es_mock,
        contenidos_en_historial=repositorio.total(),
    )


@router.get("/categorias", tags=["Contenido"], summary="Catalogo de categorias")
def categorias(clasificador: Clasificador = Depends(get_clasificador)) -> dict:
    """Lista de categorias que el clasificador activo puede devolver."""
    return {"categorias": clasificador.categorias()}
