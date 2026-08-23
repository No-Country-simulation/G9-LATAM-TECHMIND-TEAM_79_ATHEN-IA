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
from .routers import analiticas, auth, contenido, cursos, salud
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

    if settings.es_produccion and settings.jwt_secreto_por_defecto:
        # No se bloquea el arranque (el jurado necesita que la demo funcione),
        # pero queda gritando en los logs de OCI hasta que se configure.
        logger.warning(
            "ATHENIA_JWT_SECRET no esta configurado en produccion: los tokens "
            "de sesion se firman con la clave de desarrollo publica del repo."
        )

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
app.include_router(analiticas.router)
app.include_router(cursos.router)
app.include_router(auth.router)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.es_produccion,
    )


# --- RUTA DIRECTA DE RECOMENDACIONES (.PKL) ---
@app.get("/recomendaciones-matriz/{curso_id}", tags=["Recomendaciones Matriz"])
def obtener_recomendaciones_matriz(curso_id: int, limite: int = 4):
    """
    Devuelve recomendaciones usando la matriz de similitud de NumPy (.pkl).

    Reutiliza `recomendador_matriz` (instancia unica) en vez de instanciar
    `MatrixRecommender()` en cada request: esa version recargaba los ~190 MB
    de la matriz con `joblib.load()` en cada llamada a este endpoint.
    Duplica `/cursos/{id}/relacionados-matriz` a proposito (ver ese router
    para el mismo dato con el motivo de fallo incluido); se deja este alias
    porque el frontend ya lo referencia en algunos lugares.
    """
    from .ml.matrix_recommender import recomendador_matriz

    resultados = recomendador_matriz.recomendar(curso_idx=curso_id, top_n=limite)
    return {
        "recomendaciones": resultados,
        "motivo": recomendador_matriz.ultimo_error if not resultados else None,
    }
