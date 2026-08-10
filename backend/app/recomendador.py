"""
Motor de recomendaciones de contenido relacionado (Semana 4).
===============================================================

Implementa `domain.protocols.MotorRecomendaciones` puntuando cada contenido
del historial contra el contenido de referencia con las metricas puras de
`domain.similitud`.

Por que un modulo aparte y no dentro de `services.py`
------------------------------------------------------
SRP: recomendar es una razon de cambio distinta a "clasificar" o "persistir".
Si manana el equipo ajusta los pesos, cambia a similitud coseno o mete
embeddings, el cambio queda contenido aqui.

Por que no hay un registro de proveedores como en `ml/`
--------------------------------------------------------
`ml/registro.py` existe porque el motor de ML **puede no estar disponible**
(sin artefacto, pickle corrupto, version incompatible) y hay que degradar a un
fallback en tiempo de arranque. Recomendar no tiene esa incertidumbre: siempre
se puede calcular sobre el historial en memoria. Sustituir esta implementacion
por una de embeddings en la Semana 5 es cambiar una linea en
`dependencies.get_recomendador()`, sin necesidad de cascada de fallback.
"""

from __future__ import annotations

import logging
from typing import List

from .domain.similitud import es_relevante, palabras_compartidas, puntuar_similitud

logger = logging.getLogger("athenia.recomendador")

# Tope defensivo: aunque la ruta valide `limite`, el motor nunca devuelve mas.
LIMITE_MAXIMO = 20


class RecomendadorPorKeywords:
    """
    Recomienda por similitud de palabras clave + coincidencia de categoria.

    Es O(n) sobre el historial, que con el tope de `ATHENIA_MAX_HISTORIAL`
    (500 por defecto) es trivial. Si el historial creciera a decenas de miles
    habria que indexar, pero eso es un problema de la Semana 5+ junto con la
    migracion a Oracle Database.
    """

    nombre = "keywords-jaccard-v1"

    def recomendar(
        self,
        contenido: dict,
        candidatos: List[dict],
        limite: int = 5,
    ) -> List[dict]:
        """Ver `domain.protocols.MotorRecomendaciones.recomendar`."""
        limite = max(1, min(limite, LIMITE_MAXIMO))

        palabras_origen = contenido.get("informacion_adicional") or []
        categoria_origen = contenido.get("categoria") or ""
        id_origen = contenido.get("id")

        recomendaciones: List[dict] = []

        for candidato in candidatos:
            # Nunca recomendar el propio contenido consultado.
            if candidato.get("id") == id_origen:
                continue

            palabras_candidato = candidato.get("informacion_adicional") or []
            puntaje = puntuar_similitud(
                palabras_origen,
                categoria_origen,
                palabras_candidato,
                candidato.get("categoria") or "",
            )

            if not es_relevante(puntaje):
                continue

            recomendaciones.append(
                {
                    "id": candidato["id"],
                    "titulo": candidato.get("titulo", ""),
                    "categoria": candidato.get("categoria", ""),
                    "probabilidad": candidato.get("probabilidad", 0.0),
                    "resumen": candidato.get("resumen", ""),
                    "origen": candidato.get("origen"),
                    "puntaje": puntaje,
                    "palabras_compartidas": palabras_compartidas(
                        palabras_origen, palabras_candidato
                    ),
                }
            )

        # Orden estable: por puntaje descendente y, a igualdad, por id
        # descendente (lo mas reciente primero). Sin el segundo criterio, dos
        # contenidos con el mismo puntaje podrian alternar de posicion entre
        # llamadas y romper las aserciones de QA.
        recomendaciones.sort(key=lambda r: (-r["puntaje"], -r["id"]))

        return recomendaciones[:limite]
