"""
Rutas de autenticacion y usuarios (Semana 5).
=================================================

Sigue el mismo patron que `routers/contenido.py`: cada endpoint depende del
`Protocol` `RepositorioUsuarios` via `Depends`, nunca de
`RepositorioUsuariosSQL` directamente, y delega la logica de negocio en
`auth_service` (no hashea contrasenas ni arma JWT aqui).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from .. import auth_service
from ..dependencies import get_repositorio_usuarios, get_usuario_actual, requiere_rol
from ..domain.protocols import RepositorioUsuarios
from ..schemas import ErrorResponse, TokenOutput, UsuarioLogin, UsuarioOutput, UsuarioRegistro

logger = logging.getLogger("athenia.routers.auth")

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post(
    "/registro",
    summary="Crear una cuenta",
    response_model=TokenOutput,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def registrar(
    payload: UsuarioRegistro,
    repositorio: RepositorioUsuarios = Depends(get_repositorio_usuarios),
) -> TokenOutput:
    """
    Crea la cuenta y devuelve un token de sesion (login automatico).

    El primer usuario que se registra en una instalacion nueva de AthenIA
    recibe el rol `admin` automaticamente; el resto entra como `estudiante`
    (ver `domain.usuarios.rol_por_defecto`). 409 si el correo ya existe.
    """
    try:
        usuario = auth_service.registrar_usuario(
            repositorio, email=payload.email, password=payload.password, nombre=payload.nombre
        )
    except auth_service.CorreoYaRegistrado as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    logger.info("Cuenta creada: %s (rol=%s)", usuario["email"], usuario["rol"])
    token = auth_service.emitir_token(usuario)
    return TokenOutput(access_token=token, usuario=UsuarioOutput(**usuario))


@router.post(
    "/login",
    summary="Iniciar sesion",
    response_model=TokenOutput,
    responses={401: {"model": ErrorResponse}},
)
def iniciar_sesion(
    payload: UsuarioLogin,
    repositorio: RepositorioUsuarios = Depends(get_repositorio_usuarios),
) -> TokenOutput:
    """Verifica credenciales y devuelve un JWT. 401 si el correo o la contrasena no coinciden."""
    try:
        usuario = auth_service.autenticar_usuario(repositorio, email=payload.email, password=payload.password)
    except auth_service.CredencialesInvalidas as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    token = auth_service.emitir_token(usuario)
    return TokenOutput(access_token=token, usuario=UsuarioOutput(**usuario))


@router.get(
    "/me",
    summary="Usuario autenticado",
    response_model=UsuarioOutput,
    responses={401: {"model": ErrorResponse}},
)
def usuario_actual(usuario: dict = Depends(get_usuario_actual)) -> UsuarioOutput:
    """Devuelve el usuario dueno del token enviado en `Authorization: Bearer <token>`."""
    return UsuarioOutput(**usuario)


@router.get(
    "/usuarios",
    summary="Listar usuarios (solo admin)",
    response_model=list[UsuarioOutput],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def listar_usuarios(
    repositorio: RepositorioUsuarios = Depends(get_repositorio_usuarios),
    _admin: dict = Depends(requiere_rol("admin")),
) -> list[UsuarioOutput]:
    """
    Catalogo de cuentas registradas. Demuestra el control de acceso por rol:
    un `estudiante` recibe 403 aunque su token sea valido.
    """
    return [UsuarioOutput(**u) for u in repositorio.listar()]
