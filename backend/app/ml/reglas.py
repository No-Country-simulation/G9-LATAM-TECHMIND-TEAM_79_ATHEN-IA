"""
Clasificador por reglas (fallback incondicional).
===================================================

Motor de clasificacion por coincidencia de palabras clave contra la taxonomia
de `domain.taxonomia`. Es la unica pieza del sistema que `ml.registro` puede
construir siempre, sin condiciones — por eso NO se registra como proveedor
opcional (ver `ml/__init__.py`): es el piso de la cascada de fallback.

Determinista por diseno, para que QA pueda escribir aserciones estables.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List

from ..domain.protocols import MOTOR_REGLAS, ClasificadorBase
from ..domain.taxonomia import (
    TAXONOMIA,
    CATEGORIA_POR_DEFECTO,
    contiene,
    normalizar,
    resumir,
)

# Probabilidad asignada cuando no se detecta ninguna tecnologia conocida.
PROBABILIDAD_SIN_EVIDENCIA = 0.35


class ClasificadorReglas(ClasificadorBase):
    """
    Clasificador por coincidencia de palabras clave.

    Se usa mientras el modelo real no este disponible, y tambien si la carga
    o la inferencia del artefacto fallan (ver `ml.modelo.ClasificadorML`).
    """

    nombre = "reglas-keywords-v1"
    motor = MOTOR_REGLAS
    es_mock = True
    detalle = "taxonomia de palabras clave"

    # El titulo suele ser mas informativo que el cuerpo, asi que sus
    # coincidencias pesan mas al puntuar.
    PESO_TITULO = 3
    PESO_TEXTO = 1

    def clasificar(self, titulo: str, texto: str) -> dict:
        titulo_norm = normalizar(titulo)
        texto_norm = normalizar(texto)

        puntajes: Counter = Counter()
        keywords_por_categoria: Dict[str, List[str]] = {}

        for categoria, keywords in TAXONOMIA.items():
            encontradas: List[str] = []
            for etiqueta, patrones in keywords.items():
                golpe_titulo = any(contiene(titulo_norm, p) for p in patrones)
                golpe_texto = any(contiene(texto_norm, p) for p in patrones)
                if not (golpe_titulo or golpe_texto):
                    continue
                encontradas.append(etiqueta)
                puntajes[categoria] += (self.PESO_TITULO if golpe_titulo else 0) + (
                    self.PESO_TEXTO if golpe_texto else 0
                )
            if encontradas:
                keywords_por_categoria[categoria] = encontradas

        # Sin evidencia no se fuerza una categoria tecnica.
        if not puntajes:
            return {
                "categoria": CATEGORIA_POR_DEFECTO,
                "probabilidad": PROBABILIDAD_SIN_EVIDENCIA,
                "informacion_adicional": [],
                "resumen": resumir(texto),
                "categorias_relacionadas": [],
                "modelo": self.nombre,
            }

        ordenadas = puntajes.most_common()
        categoria, mejor_puntaje = ordenadas[0]
        total = sum(puntajes.values())

        # La confianza combina cuanto domina la categoria ganadora sobre el
        # resto (`share`) y cuanta evidencia absoluta hay (`evidencia`).
        share = mejor_puntaje / total
        evidencia = min(mejor_puntaje / 12, 1.0)
        probabilidad = round(min(0.55 + 0.35 * share + 0.10 * evidencia, 0.99), 2)

        return {
            "categoria": categoria,
            "probabilidad": probabilidad,
            "informacion_adicional": keywords_por_categoria.get(categoria, [])[:8],
            "resumen": resumir(texto),
            "categorias_relacionadas": [c for c, _ in ordenadas[1:4]],
            "modelo": self.nombre,
        }
