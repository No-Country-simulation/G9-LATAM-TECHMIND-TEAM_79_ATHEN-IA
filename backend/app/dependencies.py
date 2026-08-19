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
from .busqueda.almacen import AlmacenChroma
from .busqueda.servicio import BuscadorCursos
from .domain.protocols import Clasificador, MotorRecomendaciones, RepositorioContenidos
from .recomendador import RecomendadorPorKeywords

# Instancia unica del motor de recomendaciones. Es sin estado (solo calcula
# sobre los candidatos que recibe), asi que compartirla entre peticiones es
# seguro y evita reconstruirla en cada request.
_recomendador = RecomendadorPorKeywords()

# Instancia unica del buscador de cursos. `AlmacenChroma` abre la base
# vectorial de forma perezosa —la primera busqueda paga la carga del modelo,
# las siguientes no—, asi que construirlo aqui no ralentiza el arranque.
#
# La version original abria un `PersistentClient` y reinstanciaba el
# `SentenceTransformer` en CADA peticion: cientos de milisegundos por busqueda
# y varias copias del modelo en memoria bajo carga concurrente.
_buscador_cursos = BuscadorCursos(AlmacenChroma())


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


def get_recomendador() -> MotorRecomendaciones:
    """
    Devuelve el motor de recomendaciones activo.

    Punto unico de sustitucion: cambiar a un motor de embeddings en la
    Semana 5 es reemplazar la instancia de arriba, sin tocar la ruta
    `/contenidos/{id}/recomendaciones` ni su firma — que depende del
    `Protocol` `MotorRecomendaciones`, no de `RecomendadorPorKeywords`.
    """
    return _recomendador


def get_buscador_cursos() -> BuscadorCursos:
    """
    Devuelve el buscador semantico de cursos.

    Punto unico de sustitucion del indice vectorial: migrar de ChromaDB a
    Oracle AI Vector Search es cambiar el almacen que se inyecta arriba, sin
    tocar la ruta `/cursos/buscar` ni `busqueda.servicio`.

    En pruebas se sustituye con
    `app.dependency_overrides[get_buscador_cursos] = lambda: doble`, lo que
    permite ejercitar la ruta completa sin la base vectorial de 26 MB ni el
    modelo de embeddings.
    """
    return _buscador_cursos
