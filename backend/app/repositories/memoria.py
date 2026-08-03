"""
Historial de analisis en memoria.
====================================

Implementacion de `domain.protocols.RepositorioContenidos` que vive en un
`list` del proceso. Suficiente para el MVP y para la demo: el jurado ve el
historial crecer en vivo sin depender de una base de datos.

Sustitucion futura: un `RepositorioOracle` contra Autonomous Database
implementando el mismo `Protocol` (`agregar`, `listar`, `obtener`, `limpiar`,
`total`) reemplaza esta clase sin que `services.py` ni las rutas cambien.

Nota: al ser en memoria, el historial se pierde al reiniciar el proceso.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from itertools import count
from typing import List, Optional

from ..config import settings
from ..domain.taxonomia import normalizar


class RepositorioMemoria:
    """
    Historial de analisis en un `list` protegido por lock.

    El lock existe porque uvicorn puede atender peticiones desde distintos
    hilos del threadpool (los endpoints sincronos de FastAPI corren en un
    threadpool, no en la corrutina del event loop).
    """

    def __init__(self, maximo: Optional[int] = None) -> None:
        self._items: List[dict] = []
        self._secuencia = count(1)
        self._lock = threading.Lock()
        self._maximo = maximo or settings.MAX_HISTORIAL

    # --- Escritura ---------------------------------------------------------

    def agregar(self, contenido: dict) -> dict:
        """Guarda un analisis y devuelve el registro con `id` y `creado_en`."""
        with self._lock:
            registro = {
                **contenido,
                "id": next(self._secuencia),
                "creado_en": datetime.now(timezone.utc),
            }
            self._items.append(registro)

            # Descarta los mas antiguos para acotar el uso de memoria.
            if len(self._items) > self._maximo:
                self._items = self._items[-self._maximo :]

            return registro

    def limpiar(self) -> None:
        """Vacia el historial. La usan las pruebas para aislarse entre casos."""
        with self._lock:
            self._items.clear()
            self._secuencia = count(1)

    # --- Lectura -----------------------------------------------------------

    def listar(
        self,
        categoria: Optional[str] = None,
        buscar: Optional[str] = None,
        limite: Optional[int] = None,
    ) -> List[dict]:
        """
        Devuelve el historial del mas reciente al mas antiguo.

        `buscar` hace coincidencia parcial, sin acentos, sobre titulo, texto,
        categoria y palabras clave — el mismo criterio que usa la vista
        "Buscar Contenidos" del frontend.
        """
        with self._lock:
            items = list(self._items)

        if categoria:
            objetivo = normalizar(categoria)
            items = [i for i in items if normalizar(i["categoria"]) == objetivo]

        if buscar:
            termino = normalizar(buscar)
            items = [i for i in items if termino in self._corpus(i)]

        items.sort(key=lambda i: i["id"], reverse=True)

        return items[:limite] if limite else items

    def obtener(self, contenido_id: int) -> Optional[dict]:
        """Devuelve un analisis por su id, o `None` si no existe."""
        with self._lock:
            return next((i for i in self._items if i["id"] == contenido_id), None)

    def total(self) -> int:
        with self._lock:
            return len(self._items)

    @staticmethod
    def _corpus(item: dict) -> str:
        """Texto normalizado sobre el que se aplica la busqueda libre."""
        partes = [
            item.get("titulo", ""),
            item.get("texto", ""),
            item.get("categoria", ""),
            *item.get("informacion_adicional", []),
        ]
        return normalizar(" ".join(partes))
