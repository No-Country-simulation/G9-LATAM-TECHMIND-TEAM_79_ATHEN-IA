"""
Capa de aplicacion (casos de uso) de AthenIA.
================================================

Tras el refactor SOLID de la Semana 3, este modulo dejo de ser un contenedor
de 929 lineas con seis responsabilidades distintas (SRP). Hoy es una capa
delgada de orquestacion que:

  1. Compone las abstracciones del dominio con sus implementaciones
     concretas (esto lo convierte en la "raiz de composicion" del backend).
  2. Expone los casos de uso que las rutas invocan: `analizar_y_guardar`,
     `calcular_metricas`, `sembrar_demo`.
  3. Mantiene el estado activo del proceso: que clasificador y que
     repositorio estan en uso ahora mismo.

El resto de la logica vive en capas dedicadas:

    domain/         Abstracciones (`Clasificador`, `RepositorioContenidos`)
                    y reglas de negocio puras (taxonomia, normalizacion).
    ml/             Motores de clasificacion + el registro que decide cual
                    esta activo (extension point del OCP).
    repositories/   Implementaciones de persistencia.
    routers/        Endpoints HTTP, delegando en este modulo via `Depends`
                    (ver `dependencies.py` — ahi vive la inversion real).

Este archivo NO define ninguna clase de clasificador ni de repositorio: solo
las instancia e importa. Quien quiera el detalle de "como" clasifica el
modelo real debe ir a `ml/modelo.py`; "como" persiste el historial, a
`repositories/memoria.py`.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import List, Optional

from .config import settings
from .domain.protocols import Clasificador, RepositorioContenidos
from .ml import registro as registro_ml
from .ml.adaptador import AdaptadorModelo
from .ml.modelo import ClasificadorML
from .ml.reglas import ClasificadorReglas
from .repositories.memoria import RepositorioMemoria

logger = logging.getLogger("athenia.services")

# Re-exportados por compatibilidad: codigo y pruebas que importaban estas
# clases directamente desde `services` (antes del refactor) siguen funcionando
# sin cambios. Los tipos "de verdad" viven en `ml/`.
__all__ = [
    "AdaptadorModelo",
    "ClasificadorML",
    "ClasificadorReglas",
    "clasificador",
    "repositorio",
    "recargar_clasificador",
    "analizar_y_guardar",
    "calcular_metricas",
    "calcular_analiticas",
    "sembrar_demo",
]


# ===========================================================================
# Raiz de composicion: que implementaciones estan activas ahora mismo
# ===========================================================================
#
# `clasificador` se resuelve a traves de `ml.registro`, que es el UNICO lugar
# que decide "modelo real vs reglas" (ver `ml/registro.py`). Este modulo no
# contiene ningun if/else de motores.
#
# `ml/__init__.py` reexporta la instancia `registro` (un `RegistroProveedores`
# ya poblado con los proveedores conocidos), asi que `registro_ml` aqui ES esa
# instancia — no el submodulo `ml/registro.py`.

clasificador: Clasificador = registro_ml.resolver()
repositorio: RepositorioContenidos = RepositorioMemoria()


def recargar_clasificador() -> Clasificador:
    """
    Vuelve a resolver el motor activo y lo publica en el modulo.

    Permite integrar un artefacto nuevo sin reiniciar el proceso, y es lo que
    usan las pruebas para alternar entre modelo real y fallback.
    """
    global clasificador
    clasificador = registro_ml.resolver()
    return clasificador


# ===========================================================================
# Casos de uso
# ===========================================================================


def analizar_y_guardar(
    entrada: dict,
    motor: Optional[Clasificador] = None,
    historial: Optional[RepositorioContenidos] = None,
) -> dict:
    """
    Caso de uso principal: clasifica el contenido y lo persiste en el historial.

    Es lo que ejecuta `POST /contenido` (via `routers/contenido.py`, que pasa
    las instancias resueltas por `Depends`) y tambien `sembrar_demo()` al
    arrancar (que usa las instancias activas del modulo por defecto). Ninguna
    de las dos rutas de llamada importa `ClasificadorML` ni `RepositorioMemoria`
    directamente: ambas trabajan contra los `Protocol` del dominio.
    """
    motor = motor or clasificador
    historial = historial or repositorio

    resultado = motor.clasificar(entrada["titulo"], entrada["texto"])

    return historial.agregar(
        {
            **resultado,
            "titulo": entrada["titulo"],
            "texto": entrada["texto"],
            "origen": entrada.get("origen"),
            "url": entrada.get("url"),
        }
    )


def calcular_metricas(items: List[dict]) -> dict:
    """Agrega el historial en los numeros que muestra el Dashboard."""
    if not items:
        return {
            "total_cursos": 0,
            "total_categorias": 0,
            "total_palabras_clave": 0,
            "confianza_promedio": 0.0,
            "distribucion": [],
            "top_palabras_clave": [],
        }

    total = len(items)
    por_categoria = Counter(i["categoria"] for i in items)
    palabras = Counter(p for i in items for p in i.get("informacion_adicional", []))

    distribucion = [
        {
            "categoria": categoria,
            "cantidad": cantidad,
            "porcentaje": round(cantidad / total * 100),
        }
        for categoria, cantidad in por_categoria.most_common()
    ]

    return {
        "total_cursos": total,
        "total_categorias": len(por_categoria),
        "total_palabras_clave": len(palabras),
        "confianza_promedio": round(sum(i["probabilidad"] for i in items) / total, 2),
        "distribucion": distribucion,
        "top_palabras_clave": [
            {"palabra": palabra, "cantidad": cantidad}
            for palabra, cantidad in palabras.most_common(10)
        ],
    }


# --- Analiticas del dashboard (Semana 4) -----------------------------------

#: Franjas de confianza, evaluadas en orden. La primera cuyo umbral se cumple
#: gana, asi que deben ir de mayor a menor.
FRANJAS_CONFIANZA = (
    ("Alta (≥75%)", 0.75),
    ("Media (50-74%)", 0.50),
    ("Baja (<50%)", 0.0),
)

ORIGEN_NO_ESPECIFICADO = "Sin origen"


def _segmentos(conteo: Counter, total: int) -> List[dict]:
    """Convierte un `Counter` en segmentos con porcentaje, de mayor a menor."""
    return [
        {
            "etiqueta": etiqueta,
            "cantidad": cantidad,
            "porcentaje": round(cantidad / total * 100, 1),
        }
        for etiqueta, cantidad in conteo.most_common()
    ]


def _franja_de_confianza(probabilidad: float) -> str:
    """Etiqueta de la franja a la que pertenece una probabilidad."""
    for etiqueta, minimo in FRANJAS_CONFIANZA:
        if probabilidad >= minimo:
            return etiqueta
    return FRANJAS_CONFIANZA[-1][0]


def calcular_analiticas(items: List[dict], motor: Clasificador) -> dict:
    """
    Agrega el historial en el panel completo de analiticas (`GET /analiticas`).

    Superset de `calcular_metricas`: ademas de los totales, produce la
    distribucion de confianza (para detectar contenido clasificado con poca
    certeza), la distribucion por origen y la actividad por dia.

    Recibe `motor` en vez de leerlo del modulo para no depender del estado
    global: la ruta le pasa el clasificador resuelto por `Depends`, y las
    pruebas pueden inyectar un doble.
    """
    if not items:
        return {
            "total_contenidos": 0,
            "total_categorias": 0,
            "total_palabras_clave": 0,
            "confianza_promedio": 0.0,
            "distribucion_categorias": [],
            "distribucion_confianza": [],
            "distribucion_origenes": [],
            "top_palabras_clave": [],
            "actividad_reciente": [],
            "motor_activo": motor.motor,
            "modelo_cargado": motor.nombre,
        }

    total = len(items)
    por_categoria = Counter(i["categoria"] for i in items)
    palabras = Counter(p for i in items for p in i.get("informacion_adicional", []))
    por_confianza = Counter(_franja_de_confianza(i["probabilidad"]) for i in items)
    por_origen = Counter(i.get("origen") or ORIGEN_NO_ESPECIFICADO for i in items)

    # Actividad por dia. `creado_en` es un datetime con tz UTC; se agrupa por
    # fecha ISO y se ordena cronologicamente para que el grafico de linea del
    # frontend no tenga que reordenar nada.
    por_dia: Counter = Counter()
    for item in items:
        creado = item.get("creado_en")
        if creado is not None:
            por_dia[creado.date().isoformat()] += 1

    return {
        "total_contenidos": total,
        "total_categorias": len(por_categoria),
        "total_palabras_clave": len(palabras),
        "confianza_promedio": round(sum(i["probabilidad"] for i in items) / total, 2),
        "distribucion_categorias": _segmentos(por_categoria, total),
        # Se ordena por la definicion de FRANJAS_CONFIANZA (Alta, Media, Baja)
        # y no por cantidad: una leyenda que cambia de orden segun los datos
        # es confusa de leer en el dashboard.
        "distribucion_confianza": [
            {
                "etiqueta": etiqueta,
                "cantidad": por_confianza.get(etiqueta, 0),
                "porcentaje": round(por_confianza.get(etiqueta, 0) / total * 100, 1),
            }
            for etiqueta, _ in FRANJAS_CONFIANZA
        ],
        "distribucion_origenes": _segmentos(por_origen, total),
        "top_palabras_clave": [
            {"palabra": palabra, "cantidad": cantidad}
            for palabra, cantidad in palabras.most_common(10)
        ],
        "actividad_reciente": [
            {"fecha": fecha, "cantidad": cantidad} for fecha, cantidad in sorted(por_dia.items())
        ],
        "motor_activo": motor.motor,
        "modelo_cargado": motor.nombre,
    }


# ===========================================================================
# Datos de demo
# ===========================================================================
# Contenido de ejemplo: da vida al Dashboard y a la busqueda en la primera
# carga, antes de que el usuario analice nada. Se desactiva con
# ATHENIA_SEED_DEMO=false (las pruebas lo hacen para aislarse).

CONTENIDO_DEMO: List[dict] = [
    {
        "titulo": "Introduccion a Spring Boot",
        "texto": (
            "Curso practico para construir APIs REST seguras con Java y Spring Boot, "
            "aplicando Spring Security, Spring Data JPA y autenticacion con JWT."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "Docker para Principiantes",
        "texto": (
            "Conceptos basicos de contenedores e imagenes, escritura de un Dockerfile "
            "y despliegue de aplicaciones sobre Linux."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "Machine Learning con Python",
        "texto": (
            "Entrenamiento de modelos de clasificacion con Scikit-Learn y Pandas, "
            "aplicando tecnicas de NLP y vectorizacion TF-IDF."
        ),
        "origen": "Oracle Next Education",
    },
    {
        "titulo": "React desde Cero",
        "texto": (
            "Componentes, hooks y manejo de estado en React, con estilos en "
            "Tailwind CSS para lograr una interfaz responsive."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "Despliegue de Apps en Oracle Cloud",
        "texto": (
            "Uso de OCI: Compute, Object Storage y Autonomous Database, con "
            "balanceo de carga y alta disponibilidad."
        ),
        "origen": "Oracle",
    },
    {
        "titulo": "Microservicios con Spring Cloud",
        "texto": (
            "Arquitectura distribuida con microservicios, service discovery, "
            "API Gateway y tolerancia a fallos sobre Spring Boot."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "SQL y Modelado de Datos con Oracle",
        "texto": (
            "Consultas avanzadas con SQL, uso de join, normalizacion y modelado "
            "de datos sobre Oracle Database."
        ),
        "origen": "Oracle",
    },
    {
        "titulo": "Kubernetes en Produccion",
        "texto": (
            "Orquestacion de contenedores con Kubernetes, despliegues, escalado "
            "automatico, monitoreo y observabilidad."
        ),
        "origen": "Comunidad",
    },
]


def sembrar_demo(forzar: bool = False) -> int:
    """
    Precarga el historial con contenido de ejemplo.

    Se llama al arrancar la app. Devuelve cuantos items se insertaron; 0 si la
    semilla esta desactivada o el historial ya tenia datos.
    """
    if not (settings.SEED_DEMO or forzar):
        return 0
    if repositorio.total() > 0:
        return 0

    for demo in CONTENIDO_DEMO:
        analizar_y_guardar(demo)

    logger.info("Historial precargado con %d contenidos de demo.", len(CONTENIDO_DEMO))
    return len(CONTENIDO_DEMO)
