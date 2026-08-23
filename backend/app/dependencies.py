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

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import auth_service, services
from .busqueda.almacen import AlmacenChroma
from .busqueda.servicio import BuscadorCursos
from .config import settings
from .domain.protocols import (
    Clasificador,
    MotorRecomendaciones,
    RepositorioContenidos,
    RepositorioUsuarios,
)
from .domain.seguridad import decodificar_token
from .recomendador import RecomendadorPorKeywords
from .repositories.usuarios_sql import RepositorioUsuariosSQL

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

# Instancia unica del repositorio de usuarios. A diferencia del clasificador,
# NO se reconstruye en cada peticion: abrir un engine de SQLAlchemy por
# request agotaria el pool de conexiones bajo carga. `settings.DB_URL` decide
# si esto es un archivo SQLite (desarrollo) o Postgres (`athenia-db` en
# `docker-compose.yml`, produccion) — ver `repositories/usuarios_sql.py`.
_repositorio_usuarios = RepositorioUsuariosSQL(settings.DB_URL)

# `auto_error=False`: se prefiere devolver un 401 con el formato uniforme de
# `ErrorResponse` (via `HTTPException` propia) antes que el 403 generico que
# FastAPI arma cuando falta el header `Authorization`.
_esquema_bearer = HTTPBearer(auto_error=False)


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


def get_repositorio_usuarios() -> RepositorioUsuarios:
    """
    Devuelve el repositorio de usuarios activo.

    Las pruebas de auth sustituyen esta dependencia con
    `app.dependency_overrides[get_repositorio_usuarios] = lambda: doble`,
    apuntando a un `RepositorioUsuariosSQL("sqlite:///:memory:")` propio por
    sesion de pruebas — nunca tocan el archivo de desarrollo ni Postgres.
    """
    return _repositorio_usuarios


def get_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
    repositorio: RepositorioUsuarios = Depends(get_repositorio_usuarios),
) -> dict:
    """
    Resuelve el usuario autenticado a partir del header `Authorization: Bearer <token>`.

    Unifica en un solo 401 los tres motivos por los que puede fallar (sin
    header, token invalido/expirado, o usuario borrado tras emitirse el
    token): al cliente le basta con saber que debe volver a iniciar sesion,
    no por cual de los tres paso.
    """
    if credenciales is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticacion. Envia el token en 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decodificar_token(credenciales.credentials)
    usuario = auth_service.obtener_usuario_desde_payload(repositorio, payload)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesion invalida o expirada. Inicia sesion de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def requiere_rol(*roles_permitidos: str):
    """
    Fabrica de dependencias para proteger rutas por rol (RBAC).

    Uso:
        @router.get("/auth/usuarios")
        def listar(usuario: dict = Depends(requiere_rol("admin"))): ...

    Se implementa como una fabrica (funcion que devuelve una dependencia) y no
    como una dependencia fija, porque distintas rutas necesitan distintos
    roles — `Depends(requiere_rol("admin"))` en una,
    `Depends(requiere_rol("admin", "estudiante"))` en otra — sin duplicar la
    logica de comparacion en cada router.
    """

    def _verificar(usuario: dict = Depends(get_usuario_actual)) -> dict:
        if usuario["rol"] not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este recurso.",
            )
        return usuario

    return _verificar
