"""
Rutas de analiticas del dashboard (Semana 4).

Router aparte de `contenido.py` por SRP: agrupa la lectura agregada del
historial, que cambia por razones distintas (nuevas dimensiones de analisis)
a las del CRUD de contenidos.

Relacion con `GET /metricas`
-----------------------------
`/metricas` (en `routers/contenido.py`) sigue existiendo sin cambios: devuelve
el resumen basico y hay clientes y pruebas que dependen de su contrato.
`/analiticas` es un **superset**: los mismos totales mas distribucion de
confianza, distribucion por origen, actividad temporal y el motor activo.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import services
from ..dependencies import get_clasificador, get_repositorio
from ..domain.protocols import Clasificador, RepositorioContenidos
from ..schemas import AnaliticasOutput

router = APIRouter(tags=["Analiticas"])


@router.get(
    "/analiticas",
    summary="Panel completo de analiticas del dashboard",
    response_model=AnaliticasOutput,
)
def analiticas(
    repositorio: RepositorioContenidos = Depends(get_repositorio),
    clasificador: Clasificador = Depends(get_clasificador),
) -> AnaliticasOutput:
    """
    Agregados del historial para el Dashboard de analiticas.

    Incluye:

    - **Totales**: contenidos, categorias distintas, palabras clave unicas y
      confianza promedio.
    - **Distribucion por categoria**: que areas domina la biblioteca.
    - **Distribucion de confianza**: cuanto contenido clasifico el modelo con
      certeza Alta (>=75%), Media (50-74%) o Baja (<50%). Es la senal mas util
      para decidir si conviene reentrenar.
    - **Distribucion por origen**: de donde viene el contenido catalogado.
    - **Top 10 palabras clave**: las tecnologias mas frecuentes.
    - **Actividad reciente**: analisis por dia, en orden cronologico.
    - **Motor activo**: que engine produjo estas clasificaciones.

    Con el historial vacio devuelve todos los contadores en cero y las listas
    vacias — nunca falla.
    """
    return AnaliticasOutput(
        **services.calcular_analiticas(repositorio.listar(), clasificador)
    )
