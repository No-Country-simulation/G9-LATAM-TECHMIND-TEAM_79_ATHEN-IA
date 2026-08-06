"""
Proveedores de dependencias (Dependency Inversion Principle).
================================================================

Este modulo es la pieza que invierte la dependencia entre las rutas HTTP y
las implementaciones concretas. Sin el:

    from . import services
    def analizar_contenido(payload: ContenidoInput):
        resultado = services.clasificador.clasificar(...)   # <- acopla la ruta
                                                              #    al modulo services
                                                              #    y a su global mutable

Con el:

    def analizar_contenido(
        payload: ContenidoInput,
        clasificador: Clasificador = Depends(get_clasificador),  # <- la ruta pide
    ):                                                            #    una ABSTRACCION
        resultado = clasificador.clasificar(...)

La firma de la ruta ahora dice `Clasificador` (el `Protocol` de
`domain.protocols`), no `ClasificadorML` ni `ClasificadorReglas`. FastAPI
resuelve `Depends(get_clasificador)` en cada peticion, asi que:

  - Las rutas nunca importan `ml.modelo`, `ml.reglas` ni `repositories.memoria`.
  - Las pruebas pueden sustituir `get_clasificador` con
    `app.dependency_overrides[get_clasificador] = lambda: doble_de_prueba`
    sin tocar el modulo `services` ni las rutas.
  - `services.py` sigue siendo la unica raiz de composicion: este modulo solo
    LEE su estado activo en cada llamada, nunca lo decide.
"""

from __future__ import annotations

from . import services
from .domain.protocols import Clasificador, RepositorioContenidos


def get_clasificador() -> Clasificador:
    """
    Devuelve el motor de clasificacion activo.

    Se re-lee en cada peticion (FastAPI no cachea `Depends` entre requests),
    por lo que un `services.recargar_clasificador()` en caliente —tras
    integrar un `.pkl` nuevo— se refleja de inmediato en el siguiente
    `POST /contenido`, sin reiniciar el servidor.
    """
    return services.clasificador


def get_repositorio() -> RepositorioContenidos:
    """Devuelve el repositorio de historial activo."""
    return services.repositorio
