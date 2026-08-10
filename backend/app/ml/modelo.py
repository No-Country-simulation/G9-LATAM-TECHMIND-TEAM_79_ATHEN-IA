"""
Motor de inferencia real: envuelve el artefacto entrenado por Data Science.
=============================================================================

`ClasificadorML` implementa `domain.protocols.Clasificador` sobre un
`AdaptadorModelo` ya cargado y verificado (ver `ml/carga.py`). No sabe leer
archivos ni deserializar: solo sabe convertir una prediccion del modelo en la
forma que la API expone.

Resiliencia: si `predict`/`predict_proba` lanzan en tiempo de ejecucion (texto
inesperado, incompatibilidad de versiones de sklearn, vectorizador
desalineado), `clasificar()` responde con el clasificador por reglas en lugar
de propagar el error. La API nunca devuelve 500 por culpa del modelo.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..domain.protocols import MOTOR_ML, ClasificadorBase
from ..domain.taxonomia import extraer_palabras_clave, resumir
from .adaptador import AdaptadorModelo
from .reglas import ClasificadorReglas

logger = logging.getLogger("athenia.ml.modelo")

# Probabilidad reportada cuando el modelo real no expone `predict_proba`.
PROBABILIDAD_SIN_PROBA = 0.75

# Cuantas categorias alternativas se reportan y con que probabilidad minima.
# Por debajo del umbral la alternativa es ruido y solo confunde al usuario.
MAX_CATEGORIAS_RELACIONADAS = 3
UMBRAL_CATEGORIA_RELACIONADA = 0.05


class ClasificadorML(ClasificadorBase):
    """Adapta un `AdaptadorModelo` ya verificado a la interfaz `Clasificador`."""

    motor = MOTOR_ML
    es_mock = False

    def __init__(self, adaptador: AdaptadorModelo, ruta: Path) -> None:
        self._adaptador = adaptador
        self._fallback = ClasificadorReglas()
        self.ruta = ruta
        self.nombre = ruta.name
        self.detalle = adaptador.describir()

    @staticmethod
    def preparar_entrada(titulo: str, texto: str) -> str:
        """
        Construye el texto que recibe el modelo.

        Debe coincidir con la concatenacion usada durante el entrenamiento
        (ver `backend/models/README.md`).
        """
        return f"{titulo}. {texto}".strip()

    def clasificar(self, titulo: str, texto: str) -> dict:
        entrada = self.preparar_entrada(titulo, texto)

        try:
            proba = self._adaptador.predict_proba([entrada])
            clases = self._adaptador.clases

            if proba is not None and clases:
                # Con probabilidades se obtiene todo de una vez: la clase
                # ganadora, su confianza y las alternativas mas probables.
                ranking = sorted(zip(clases, proba[0]), key=lambda par: par[1], reverse=True)
                categoria = str(ranking[0][0])
                probabilidad = round(float(ranking[0][1]), 2)
                relacionadas = [
                    str(clase)
                    for clase, p in ranking[1 : 1 + MAX_CATEGORIAS_RELACIONADAS]
                    if p >= UMBRAL_CATEGORIA_RELACIONADA
                ]
            else:
                categoria = str(self._adaptador.predict([entrada])[0])
                probabilidad = PROBABILIDAD_SIN_PROBA
                relacionadas = []
        except Exception:  # noqa: BLE001 - un fallo de inferencia no tumba la API
            logger.exception(
                "Fallo la inferencia de %s. Se responde con el clasificador por reglas.",
                self.nombre,
            )
            resultado = self._fallback.clasificar(titulo, texto)
            resultado["modelo"] = f"{self._fallback.nombre} (fallback en inferencia)"
            return resultado

        return {
            "categoria": categoria,
            "probabilidad": probabilidad,
            # Las palabras clave siguen saliendo de la taxonomia: el modelo
            # entrega la categoria, no las tecnologias presentes en el texto.
            "informacion_adicional": extraer_palabras_clave(titulo, texto, categoria),
            "resumen": resumir(texto),
            # Salen del propio modelo, no de las reglas: mezclar dos taxonomias
            # distintas en una misma respuesta confunde al usuario.
            "categorias_relacionadas": relacionadas,
            "modelo": self.nombre,
        }

    def categorias(self) -> list[str]:
        """Clases reales del modelo; si no las expone, cae al catalogo local."""
        return self._adaptador.clases or super().categorias()
