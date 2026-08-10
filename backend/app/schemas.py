"""
Contratos de datos (Pydantic v2) de la API de AthenIA.
======================================================

Estos esquemas son el limite entre el frontend, QA y el equipo de Data
Science. Cambiar la implementacion del modelo no debe cambiar nada de aqui.

Contrato EXIGIDO por el Hackathon ONE Alura + Oracle
----------------------------------------------------
    POST /contenido
      Request : ContenidoInput  -> {"titulo": "...", "texto": "..."}
      Response: AnalisisOutput  -> {"categoria": "...", "probabilidad": 0.92,
                                    "informacion_adicional": ["..."]}

Los campos adicionales de `AnalisisOutput` son extensiones de AthenIA: el
frontend los usa para enriquecer la vista, y omitirlos no rompe el contrato.
"""

from datetime import datetime
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Reutilizados por varios esquemas para no repetir literales.
EJEMPLO_TITULO = "Introduccion a Spring Boot"
EJEMPLO_TEXTO = (
    "En este curso aprenderas a desarrollar APIs REST con Spring Boot, "
    "implementando buenas practicas, autenticacion con JWT, manejo de "
    "excepciones y conexion a bases de datos con Spring Data JPA."
)


# ===========================================================================
# Entrada
# ===========================================================================


class ContenidoInput(BaseModel):
    """Payload de entrada para `POST /contenido`."""

    titulo: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Titulo del curso o del contenido tecnico.",
    )
    texto: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
        description="Descripcion, temario o contenido a analizar.",
    )

    # --- Metadatos opcionales (no forman parte del contrato del Hackathon) --
    origen: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Fuente del contenido: Alura, Oracle Next Education, blog...",
    )
    url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Enlace al recurso original, si existe.",
    )

    @field_validator("titulo", "texto")
    @classmethod
    def no_puede_ser_espacios_en_blanco(cls, valor: str) -> str:
        """
        Rechaza cadenas que solo contienen espacios.

        `min_length` no cubre el caso `"   "`, y QA lo tiene como caso de
        prueba explicito (CP-24). Devolver el valor recortado evita ademas que
        el modelo reciba ruido al inicio/fin del texto.
        """
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El campo no puede estar vacio ni contener solo espacios.")
        return limpio

    @field_validator("origen", "url")
    @classmethod
    def normalizar_opcionales(cls, valor: Optional[str]) -> Optional[str]:
        """Convierte cadenas vacias en `None` para no guardar ruido."""
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"titulo": EJEMPLO_TITULO, "texto": EJEMPLO_TEXTO}]
        }
    )


# ===========================================================================
# Salida
# ===========================================================================


class AnalisisOutput(BaseModel):
    """
    Respuesta de `POST /contenido`.

    Los tres primeros campos son el contrato exigido por el Hackathon y NO
    deben renombrarse.
    """

    # --- Contrato oficial ---------------------------------------------------
    categoria: str = Field(
        ...,
        description="Categoria principal detectada por el modelo.",
    )
    probabilidad: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confianza del modelo sobre la categoria principal (0-1).",
    )
    informacion_adicional: List[str] = Field(
        default_factory=list,
        description="Palabras clave / tecnologias detectadas en el contenido.",
    )

    # --- Extensiones AthenIA ------------------------------------------------
    id: Optional[int] = Field(
        default=None,
        description="Identificador del analisis en el historial.",
    )
    resumen: str = Field(
        default="",
        description="Resumen corto del contenido analizado.",
    )
    categorias_relacionadas: List[str] = Field(
        default_factory=list,
        description="Otras categorias con puntaje relevante.",
    )
    modelo: str = Field(
        default="mock",
        description="Identificador del modelo que produjo la prediccion.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "categoria": "Backend",
                    "probabilidad": 0.92,
                    "informacion_adicional": ["Java", "Spring Boot", "API REST"],
                }
            ]
        }
    )


