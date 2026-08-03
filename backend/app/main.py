"""
AthenIA - Rutas HTTP y middleware.
==================================

Este modulo es deliberadamente delgado: valida, delega en `services` y
serializa. Toda la logica de negocio vive en la capa de servicios.

Endpoints
---------
    GET    /                  Informacion de la API.
    GET    /salud             Health check para QA y monitoreo de OCI.
    GET    /categorias        Catalogo de categorias soportadas.
    POST   /contenido         [CONTRATO HACKATHON] Clasifica contenido tecnico.
    GET    /contenidos        Historial de analisis, con filtros.
    GET    /contenidos/{id}   Detalle de un analisis.
    GET    /metricas          Agregados para el Dashboard.
    DELETE /contenidos        Vacia el historial (utilidad para QA).

Ejecutar en local:
    uvicorn app.main:app --reload --port 8000    # desde backend/
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import services
from .config import settings
from .schemas import (
    AnalisisOutput,
    ContenidoAlmacenado,
    ContenidoInput,
    ErrorResponse,
    ListaContenidos,
    MetricasOutput,
    SaludOutput,
)

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("athenia")


# ---------------------------------------------------------------------------
# Ciclo de vida
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranque: reporta el clasificador activo y precarga el historial demo."""
    logger.info("Iniciando %s v%s (%s)", settings.APP_NAME, settings.VERSION, settings.ENV)
    logger.info(
        "Motor de clasificacion: %s | artefacto: %s | detalle: %s",
        services.clasificador.motor,
        services.clasificador.nombre,
        services.clasificador.detalle,
    )

    sembrados = services.sembrar_demo()
    if sembrados:
        logger.info("Historial precargado con %d contenidos de demo.", sembrados)

    yield

    logger.info("Deteniendo %s", settings.APP_NAME)


# ---------------------------------------------------------------------------
# Aplicacion
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_habilitados else None,
    redoc_url="/redoc" if settings.docs_habilitados else None,
    responses={422: {"model": ErrorResponse, "description": "Error de validacion"}},
)

# CORS: en desarrollo se abre a "*" para que cualquier puerto de Vite conecte.
# `allow_credentials` debe quedar en False cuando el origen es "*".
permite_todos = "*" in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=not permite_todos,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def medir_tiempo(request: Request, call_next):
    """Anade `X-Process-Time` a cada respuesta. Util para QA y para OCI APM."""
    inicio = time.perf_counter()
    respuesta = await call_next(request)
    duracion_ms = (time.perf_counter() - inicio) * 1000
    respuesta.headers["X-Process-Time"] = f"{duracion_ms:.2f}ms"
    return respuesta


# ---------------------------------------------------------------------------
# Manejo uniforme de errores
# ---------------------------------------------------------------------------


def _errores_serializables(errores: list[dict]) -> list[dict]:
    """
    Deja los errores de Pydantic en JSON puro.

    Cuando un `field_validator` propio falla, Pydantic guarda la excepcion
    original en `ctx["error"]`; ese objeto no es serializable y rompe la
    respuesta. Se convierte a texto y se descarta `url`, que solo apunta a la
    documentacion de Pydantic y no aporta nada al frontend.
    """
    limpios = []
    for error in errores:
        item = {k: v for k, v in error.items() if k not in {"ctx", "url"}}
        if ctx := error.get("ctx"):
            item["ctx"] = {clave: str(valor) for clave, valor in ctx.items()}
        limpios.append(item)
    return limpios


