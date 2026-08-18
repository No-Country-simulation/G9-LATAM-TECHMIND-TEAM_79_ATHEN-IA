"""
Niveles de confianza del clasificador (dominio puro).
=======================================================

Traduce la probabilidad cruda del modelo (0.0-1.0) a una franja legible:
Alta, Media o Baja.

Por que existe este modulo
--------------------------
Las bandas se usaban solo en `GET /analiticas` para agrupar el historial. Pero
la respuesta de `POST /contenido` devolvia la probabilidad "pelada", y la UI la
pintaba siempre igual: una barra de color con un porcentaje. Un resultado de
0.37 —que en la practica significa "el modelo no tiene ni idea"— se presentaba
con la misma autoridad visual que uno de 0.93.

Centralizar las bandas aqui permite que el panel de analiticas y la respuesta
de cada analisis hablen exactamente el mismo idioma, sin duplicar umbrales.

Sobre los umbrales
------------------
Se eligieron midiendo el modelo real (`clasificador_cursos.pkl`) contra
entradas conocidas:

    ruido / texto sin senal .......... 0.37   <- suelo del modelo
    contenido tecnico reconocible .... 0.55 - 0.93

El corte en 0.50 separa el suelo del rango util. NO pretende detectar
"contenido no tecnico": un texto sin senal puede recibir una probabilidad alta
si el vocabulario se parece por casualidad a una clase. Lo que este modulo
reporta es **la certeza declarada por el propio modelo**, ni mas ni menos.
"""

from __future__ import annotations

from typing import Literal, Tuple

NivelConfianza = Literal["alta", "media", "baja"]

#: Franjas evaluadas en orden: la primera cuyo minimo se cumple gana.
#: (nivel, etiqueta para la UI, probabilidad minima)
FRANJAS_CONFIANZA: Tuple[Tuple[str, str, float], ...] = (
    ("alta", "Alta (≥75%)", 0.75),
    ("media", "Media (50-74%)", 0.50),
    ("baja", "Baja (<50%)", 0.0),
)

#: Por debajo de este valor el resultado se considera poco fiable y la interfaz
#: debe advertirlo en vez de presentarlo como una clasificacion firme.
UMBRAL_CONFIANZA_BAJA = 0.50


def nivel_de_confianza(probabilidad: float) -> NivelConfianza:
    """Devuelve `"alta"`, `"media"` o `"baja"` para una probabilidad 0.0-1.0."""
    for nivel, _etiqueta, minimo in FRANJAS_CONFIANZA:
        if probabilidad >= minimo:
            return nivel  # type: ignore[return-value]
    return "baja"


def etiqueta_de_franja(probabilidad: float) -> str:
    """Etiqueta legible de la franja, la que muestra el panel de analiticas."""
    for _nivel, etiqueta, minimo in FRANJAS_CONFIANZA:
        if probabilidad >= minimo:
            return etiqueta
    return FRANJAS_CONFIANZA[-1][1]


def etiquetas_ordenadas() -> list[str]:
    """
    Etiquetas en orden fijo Alta -> Media -> Baja.

    El panel las pinta en este orden y no por cantidad: una leyenda que se
    reordena segun los datos es confusa de leer.
    """
    return [etiqueta for _nivel, etiqueta, _minimo in FRANJAS_CONFIANZA]
