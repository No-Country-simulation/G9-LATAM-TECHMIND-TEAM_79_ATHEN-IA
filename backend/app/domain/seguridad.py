"""
Hashing de contrasenas y tokens de sesion (JWT).
==================================================

Modulo de infraestructura ligera, aislado del resto del dominio a proposito:
es el UNICO lugar del backend que importa `passlib` y `jose`. Si mañana se
cambia bcrypt por argon2, o JWT por sesiones opacas en Redis, solo este
archivo se toca — `routers/auth.py` y `dependencies.py` siguen llamando a
`hash_password`, `verificar_password`, `crear_token` y `decodificar_token`
sin saber como estan implementados.

Nunca se registra ni se loggea una contrasena en texto plano ni un token
completo: solo el resultado (True/False, o el payload ya decodificado).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings

_contexto_password = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITMO_JWT = "HS256"


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de `password`. Nunca falla con una excepcion util al cliente."""
    return _contexto_password.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """True si `password` corresponde al hash guardado. False ante cualquier problema."""
    try:
        return _contexto_password.verify(password, password_hash)
    except (ValueError, TypeError):
        # Hash corrupto o con formato desconocido: nunca se autentica por error.
        return False


def crear_token(datos: dict[str, Any], expira_minutos: Optional[int] = None) -> str:
    """
    Firma un JWT con `datos` como payload (tipicamente `sub` = id de usuario).

    Usa `ATHENIA_JWT_SECRET` (ver `config.py`). En desarrollo hay un valor por
    defecto para que el equipo no tenga que configurar nada; en produccion
    DEBE sobreescribirse via variable de entorno.
    """
    minutos = expira_minutos if expira_minutos is not None else settings.JWT_EXPIRA_MINUTOS
    expira = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    payload = {**datos, "exp": expira}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITMO_JWT)


def decodificar_token(token: str) -> Optional[dict[str, Any]]:
    """
    Devuelve el payload del token si es valido y no expiro, o `None`.

    No lanza: un token invalido, corrupto o expirado es indistinguible de "no
    hay sesion" para quien llama — es responsabilidad de `dependencies.py`
    traducir eso a un 401.
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITMO_JWT])
    except JWTError:
        return None
