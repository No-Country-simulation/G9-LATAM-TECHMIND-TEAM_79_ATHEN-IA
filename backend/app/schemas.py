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
    nivel_confianza: Literal["alta", "media", "baja"] = Field(
        default="baja",
        description=(
            "Franja de certeza declarada por el modelo: alta (>=75%), "
            "media (50-74%) o baja (<50%). Usa los mismos umbrales que la "
            "distribucion de `GET /analiticas`. Cuando es 'baja', la interfaz "
            "advierte al usuario en vez de presentar la categoria como firme."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "categoria": "Backend",
                    "probabilidad": 0.92,
                    "informacion_adicional": ["Java", "Spring Boot", "API REST"],
                    "nivel_confianza": "alta",
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


# ===========================================================================
# Recomendaciones (Semana 4)
# ===========================================================================


class RecomendacionItem(BaseModel):
    """Un contenido recomendado, con la evidencia de por que se recomendo."""

    id: int = Field(..., description="Identificador del contenido recomendado.")
    titulo: str = Field(..., description="Titulo del contenido recomendado.")
    categoria: str = Field(..., description="Categoria detectada por el modelo.")
    probabilidad: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confianza con la que se clasifico el contenido recomendado.",
    )
    resumen: str = Field(default="", description="Resumen corto del contenido.")
    origen: Optional[str] = Field(default=None, description="Fuente del contenido.")

    puntaje: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Relevancia respecto al contenido consultado (0-1). Combina "
            "similitud de palabras clave (75%) y coincidencia de categoria (25%)."
        ),
    )
    palabras_compartidas: List[str] = Field(
        default_factory=list,
        description=(
            "Tecnologias presentes en ambos contenidos. Permiten a la UI "
            "explicar la recomendacion en vez de mostrar un puntaje opaco."
        ),
    )


class ListaRecomendaciones(BaseModel):
    """Respuesta de `GET /contenidos/{id}/recomendaciones`."""

    contenido_id: int = Field(..., description="Contenido de referencia consultado.")
    titulo: str = Field(..., description="Titulo del contenido de referencia.")
    estrategia: str = Field(
        ...,
        description="Motor de recomendacion que produjo la lista. Ej: 'keywords-jaccard-v1'.",
    )
    total: int = Field(..., description="Cantidad de recomendaciones devueltas.")
    items: List[RecomendacionItem] = Field(
        default_factory=list,
        description="Recomendaciones ordenadas de mayor a menor relevancia.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "contenido_id": 3,
                    "titulo": "Docker para Principiantes",
                    "estrategia": "keywords-jaccard-v1",
                    "total": 1,
                    "items": [
                        {
                            "id": 8,
                            "titulo": "Kubernetes en Produccion",
                            "categoria": "Cloud Computing y DevOps",
                            "probabilidad": 0.76,
                            "resumen": "Orquestacion de contenedores...",
                            "origen": "Comunidad",
                            "puntaje": 0.5833,
                            "palabras_compartidas": ["Docker", "Kubernetes"],
                        }
                    ],
                }
            ]
        }
    )


# ===========================================================================
# Analiticas del dashboard (Semana 4)
# ===========================================================================


class SegmentoConteo(BaseModel):
    """
    Un segmento generico de una distribucion (etiqueta + cantidad + porcentaje).

    Se reutiliza para categorias, origenes y franjas de confianza en vez de
    definir tres modelos identicos.
    """

    etiqueta: str = Field(..., description="Nombre del segmento.")
    cantidad: int = Field(..., ge=0, description="Contenidos en este segmento.")
    porcentaje: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Proporcion sobre el total, redondeada a un decimal.",
    )


class PuntoActividad(BaseModel):
    """Contenidos analizados en un dia concreto."""

    fecha: str = Field(..., description="Fecha en formato ISO (YYYY-MM-DD).")
    cantidad: int = Field(..., ge=0, description="Analisis realizados ese dia.")


class AnaliticasOutput(BaseModel):
    """
    Respuesta de `GET /analiticas` — panel completo del Dashboard.

    Superset de `GET /metricas`: incluye los mismos totales y agrega
    distribucion de confianza, distribucion por origen, actividad temporal y
    el motor de clasificacion activo. `/metricas` se mantiene sin cambios por
    compatibilidad con los clientes que ya lo consumen.
    """

    # --- Totales ------------------------------------------------------------
    total_contenidos: int = Field(..., ge=0, description="Contenidos analizados.")
    total_categorias: int = Field(..., ge=0, description="Categorias distintas detectadas.")
    total_palabras_clave: int = Field(
        ...,
        ge=0,
        description="Palabras clave unicas extraidas en todo el historial.",
    )
    confianza_promedio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Promedio de la confianza del modelo sobre todo el historial.",
    )

    # --- Distribuciones -----------------------------------------------------
    distribucion_categorias: List[SegmentoConteo] = Field(
        default_factory=list,
        description="Conteo por categoria, de mayor a menor.",
    )
    distribucion_confianza: List[SegmentoConteo] = Field(
        default_factory=list,
        description=(
            "Contenidos agrupados por franja de confianza: Alta (>=0.75), "
            "Media (0.50-0.74) y Baja (<0.50). Permite detectar de un vistazo "
            "cuanto contenido clasifico el modelo con poca certeza."
        ),
    )
    distribucion_origenes: List[SegmentoConteo] = Field(
        default_factory=list,
        description="Conteo por fuente del contenido (Alura, Oracle, etc.).",
    )
    top_palabras_clave: List["ConteoPalabraClave"] = Field(
        default_factory=list,
        description="Las 10 tecnologias mas frecuentes del historial.",
    )
    actividad_reciente: List[PuntoActividad] = Field(
        default_factory=list,
        description="Analisis por dia, de mas antiguo a mas reciente.",
    )

    # --- Estado del motor ---------------------------------------------------
    motor_activo: str = Field(
        ...,
        description="Motor de clasificacion en uso: modelo_ml_real | clasificador_reglas.",
    )
    modelo_cargado: str = Field(
        ...,
        description="Artefacto o version de reglas que produjo estas clasificaciones.",
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


# Resuelve las referencias adelantadas usadas en `MetricasOutput` y
# `AnaliticasOutput` (ambos citan `ConteoPalabraClave` antes de su definicion).
MetricasOutput.model_rebuild()
AnaliticasOutput.model_rebuild()