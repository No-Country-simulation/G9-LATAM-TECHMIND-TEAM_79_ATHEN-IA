"""
Casos de uso de autenticacion.
=================================

Analogo a `services.py` (que orquesta clasificacion + historial), pero para
usuarios. Las rutas de `routers/auth.py` no hashean contrasenas ni consultan
el repositorio directamente: llaman a estas funciones, que si conocen los
`Protocol` del dominio (`RepositorioUsuarios`) pero no una implementacion
concreta.
"""

from __future__ import annotations

from typing import Optional

from .domain.protocols import RepositorioUsuarios
from .domain.seguridad import crear_token, hash_password, verificar_password
from .domain.usuarios import rol_por_defecto


class CredencialesInvalidas(Exception):
    """El email no existe o la contrasena no coincide. Se traduce a un 401."""


class CorreoYaRegistrado(Exception):
    """Ya existe una cuenta con ese correo. Se traduce a un 409."""


def registrar_usuario(repositorio: RepositorioUsuarios, email: str, password: str, nombre: str) -> dict:
    """
    Crea la cuenta y devuelve el usuario (sin el hash).

    El rol se decide aqui, no en la ruta ni en el repositorio: el primer
    usuario de una instalacion nueva queda como `admin` (ver
    `domain.usuarios.rol_por_defecto`).
    """
    rol = rol_por_defecto(repositorio.total())
    try:
        usuario = repositorio.crear(
            email=email,
            password_hash=hash_password(password),
            nombre=nombre,
            rol=rol,
        )
    except ValueError as exc:
        raise CorreoYaRegistrado(str(exc)) from exc

    return _sin_password(usuario)


def autenticar_usuario(repositorio: RepositorioUsuarios, email: str, password: str) -> dict:
    """
    Verifica credenciales y devuelve el usuario si son correctas.

    Lanza `CredencialesInvalidas` tanto si el correo no existe como si la
    contrasena no coincide: no se distingue el motivo en la respuesta HTTP
    (evita filtrar que correos estan registrados por fuerza bruta).
    """
    usuario = repositorio.obtener_por_email(email)
    if usuario is None or not verificar_password(password, usuario["password_hash"]):
        raise CredencialesInvalidas("Correo o contrasena incorrectos.")
    return _sin_password(usuario)


def emitir_token(usuario: dict) -> str:
    """Genera el JWT de sesion para un usuario ya autenticado/registrado."""
    return crear_token({"sub": str(usuario["id"])})


def obtener_usuario_desde_payload(repositorio: RepositorioUsuarios, payload: Optional[dict]) -> Optional[dict]:
    """
    Resuelve el usuario actual a partir del payload decodificado del JWT.

    Devuelve `None` si el payload es invalido, no trae `sub`, o el usuario ya
    no existe (cuenta borrada tras emitirse el token) — `dependencies.py`
    traduce cualquiera de estos casos a un 401 uniforme.
    """
    if not payload:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        usuario_id = int(sub)
    except (TypeError, ValueError):
        return None

    usuario = repositorio.obtener_por_id(usuario_id)
    return _sin_password(usuario) if usuario else None


def _sin_password(usuario: dict) -> dict:
    """Copia el registro sin `password_hash`. Nunca debe salir de este modulo."""
    return {clave: valor for clave, valor in usuario.items() if clave != "password_hash"}