class ContenidoAlmacenado(AnalisisOutput):
    """
    Item del historial (`GET /contenidos`).

    Extiende `AnalisisOutput` con el contenido original y la marca temporal,
    para que el frontend pueda listarlo, filtrarlo y mostrar su detalle.
    """

    id: int = Field(..., description="Identificador unico del analisis.")
    titulo: str = Field(..., description="Titulo enviado al analizar.")
    texto: str = Field(..., description="Texto original analizado.")
    origen: Optional[str] = Field(default=None, description="Fuente del contenido.")
    url: Optional[str] = Field(default=None, description="Enlace al recurso original.")
    creado_en: datetime = Field(..., description="Fecha y hora del analisis (UTC).")


class ListaContenidos(BaseModel):
    """Respuesta paginada de `GET /contenidos`."""

    total: int = Field(..., description="Cantidad total de items tras aplicar filtros.")
    items: List[ContenidoAlmacenado] = Field(
        default_factory=list,
        description="Analisis ordenados del mas reciente al mas antiguo.",
    )


class MetricasOutput(BaseModel):
    """Metricas agregadas del historial. Alimenta el Dashboard del frontend."""

    total_cursos: int = Field(..., description="Contenidos analizados.")
    total_categorias: int = Field(..., description="Categorias distintas detectadas.")
    total_palabras_clave: int = Field(..., description="Palabras clave unicas extraidas.")
    confianza_promedio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Promedio de la confianza del modelo.",
    )
    distribucion: List["DistribucionCategoria"] = Field(
        default_factory=list,
        description="Conteo por categoria, de mayor a menor.",
    )
    top_palabras_clave: List["ConteoPalabraClave"] = Field(
        default_factory=list,
        description="Palabras clave mas frecuentes.",
    )


class DistribucionCategoria(BaseModel):
    """Una porcion del grafico de categorias."""

    categoria: str
    cantidad: int
    porcentaje: int = Field(..., ge=0, le=100)


class ConteoPalabraClave(BaseModel):
    """Frecuencia de una palabra clave en el historial."""

    palabra: str
    cantidad: int


class SaludOutput(BaseModel):
    """Respuesta de `GET /salud`, consumida por QA y el monitoreo de OCI."""

    estado: str = Field(..., description="'ok' mientras el proceso responda.")
    version: str = Field(..., description="Version de la API.")
    entorno: str = Field(..., description="development | production.")

    # --- Motor de clasificacion ---------------------------------------------
    motor: Literal["modelo_ml_real", "clasificador_reglas"] = Field(
        ...,
        description=(
            "Motor de inferencia en uso. `modelo_ml_real` cuando hay un "
            "artefacto entrenado cargado y verificado; `clasificador_reglas` "
            "cuando esta activo el fallback."
        ),
    )
    modelo_cargado: str = Field(
        ...,
        description="Nombre del artefacto (o de la version de reglas) activo.",
    )
    detalle_modelo: str = Field(
        default="",
        description="Tipo del estimador cargado. Util para diagnostico de QA.",
    )
    es_mock: bool = Field(
        ...,
        description="True mientras no se haya cargado el modelo entrenado real.",
    )

    contenidos_en_historial: int = Field(
        ...,
        description="Cantidad de analisis almacenados en memoria.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "estado": "ok",
                    "version": "0.4.0",
                    "entorno": "development",
                    "motor": "modelo_ml_real",
                    "modelo_cargado": "clasificador_cursos.pkl",
                    "detalle_modelo": "Pipeline",
                    "es_mock": False,
                    "contenidos_en_historial": 8,
                }
            ]
        }
    )


class ErrorResponse(BaseModel):
    """
    Formato uniforme de error.

    `detail` conserva la estructura nativa de FastAPI (lista de errores de
    validacion o mensaje simple) para no romper a los clientes existentes;
    `error` y `mensaje` la envuelven con algo legible para la UI.
    """

    error: str = Field(..., description="Codigo corto del error.")
    mensaje: str = Field(..., description="Mensaje legible para el usuario final.")
    detail: Optional[Union[str, List[Any]]] = Field(
        default=None,
        description="Detalle tecnico: errores de validacion o descripcion.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "validacion",
                    "mensaje": "Los datos enviados no son validos.",
                    "detail": [
                        {
                            "type": "missing",
                            "loc": ["body", "texto"],
                            "msg": "Field required",
                        }
                    ],
                }
            ]
        }
    )


# Resuelve las referencias adelantadas usadas en `MetricasOutput`.
MetricasOutput.model_rebuild()