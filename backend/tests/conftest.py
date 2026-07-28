"""
Configuracion compartida de pytest - QA AthenIA.
================================================

Responsabilidades:

  1. Desactivar la semilla de demo ANTES de importar la app, para que cada
     prueba parta de un historial vacio y predecible.
  2. Agregar `backend/` al `sys.path` para que `from app.main import app`
     funcione sin instalar el backend como paquete.
  3. Exponer el `TestClient` y payloads de referencia como fixtures.
"""

import os
import sys
from pathlib import Path

# --- 1. El entorno debe quedar fijado ANTES de importar la aplicacion ------
# `config.Settings` se resuelve en tiempo de import, asi que este orden importa.
os.environ.setdefault("ATHENIA_SEED_DEMO", "false")
os.environ.setdefault("ATHENIA_ENV", "test")
os.environ.setdefault("ATHENIA_LOG_LEVEL", "WARNING")

# --- 2. Rutas --------------------------------------------------------------
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import services  # noqa: E402
from app.main import app  # noqa: E402


# --- 3. Fixtures -----------------------------------------------------------


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Cliente HTTP contra la app FastAPI, sin levantar un servidor real."""
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture(autouse=True)
def historial_limpio():
    """
    Vacia el historial antes de cada prueba.

    `autouse` para que ninguna prueba dependa del orden de ejecucion ni de los
    contenidos que hayan guardado las anteriores.
    """
    services.repositorio.limpiar()
    yield
    services.repositorio.limpiar()


@pytest.fixture
def payload_valido() -> dict:
    """Payload de referencia de QA (caso feliz: contenido de Backend)."""
    return {
        "titulo": "Introduccion a Spring Boot",
        "texto": (
            "En este curso aprenderas a desarrollar APIs REST con Spring Boot, "
            "implementando buenas practicas, autenticacion con JWT, manejo de "
            "excepciones y conexion a bases de datos con Spring Data JPA."
        ),
    }


@pytest.fixture
def historial_poblado(client, payload_valido) -> list:
    """
    Crea tres analisis de categorias distintas y devuelve sus respuestas.

    Base comun para las pruebas de `GET /contenidos` y `GET /metricas`.
    """
    entradas = [
        payload_valido,
        {
            "titulo": "Docker para Principiantes",
            "texto": "Conceptos de contenedores, Dockerfile, Kubernetes y CI/CD.",
        },
        {
            "titulo": "Machine Learning con Python",
            "texto": "Modelos con Scikit-Learn, Pandas y NLP usando TF-IDF.",
        },
    ]
    return [client.post("/contenido", json=entrada).json() for entrada in entradas]