@app.exception_handler(RequestValidationError)
async def error_de_validacion(request: Request, exc: RequestValidationError):
    """
    422 con formato `ErrorResponse`.

    `detail` conserva la estructura nativa de FastAPI (lista con `loc`, `msg`,
    `type`) para no romper clientes ni la prueba CP-26; `error` y `mensaje`
    la envuelven con texto que el frontend puede mostrar tal cual.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            ErrorResponse(
                error="validacion",
                mensaje=(
                    "Los datos enviados no son validos. Revisa que 'titulo' y "
                    "'texto' esten presentes y no vacios."
                ),
                detail=_errores_serializables(exc.errors()),
            )
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def error_http(request: Request, exc: StarletteHTTPException):
    """Normaliza 404, 405 y demas errores HTTP al formato `ErrorResponse`."""
    mensajes = {
        404: "El recurso solicitado no existe.",
        405: "El metodo HTTP no esta permitido para esta ruta.",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ErrorResponse(
                error=f"http_{exc.status_code}",
                mensaje=mensajes.get(exc.status_code, "No se pudo procesar la peticion."),
                detail=exc.detail if isinstance(exc.detail, str) else None,
            )
        ),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def error_no_controlado(request: Request, exc: Exception):
    """Ultima red de seguridad: nunca se filtra un stacktrace al cliente."""
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            ErrorResponse(
                error="error_interno",
                mensaje="El servidor de AthenIA tuvo un problema. Intenta mas tarde.",
                detail=None,
            )
        ),
    )


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


@app.get("/", tags=["Meta"], summary="Informacion de la API")
def root() -> dict:
    """Punto de entrada informativo. Verifica de un vistazo que el deploy vive."""
    return {
        "nombre": settings.APP_NAME,
        "version": settings.VERSION,
        "entorno": settings.ENV,
        "motor": services.clasificador.motor,
        "modelo": services.clasificador.nombre,
        "docs": "/docs",
        "endpoints": [
            "POST /contenido",
            "GET /contenidos",
            "GET /contenidos/{id}",
            "GET /metricas",
            "GET /categorias",
            "GET /salud",
        ],
    }


@app.get(
    "/salud",
    tags=["Meta"],
    summary="Health check para QA / uptime",
    response_model=SaludOutput,
)
def salud() -> SaludOutput:
    """
    Verificacion de uptime usada por QA y por el monitoreo de OCI.

    Responde 200 mientras el proceso este vivo e informa que motor de
    clasificacion esta en uso:

    - `motor: "modelo_ml_real"`      -> artefacto entrenado cargado y verificado
    - `motor: "clasificador_reglas"` -> fallback por taxonomia de palabras clave
    """
    motor = services.clasificador
    return SaludOutput(
        estado="ok",
        version=settings.VERSION,
        entorno=settings.ENV,
        motor=motor.motor,
        modelo_cargado=motor.nombre,
        detalle_modelo=motor.detalle,
        es_mock=motor.es_mock,
        contenidos_en_historial=services.repositorio.total(),
    )


@app.get("/categorias", tags=["Contenido"], summary="Catalogo de categorias")
def categorias() -> dict:
    """Lista de categorias que el clasificador activo puede devolver."""
    return {"categorias": services.clasificador.categorias()}


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------


@app.post(
    "/contenido",
    tags=["Contenido"],
    summary="Clasificar contenido tecnico",
    response_model=AnalisisOutput,
    status_code=status.HTTP_200_OK,
    responses={422: {"model": ErrorResponse}},
)
def analizar_contenido(payload: ContenidoInput) -> AnalisisOutput:
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
    registro = services.analizar_y_guardar(payload.model_dump())
    return AnalisisOutput(**registro)


@app.get(
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
) -> ListaContenidos:
    """
    Devuelve los analisis realizados, del mas reciente al mas antiguo.

    Alimenta el Dashboard y la vista "Buscar Contenidos" del frontend.
    """
    items = services.repositorio.listar(categoria=categoria, buscar=buscar, limite=limite)
    return ListaContenidos(
        total=len(items),
        items=[ContenidoAlmacenado(**item) for item in items],
    )


@app.get(
    "/contenidos/{contenido_id}",
    tags=["Historial"],
    summary="Detalle de un analisis",
    response_model=ContenidoAlmacenado,
    responses={404: {"model": ErrorResponse}},
)
def obtener_contenido(contenido_id: int) -> ContenidoAlmacenado:
    """Devuelve un analisis por su identificador, o 404 si no existe."""
    item = services.repositorio.obtener(contenido_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un contenido con id {contenido_id}.",
        )
    return ContenidoAlmacenado(**item)


@app.delete(
    "/contenidos",
    tags=["Historial"],
    summary="Vaciar el historial (utilidad para QA)",
    status_code=status.HTTP_200_OK,
)
def limpiar_contenidos() -> dict:
    """
    Vacia el historial en memoria.

    Pensado para que QA parta de un estado limpio entre sesiones de prueba
    manual sin reiniciar el servidor.
    """
    eliminados = services.repositorio.total()
    services.repositorio.limpiar()
    logger.info("Historial vaciado (%d items).", eliminados)
    return {"eliminados": eliminados, "mensaje": "Historial vaciado."}


@app.get(
    "/metricas",
    tags=["Historial"],
    summary="Metricas agregadas del historial",
    response_model=MetricasOutput,
)
def metricas() -> MetricasOutput:
    """Agregados que alimentan las tarjetas y el grafico del Dashboard."""
    return MetricasOutput(**services.calcular_metricas(services.repositorio.listar()))


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.es_produccion,
    )
