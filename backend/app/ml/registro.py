"""
Registro de proveedores de clasificacion (extension point del OCP).
=====================================================================

Este modulo es el UNICO lugar del backend que decide "cual motor gana".
Ningun otro archivo contiene un if/else de motores: agregar uno nuevo es
registrar un proveedor aqui, nunca editar esta logica de resolucion.

Un `ProveedorClasificador` es simplemente un nombre, una prioridad y una
funcion `cargar() -> Optional[Clasificador]` que intenta construir el motor y
devuelve `None` si no esta disponible (sin artefacto, dependencia ausente,
version incompatible...). `resolver()` prueba los proveedores registrados en
orden de prioridad y se queda con el primero que responda; si ninguno lo
hace, cae al clasificador por reglas, que es la unica garantia incondicional
del sistema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

from ..domain.protocols import Clasificador

logger = logging.getLogger("athenia.ml.registro")


@dataclass(frozen=True)
class ProveedorClasificador:
    """Un motor de clasificacion candidato, con su prioridad de intento."""

    nombre: str
    cargar: Callable[[], Optional[Clasificador]]
    prioridad: int


class RegistroProveedores:
    """
    Coleccion ordenada de proveedores de clasificacion.

    `registrar()` es la unica operacion de escritura: la usan los modulos de
    `ml/` al importarse (ver `ml/__init__.py`). `resolver()` es de solo
    lectura y no conoce ningun proveedor por nombre — por eso agregar el
    motor de la Semana 4 no requiere tocar esta clase.
    """

    def __init__(self) -> None:
        self._proveedores: List[ProveedorClasificador] = []

    def registrar(
        self,
        nombre: str,
        cargar: Callable[[], Optional[Clasificador]],
        prioridad: int = 50,
    ) -> None:
        """Anade un proveedor. Menor `prioridad` se intenta primero."""
        self._proveedores.append(ProveedorClasificador(nombre, cargar, prioridad))

    def resolver(self) -> Clasificador:
        """
        Devuelve el primer motor disponible, en orden de prioridad.

        Cada `cargar()` esta blindado individualmente: si uno lanza una
        excepcion inesperada (en vez de devolver `None` con elegancia), se
        registra el error y se sigue con el siguiente proveedor en lugar de
        tumbar el arranque de la API.
        """
        for proveedor in sorted(self._proveedores, key=lambda p: p.prioridad):
            try:
                motor = proveedor.cargar()
            except Exception:  # noqa: BLE001 - un proveedor roto no debe tumbar el arranque
                logger.exception("El proveedor '%s' fallo al intentar cargar.", proveedor.nombre)
                continue

            if motor is not None:
                logger.info("Proveedor activo: '%s' -> %s", proveedor.nombre, motor.nombre)
                return motor

        # Piso incondicional: garantiza que SIEMPRE hay un clasificador
        # utilizable, aunque no se haya registrado ningun proveedor.
        from .reglas import ClasificadorReglas

        logger.info("Ningun proveedor disponible. Motor activo: clasificador por reglas.")
        return ClasificadorReglas()


# Instancia unica del proceso. `ml/__init__.py` registra los proveedores
# conocidos sobre ella; `services.py` la consulta a traves de
# `ml.registro.registro.resolver()`.
registro = RegistroProveedores()
