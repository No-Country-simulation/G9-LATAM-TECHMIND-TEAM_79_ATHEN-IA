"""
Abstracciones del dominio (Dependency Inversion Principle).
===========================================================

Las capas superiores (rutas, servicios) dependen **solo** de estos contratos,
nunca de una implementacion concreta. Gracias a eso:

- Las rutas no saben si responde `clasificador_cursos.pkl`, el fallback por
  reglas o el motor de embeddings que llegue en la Semana 4.
- El servicio de analisis no sabe si el historial vive en memoria o en Oracle
  Autonomous Database.
- Las pruebas pueden inyectar dobles sin tocar el codigo de produccion.

Se usa `typing.Protocol` (tipado estructural) en lugar de herencia obligatoria:
una implementacion cumple el contrato por su forma, sin tener que importar de
aqui. Eso mantiene el acoplamiento en cero.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Identificadores de motor reportados por `GET /salud`
# ---------------------------------------------------------------------------

MOTOR_ML = "modelo_ml_real"
MOTOR_REGLAS = "clasificador_reglas"


# ---------------------------------------------------------------------------
# Clasificacion
# ---------------------------------------------------------------------------


@runtime_checkable
class Clasificador(Protocol):
    """
    Contrato de cualquier motor de clasificacion de AthenIA.

    Implementaciones actuales:
      - `ml.reglas.ClasificadorReglas`  (taxonomia de palabras clave)
      - `ml.modelo.ClasificadorML`      (artefacto de scikit-learn)

    Para agregar un motor nuevo (embeddings, LLM, ensemble) basta con cumplir
    esta forma y registrarlo en `ml.registro`. Ni las rutas ni los servicios
    cambian: eso es el Open/Closed Principle en la practica.
    """

    #: Identificador del artefacto o version de reglas. Ej: "clasificador_cursos.pkl".
    nombre: str
    #: `MOTOR_ML` o `MOTOR_REGLAS`. Lo expone `GET /salud`.
    motor: str
    #: True mientras no haya un modelo entrenado real respondiendo.
    es_mock: bool
    #: Descripcion corta para diagnostico. Ej: "Pipeline".
    detalle: str

    def clasificar(self, titulo: str, texto: str) -> dict:
        """
        Clasifica el contenido.

        Devuelve un dict compatible con `schemas.AnalisisOutput`. Claves
        obligatorias: `categoria`, `probabilidad`, `informacion_adicional`.

        **No debe lanzar**: un motor que falle internamente tiene que degradar
        a un resultado valido. La API nunca devuelve 500 por culpa del modelo.
        """
        ...

    def categorias(self) -> List[str]:
        """Catalogo de categorias que este motor puede devolver."""
        ...


class ClasificadorBase(ABC):
    """
    Clase base opcional para clasificadores.

    Cumplir el `Protocol` no exige heredar de aqui; esta clase solo evita
    repetir los atributos por defecto. Un motor externo puede ignorarla por
    completo mientras respete la forma de `Clasificador`.
    """

    nombre: str = "base"
    motor: str = MOTOR_REGLAS
    es_mock: bool = True
    detalle: str = ""

    @abstractmethod
    def clasificar(self, titulo: str, texto: str) -> dict:
        """Ver `Clasificador.clasificar`."""

    def categorias(self) -> List[str]:
        from .taxonomia import categorias_soportadas

        return categorias_soportadas()


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------


@runtime_checkable
class RepositorioContenidos(Protocol):
    """
    Contrato del historial de analisis.

    Implementacion actual: `repositories.memoria.RepositorioMemoria`.
    En la Semana 3+ se sustituye por un repositorio contra Oracle Autonomous
    Database cumpliendo esta misma forma, sin tocar servicios ni rutas.
    """

    def agregar(self, contenido: dict) -> dict:
        """Guarda un analisis y devuelve el registro con `id` y `creado_en`."""
        ...

    def listar(
        self,
        categoria: Optional[str] = None,
        buscar: Optional[str] = None,
        limite: Optional[int] = None,
    ) -> List[dict]:
        """Historial del mas reciente al mas antiguo, con filtros opcionales."""
        ...

    def obtener(self, contenido_id: int) -> Optional[dict]:
        """Un analisis por su id, o `None` si no existe."""
        ...

    def limpiar(self) -> None:
        """Vacia el historial."""
        ...

    def total(self) -> int:
        """Cantidad de analisis almacenados."""
        ...


# ---------------------------------------------------------------------------
# Tipos de apoyo
# ---------------------------------------------------------------------------


class AnalisisGuardado(Protocol):
    """Forma de un registro del historial. Documental; no se instancia."""

    id: int
    titulo: str
    texto: str
    categoria: str
    probabilidad: float
    informacion_adicional: List[str]
    creado_en: datetime
