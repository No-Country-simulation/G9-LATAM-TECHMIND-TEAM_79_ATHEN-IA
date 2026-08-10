"""
Metricas de similitud entre contenidos (dominio puro).
========================================================

Funciones sin estado ni I/O que puntuan que tan parecidos son dos contenidos
ya analizados. Viven en `domain/` porque son reglas de negocio: definen que
significa "parecido" para AthenIA, independientemente de donde se guarden los
contenidos o de que motor los haya clasificado.

`recomendador.RecomendadorPorKeywords` las consume; ninguna de estas
funciones sabe que existe un repositorio, un endpoint HTTP ni scikit-learn.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Set

from .taxonomia import normalizar

# --- Pesos del puntaje combinado -------------------------------------------
# Las palabras clave son la senal principal: dos cursos que comparten
# "Docker" y "Kubernetes" son mas parecidos entre si que dos cursos que solo
# coinciden en pertenecer a la misma categoria amplia.
PESO_PALABRAS_CLAVE = 0.75
PESO_CATEGORIA = 0.25

# Por debajo de este puntaje la relacion es ruido y no vale la pena mostrarla.
UMBRAL_MINIMO_RELEVANCIA = 0.10


def _conjunto_normalizado(palabras: Iterable[str]) -> Set[str]:
    """
    Normaliza una coleccion de palabras clave a un conjunto comparable.

    Sin esto, "Spring Boot" y "spring boot" contarian como tecnologias
    distintas y hundirian el puntaje de dos contenidos que en realidad hablan
    de lo mismo.
    """
    return {normalizar(p) for p in palabras if p and p.strip()}


def jaccard(primero: Iterable[str], segundo: Iterable[str]) -> float:
    """
    Indice de Jaccard entre dos colecciones de palabras clave.

    Es |interseccion| / |union|: 1.0 si comparten exactamente las mismas
    tecnologias, 0.0 si no comparten ninguna.

    Se elige Jaccard sobre "cantidad de coincidencias" a secas porque
    normaliza por tamano: un contenido con 8 palabras clave no debe parecer
    mas relacionado con todo el catalogo solo por tener mas terminos.
    """
    conjunto_a = _conjunto_normalizado(primero)
    conjunto_b = _conjunto_normalizado(segundo)

    if not conjunto_a or not conjunto_b:
        return 0.0

    interseccion = conjunto_a & conjunto_b
    union = conjunto_a | conjunto_b

    return len(interseccion) / len(union)


def palabras_compartidas(primero: Sequence[str], segundo: Iterable[str]) -> List[str]:
    """
    Palabras clave presentes en ambos contenidos, con el casing del primero.

    Se devuelven para que la UI pueda explicar *por que* se recomendo algo
    ("porque ambos hablan de Docker y Kubernetes") en vez de mostrar un
    puntaje opaco.
    """
    objetivo = _conjunto_normalizado(segundo)
    vistas: Set[str] = set()
    compartidas: List[str] = []

    for palabra in primero:
        clave = normalizar(palabra)
        if clave in objetivo and clave not in vistas:
            vistas.add(clave)
            compartidas.append(palabra)

    return compartidas


def puntuar_similitud(
    palabras_origen: Iterable[str],
    categoria_origen: str,
    palabras_candidato: Iterable[str],
    categoria_candidato: str,
) -> float:
    """
    Puntaje combinado de similitud entre dos contenidos, en el rango 0.0-1.0.

    Combina dos senales:
      - **Palabras clave** (peso 0.75): indice de Jaccard sobre las tecnologias.
      - **Categoria** (peso 0.25): 1.0 si comparten categoria, 0.0 si no.

    Que la categoria pese algo permite recomendar contenido relacionado aunque
    no compartan ninguna tecnologia concreta — util cuando el clasificador
    extrajo pocas palabras clave. Que pese poco evita que la categoria por si
    sola inunde las recomendaciones con todo el catalogo.
    """
    similitud_palabras = jaccard(palabras_origen, palabras_candidato)
    misma_categoria = (
        1.0 if normalizar(categoria_origen) == normalizar(categoria_candidato) else 0.0
    )

    puntaje = PESO_PALABRAS_CLAVE * similitud_palabras + PESO_CATEGORIA * misma_categoria

    return round(min(puntaje, 1.0), 4)


def es_relevante(puntaje: float) -> bool:
    """True si el puntaje supera el umbral minimo para mostrarse al usuario."""
    return puntaje >= UMBRAL_MINIMO_RELEVANCIA
