"""
Manejo uniforme de errores HTTP.
===================================

Extraido de `main.py` (SRP): antes los 3 exception handlers vivian mezclados
con la definicion de rutas y el arranque de la app. Aqui solo hay traduccion
de excepciones a `ErrorResponse`; no conocen logica de negocio.

`configurar_manejo_de_errores(app)` se llama una vez desde `main.py` al
construir la aplicacion.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas import ErrorResponse

logger = logging.getLogger("athenia.errors")


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


def configurar_manejo_de_errores(app: FastAPI) -> None:
    """Registra los exception handlers globales sobre `app`."""

    @app.exception_handler(RequestValidationError)
    async def error_de_validacion(request: Request, exc: RequestValidationError):
        """
        422 con formato `ErrorResponse`.

        `detail` conserva la estructura nativa de FastAPI (lista con `loc`,
        `msg`, `type`) para no romper clientes ni la prueba CP-26; `error` y
        `mensaje` la envuelven con texto que el frontend puede mostrar tal cual.
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
