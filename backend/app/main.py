"""
AthenIA - Composicion de la aplicacion FastAPI.
==================================================

Tras el refactor SOLID de la Semana 3, este archivo dejo de mezclar 8 rutas,
3 exception handlers, el CORS y el `lifespan` en 383 lineas (violacion de
SRP). Ahora solo:

  1. Construye la app y le aplica configuracion (CORS, middleware de timing).
  2. Registra el manejo de errores (`errors.py`).
  3. Incluye los routers (`routers/salud.py`, `routers/contenido.py`).
  4. Define el ciclo de vida (arranque/apagado).

Ninguna logica de negocio ni de clasificacion vive aqui. Ver `services.py`
para la raiz de composicion de dominio, y `docs/GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md`
para el detalle de por que quedo asi.

Ejecutar en local:
    uvicorn app.main:app --reload --port 8000    # desde backend/
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import services
from .config import settings
from .errors import configurar_manejo_de_errores
from .routers import contenido, salud
from .schemas import ErrorResponse

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


configurar_manejo_de_errores(app)

app.include_router(salud.router)
app.include_router(contenido.router)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.es_produccion,
    )
