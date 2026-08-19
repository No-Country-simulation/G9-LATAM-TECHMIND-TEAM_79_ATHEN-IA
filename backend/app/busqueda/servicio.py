"""
Caso de uso de la busqueda de cursos.
======================================

Traduce la salida cruda del `AlmacenVectorial` a la respuesta que consume el
Dashboard: convierte distancias a puntajes, descarta lo irrelevante y arma el
contrato. Depende del `Protocol`, no de ChromaDB, asi que se puede probar por
completo con un doble en memoria.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ..domain.protocols import AlmacenVectorial

logger = logging.getLogger("athenia.busqueda.servicio")

#: Umbral por defecto de relevancia (similitud coseno en [0, 1]).
#:
#: Calibrado sobre el modelo `paraphrase-multilingual-MiniLM-L12-v2`, que es
#: multilingue y por tanto genera similitudes altas incluso entre textos poco
#: relacionados. Con 0.35 se corta la cola de "cursos extranos" sin perder
#: coincidencias validas entre espanol e ingles (el catalogo esta en ingles y
#: las consultas del Dashboard llegan en espanol).
UMBRAL_RELEVANCIA = 0.35

#: Cuantos candidatos pedir de mas al indice antes de filtrar. Sin este margen,
#: una consulta con `limite=10` donde 6 candidatos caen bajo el umbral
#: devolveria 4 resultados; pidiendo el triple se rellena el hueco.
FACTOR_SOBREMUESTREO = 3

#: Tope duro de candidatos a pedir, para no forzar al indice HNSW a recorrer
#: media base cuando alguien pide `limite=50`.
MAXIMO_CANDIDATOS = 200


def distancia_a_puntaje(distancia: float) -> float:
    """
    Convierte una distancia coseno de Chroma en similitud en [0, 1].

    Chroma devuelve `1 - similitud_coseno` cuando la coleccion se creo con
    `hnsw:space="cosine"`, asi que la inversa es directa. El rango teorico de
    la distancia es [0, 2] (vectores opuestos), pero los embeddings de
    lenguaje rara vez son opuestos; se acota a [0, 1] porque un puntaje
    negativo no tiene lectura posible en la interfaz.

    Nota: si el indice se construyo con la metrica L2 por defecto —el fallo de
    la version original— la distancia no esta acotada y esta conversion
    saturaria en 0.0 casi siempre. Por eso `AlmacenChroma` verifica la metrica
    al abrir y lo registra como ERROR.
    """
    return max(0.0, min(1.0, 1.0 - float(distancia)))


class BuscadorCursos:
    """
    Busqueda semantica sobre el catalogo de cursos.

    Es sin estado (solo consulta el almacen que recibe), asi que una unica
    instancia se puede compartir entre peticiones.
    """

    def __init__(
        self,
        almacen: AlmacenVectorial,
        umbral: float = UMBRAL_RELEVANCIA,
    ):
        self._almacen = almacen
        self._umbral = umbral

    @property
    def disponible(self) -> bool:
        return self._almacen.esta_disponible()

    @property
    def total_indexado(self) -> int:
        return self._almacen.total()

    def buscar(
        self,
        consulta: str,
        limite: int = 10,
        min_score: Optional[float] = None,
    ) -> List[dict]:
        """
        Devuelve los cursos relevantes para `consulta`, del mas al menos afin.

        - `limite`    maximo de resultados a devolver.
        - `min_score` umbral de similitud; por debajo se descarta. `None` usa
          `UMBRAL_RELEVANCIA`. Con `0.0` no se filtra nada (util para depurar
          por que una consulta no devuelve resultados).

        Una consulta vacia o de solo espacios devuelve `[]` sin tocar el
        indice: vectorizar una cadena vacia produce un vector arbitrario que
        casaria con cursos al azar — otra de las fuentes de resultados
        incoherentes.
        """
        consulta = (consulta or "").strip()
        if not consulta:
            return []

        umbral = self._umbral if min_score is None else max(0.0, min(1.0, float(min_score)))
        limite = max(1, int(limite))

        candidatos = self._almacen.consultar(
            texto=consulta,
            limite=min(limite * FACTOR_SOBREMUESTREO, MAXIMO_CANDIDATOS),
        )

        relevantes = []
        titulos_vistos: set[str] = set()
        for posicion, candidato in enumerate(candidatos):
            puntaje = distancia_a_puntaje(candidato.get("distancia", 1.0))
            if puntaje < umbral:
                # Los candidatos vienen ordenados por distancia creciente: en
                # cuanto uno cae bajo el umbral, los siguientes tambien.
                break

            resultado = self._formatear(candidato, puntaje, posicion)

            # Segunda barrera contra duplicados, ademas de la del indexado.
            # `preparar_lote` deduplica por texto identico, pero el catalogo
            # tiene el mismo curso publicado en varias plataformas con textos
            # ligeramente distintos. Sin esto, una consulta puede gastar sus
            # huecos repitiendo el mismo titulo. Se aplica aqui y no en el
            # indice porque el indice no debe perder esas variantes: pueden
            # tener URLs distintas y ser utiles con otro `limite`.
            titulo = resultado["title"].strip().lower()
            if titulo in titulos_vistos:
                continue
            titulos_vistos.add(titulo)

            relevantes.append(resultado)
            if len(relevantes) >= limite:
                break

        if candidatos and not relevantes:
            logger.info(
                "Sin resultados sobre el umbral %.2f para '%s' (mejor puntaje: %.3f).",
                umbral,
                consulta,
                distancia_a_puntaje(candidatos[0].get("distancia", 1.0)),
            )

        return relevantes

    @staticmethod
    def _formatear(candidato: dict, puntaje: float, posicion: int) -> dict:
        """
        Arma el contrato que consume el Dashboard.

        Los metadatos se leen con `.get(..., defecto)` porque un indice
        construido con una version anterior del script puede no traer todas
        las claves; una `KeyError` aqui tumbaria la busqueda entera.
        """
        meta = candidato.get("metadatos") or {}
        return {
            "id": candidato.get("id", f"resultado_{posicion}"),
            "title": meta.get("titulo") or "Sin titulo",
            "description": meta.get("descripcion") or "",
            "category": meta.get("categoria") or "Otras Areas",
            "url": meta.get("url") or "",
            "site": meta.get("sitio") or "Desconocido",
            # Redondeado a 4 decimales: la precision extra de un float64 no
            # aporta nada en la interfaz y ensucia el JSON.
            "match_score": round(puntaje, 4),
        }
