"""
Roles y reglas de negocio puras de usuarios (dominio).
=======================================================

Analogo a `domain/confianza.py` y `domain/taxonomia.py`: constantes y
funciones sin efectos secundarios, sin saber si el usuario vive en SQLite,
Postgres o memoria. Las implementaciones concretas (hashing, JWT, SQL) viven
en `domain/seguridad.py` y `repositories/usuarios_sql.py`.
"""

from __future__ import annotations

from typing import Literal

ROL_ADMIN = "admin"
ROL_ESTUDIANTE = "estudiante"

Rol = Literal["admin", "estudiante"]

#: Roles validos, en el orden en que se muestran en la UI de administracion.
ROLES_VALIDOS: tuple[str, ...] = (ROL_ADMIN, ROL_ESTUDIANTE)


def rol_por_defecto(total_usuarios_existentes: int) -> Rol:
    """
    Determina el rol de un usuario nuevo.

    El primer usuario que se registra en una instalacion nueva de AthenIA
    (`total_usuarios_existentes == 0`) queda como `admin` automaticamente: sin
    esto, nadie podria alcanzar nunca las rutas de administracion en un
    despliegue limpio (huevo y gallina). El resto de registros entra como
    `estudiante`, el rol de uso normal de la plataforma.
    """
    return ROL_ADMIN if total_usuarios_existentes == 0 else ROL_ESTUDIANTE


def es_rol_valido(rol: str) -> bool:
    """True si `rol` es uno de los roles que AthenIA reconoce."""
    return rol in ROLES_VALIDOS
