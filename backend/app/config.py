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
| `ATHENIA_MODELOS_DIR`    | `backend/models`              | Carpeta de artefactos de Data Science.        |
| `ATHENIA_MODELO_PATH`    | autodeteccion                 | Ruta explicita al `.pkl` / `.joblib`.         |
| `ATHENIA_SEED_DEMO`      | `true`                        | Precarga contenido de ejemplo al arrancar.    |
| `ATHENIA_MAX_HISTORIAL`  | `500`                         | Tope de items en el historial en memoria.     |
| `ATHENIA_DB_URL`         | sqlite local (`backend/data`) | Base de usuarios. Postgres en produccion.     |
| `ATHENIA_OCI_BUCKET`     | vacio                         | Reservado: bucket de Object Storage.          |
| `ATHENIA_JWT_SECRET`     | clave de desarrollo           | Firma de los JWT de sesion. Cambiar en prod.  |
| `ATHENIA_JWT_EXPIRA_MIN` | `1440` (24 h)                 | Vigencia del token de sesion, en minutos.     |
| `ATHENIA_OPENAI_API_KEY` | vacio                         | Habilita el Asistente conversacional.         |
| `ATHENIA_OPENAI_MODEL`   | `gpt-4o-mini`                 | Modelo de OpenAI usado por el Asistente.      |
| `ATHENIA_OPENAI_MAX_TOKENS` | `500`                      | Tope de tokens de la respuesta del Asistente. |
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

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
    VERSION: str = "0.4.0"
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
        # Carpeta donde el equipo de Data Science deja el artefacto entrenado.
        self.MODELOS_DIR: Path = Path(os.getenv("ATHENIA_MODELOS_DIR", str(BASE_DIR / "models")))

        # Ruta explicita al artefacto. Si no se define, `services.localizar_modelo()`
        # busca en MODELOS_DIR por los nombres conocidos.
        modelo_env = os.getenv("ATHENIA_MODELO_PATH")
        self.MODELO_PATH: Optional[Path] = Path(modelo_env) if modelo_env else None

        # --- Historial en memoria ------------------------------------------
        self.SEED_DEMO: bool = _bool_env("ATHENIA_SEED_DEMO", True)
        self.MAX_HISTORIAL: int = _int_env("ATHENIA_MAX_HISTORIAL", 500)

        # --- Base de usuarios (Semana 5) -------------------------------------
        # Sin definir, cae a un archivo SQLite dentro de `backend/data/`: el
        # equipo clona el repo y el login funciona sin levantar Postgres. En
        # OCI, `docker-compose.yml` define `ATHENIA_DB_URL` apuntando al
        # servicio `athenia-db` (Postgres). Mismo codigo, distinto dialecto
        # segun la URL — ver `repositories/usuarios_sql.py`.
        db_url_env = os.getenv("ATHENIA_DB_URL", "").strip()
        if db_url_env:
            self.DB_URL: str = db_url_env
        else:
            datos_dir = BASE_DIR / "data"
            datos_dir.mkdir(parents=True, exist_ok=True)
            self.DB_URL = f"sqlite:///{datos_dir / 'athenia_usuarios.db'}"

        # --- Sesiones (JWT) ---------------------------------------------------
        # El valor por defecto es SOLO para desarrollo local: firmar tokens con
        # una clave conocida publicamente (este mismo repo) es inseguro en
        # produccion. `es_produccion` + `ATHENIA_JWT_SECRET` sin definir se
        # reporta en `GET /salud` -> ver `services` / `routers/salud.py`.
        self.JWT_SECRET: str = os.getenv(
            "ATHENIA_JWT_SECRET", "athenia-dev-secret-no-usar-en-produccion"
        )
        self.JWT_EXPIRA_MINUTOS: int = _int_env("ATHENIA_JWT_EXPIRA_MIN", 60 * 24)

        # --- Reservado (Object Storage / OCI) --------------------------------
        self.OCI_BUCKET: str = os.getenv("ATHENIA_OCI_BUCKET", "")
        self.OCI_NAMESPACE: str = os.getenv("ATHENIA_OCI_NAMESPACE", "")
        self.OCI_REGION: str = os.getenv("ATHENIA_OCI_REGION", "")

        # --- Asistente conversacional (OpenAI) -------------------------------
        # Sin API key, `ModeloLenguajeOpenAI.disponible` queda en False y el
        # Asistente responde solo con los cursos encontrados (sin redaccion),
        # en vez de lanzar — ver `asistente/motor_openai.py`.
        self.OPENAI_API_KEY: str = os.getenv("ATHENIA_OPENAI_API_KEY", "")
        self.OPENAI_MODEL: str = os.getenv("ATHENIA_OPENAI_MODEL", "gpt-4o-mini")
        self.OPENAI_MAX_TOKENS: int = _int_env("ATHENIA_OPENAI_MAX_TOKENS", 500)
        self.OPENAI_BASE_URL: str = os.getenv("ATHENIA_OPENAI_BASE_URL", "")
    @property
    def es_produccion(self) -> bool:
        return self.ENV == "production"

    @property
    def docs_habilitados(self) -> bool:
        """Swagger queda expuesto siempre en el MVP: el jurado debe poder probarlo."""
        return True

    @property
    def jwt_secreto_por_defecto(self) -> bool:
        """True si nadie configuro `ATHENIA_JWT_SECRET` (inseguro fuera de desarrollo)."""
        return self.JWT_SECRET == "athenia-dev-secret-no-usar-en-produccion"

    def __repr__(self) -> str:  # pragma: no cover - solo para debugging
        modelo = self.MODELO_PATH.name if self.MODELO_PATH else "auto"
        return (
            f"<Settings env={self.ENV} port={self.PORT} "
            f"cors={self.CORS_ORIGINS} modelo={modelo}>"
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
