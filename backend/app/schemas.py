"""Schemas.py le dice a FastAPI cómo deben lucir los datos que entran y salen, y valida automáticamente que nadie nos mande basura."""
from typing import List, Optional
from pydantic import BaseModel, Field

# =====================================================================
# 1. Estructura de entrada (petición / request)
# =====================================================================

class ContenidoRequest(BaseModel):
    """
    Define los datos requeridos que el usuario o el Frontend debe enviar 
    para clasificar y enriquecer un recurso técnico.
    """
    titulo: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Título corto del recurso o documento técnico.",
        example="Introducción a Spring Boot y Java"
    )
    texto: str = Field(
        ...,
        min_length=10,
        description="Contenido extenso o cuerpo del texto que será analizado por el modelo de IA.",
        example="Aprende a estructurar una API REST robusta utilizando FastAPI, Pydantic y Python."
    )
    autor: Optional[str] = Field(
        default="Anónimo",
        max_length=80,
        description="Nombre del creador del contenido.",
        example="Ferney Suárez"
    )


# =====================================================================
# 2. Estructura de salida (respuesta / response)
# =====================================================================

class ContenidoResponse(BaseModel):
    """
    Define la estructura exacta que devolverá la API al cliente 
    tras procesar, clasificar y enriquecer el contenido.
    """
    categoria: str = Field(
        ...,
        description="Categoría asignada por el modelo de IA o el módulo de Fallback.",
        example="Backend"
    )
    probabilidad: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Grado de certeza/confianza de la clasificación (entre 0.0 y 1.0).",
        example=0.92
    )
    modo_procesamiento: str = Field(
        ...,
        description="Indica si la respuesta fue generada por el 'Modelo IA Principal' o por el 'Módulo Fallback (Reserva)'.",
        example="Modelo IA Principal"
    )
    palabras_clave: List[str] = Field(
        default_factory=list,
        description="Lista de etiquetas o conceptos clave extraídos del texto.",
        example=["FastAPI", "Python", "API REST"]
    )
    tiempo_lectura_minutos: int = Field(
        ...,
        ge=0,
        description="Tiempo estimado de lectura en minutos basado en el volumen de palabras.",
        example=2
    )


# =====================================================================
# 3. ESQUEMA DE ESTADO DEL SISTEMA (Health Check / Diagnóstico)
# =====================================================================

class HealthCheckResponse(BaseModel):
    """
    Esquema para monitorear la salud de la API y el estado de carga del modelo.
    """
    estado: str = Field(..., example="OK")
    modelo_cargado: bool = Field(..., example=True)
    mensaje: str = Field(..., example="Servicio ATHEN-IA operando correctamente.")