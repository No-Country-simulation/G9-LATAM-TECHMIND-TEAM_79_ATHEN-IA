"""
Configuracion de la aplicacion AthenIA.
=======================================

Toda la configuracion se resuelve desde variables de entorno con valores por
defecto seguros para desarrollo local. Ningun otro modulo debe leer `os.environ`
directamente: asi el despliegue en OCI se ajusta sin tocar codigo.

Variables soportadas
--------------------
| Variable                 | Defecto                       | Descripcion                                   |
|--------------------------|-------------------------------|-----------------------------------------------|
| `ATHENIA_ENV`            | `development`                 | `development` \\| `production`                 |
| `ATHENIA_LOG_LEVEL`      | `INFO`                        | Nivel de logging.                             |
| `ATHENIA_CORS_ORIGINS`   | `*`                           | Origenes permitidos, separados por coma.      |
| `ATHENIA_HOST`           | `127.0.0.1`                   | Host de uvicorn.                              |
| `ATHENIA_PORT`           | `8000`                        | Puerto de uvicorn.                            |
| `ATHENIA_MODELO_PATH`    | `backend/models/classifier.joblib` | Artefacto entrenado por Data Science.    |
| `ATHENIA_SEED_DEMO`      | `true`                        | Precarga contenido de ejemplo al arrancar.    |
| `ATHENIA_MAX_HISTORIAL`  | `500`                         | Tope de items en el historial en memoria.     |
| `ATHENIA_DB_URL`         | vacio                         | Reservado: Oracle Autonomous DB (Semana 3).   |
| `ATHENIA_OCI_BUCKET`     | vacio                         | Reservado: bucket de Object Storage.          |
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

# Raiz de `backend/` (este archivo vive en backend/app/config.py).
BASE_DIR = Path(__file__).resolve().parent.parent


def _bool_env(nombre: str, defecto: bool) -> bool:
    """Lee un booleano tolerando 'true', '1', 'yes', 'si'."""
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "y", "si", "on"}


def _int_env(nombre: str, defecto: int) -> int:
    """Lee un entero; si el valor no es valido conserva el defecto."""
    try:
        return int(os.getenv(nombre, defecto))
    except (TypeError, ValueError):
        return defecto


class Settings:
    """Configuracion resuelta una sola vez por proceso."""

    # --- Identidad de la API ------------------------------------------------
    APP_NAME: str = "AthenIA API"
    VERSION: str = "0.3.0"
    DESCRIPTION: str = (
        "API de clasificacion inteligente de contenido tecnico. Recibe texto, "
        "lo clasifica por categoria, extrae palabras clave y devuelve metricas "
        "en formato JSON."
    )

    def __init__(self) -> None:
        # --- Entorno --------------------------------------------------------
        self.ENV: str = os.getenv("ATHENIA_ENV", "development").lower()
        self.LOG_LEVEL: str = os.getenv("ATHENIA_LOG_LEVEL", "INFO").upper()

        # --- Servidor -------------------------------------------------------
        self.HOST: str = os.getenv("ATHENIA_HOST", "127.0.0.1")
        self.PORT: int = _int_env("ATHENIA_PORT", 8000)

        # --- CORS -----------------------------------------------------------
        # En desarrollo se abre a "*" para que el equipo conecte desde
        # cualquier puerto de Vite. En produccion conviene enumerar dominios.
        origenes = os.getenv("ATHENIA_CORS_ORIGINS", "*")
        self.CORS_ORIGINS: List[str] = [o.strip() for o in origenes.split(",") if o.strip()]

        # --- Modelo de IA ---------------------------------------------------
        self.MODELO_PATH: Path = Path(
            os.getenv("ATHENIA_MODELO_PATH", str(BASE_DIR / "models" / "classifier.joblib"))
        )

        # --- Historial en memoria ------------------------------------------
        self.SEED_DEMO: bool = _bool_env("ATHENIA_SEED_DEMO", True)
        self.MAX_HISTORIAL: int = _int_env("ATHENIA_MAX_HISTORIAL", 500)

        # --- Reservado para la Semana 3 (integracion Oracle / OCI) ----------
        self.DB_URL: str = os.getenv("ATHENIA_DB_URL", "")
        self.OCI_BUCKET: str = os.getenv("ATHENIA_OCI_BUCKET", "")
        self.OCI_NAMESPACE: str = os.getenv("ATHENIA_OCI_NAMESPACE", "")
        self.OCI_REGION: str = os.getenv("ATHENIA_OCI_REGION", "")

    @property
    def es_produccion(self) -> bool:
        return self.ENV == "production"

    @property
    def docs_habilitados(self) -> bool:
        """Swagger queda expuesto siempre en el MVP: el jurado debe poder probarlo."""
        return True

    def __repr__(self) -> str:  # pragma: no cover - solo para debugging
        return (
            f"<Settings env={self.ENV} port={self.PORT} "
            f"cors={self.CORS_ORIGINS} modelo={self.MODELO_PATH.name}>"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Devuelve la configuracion (singleton).

    Cacheado para que la instancia sea unica. En las pruebas se puede limpiar
    con `get_settings.cache_clear()` tras modificar las variables de entorno.
    """
    return Settings()


settings = get_settings()
