"""
Suite de pruebas de QA - Recomendaciones de contenido relacionado (Semana 4)
============================================================================

Cubre `GET /contenidos/{id}/recomendaciones` y las metricas de similitud puras
sobre las que se apoya (`domain.similitud`).

    CP-200 .. CP-206   Unidad: metricas de similitud (sin HTTP)
    CP-210 .. CP-218   Integracion: el endpoint completo
    CP-220 .. CP-221   Arquitectura: el motor es sustituible (OCP / DIP)

Ejecutar solo esta suite:

    pytest backend/tests/test_recomendaciones.py -v
"""

import pytest

from app.domain.similitud import (
    UMBRAL_MINIMO_RELEVANCIA,
    es_relevante,
    jaccard,
    palabras_compartidas,
    puntuar_similitud,
)
from app.recomendador import RecomendadorPorKeywords


# ===========================================================================
# CP-200 .. CP-206  |  Metricas de similitud (unidad, sin HTTP)
# ===========================================================================


def test_jaccard_conjuntos_identicos_da_uno():
    """CP-200: dos contenidos con las mismas tecnologias tienen similitud 1.0."""
    assert jaccard(["Docker", "Kubernetes"], ["Docker", "Kubernetes"]) == 1.0


def test_jaccard_sin_coincidencias_da_cero():
    """CP-201: sin tecnologias en comun la similitud es 0.0."""
    assert jaccard(["Docker"], ["Pandas"]) == 0.0


def test_jaccard_es_insensible_a_mayusculas_y_acentos():
    """
    CP-202: "Analitica" y "analítica" son la misma tecnologia.

    Sin normalizar, dos contenidos que hablan de lo mismo con distinto casing
    puntuarian 0.0 y nunca se recomendarian entre si.
    """
    assert jaccard(["Analítica", "PYTHON"], ["analitica", "python"]) == 1.0


def test_jaccard_normaliza_por_tamano():
    """
    CP-203: compartir 1 de 2 terminos pesa mas que compartir 1 de 5.

    Es la razon de usar Jaccard y no un conteo bruto de coincidencias: un
    contenido con muchas palabras clave no debe parecer relacionado con todo.
    """
    pocos = jaccard(["Docker", "Linux"], ["Docker", "Nginx"])
    muchos = jaccard(
        ["Docker", "Linux", "Java", "SQL", "React"],
        ["Docker", "Nginx", "Python", "AWS", "Vue"],
    )
    assert pocos > muchos


def test_jaccard_con_lista_vacia_da_cero():
    """CP-204: un contenido sin palabras clave no rompe el calculo."""
    assert jaccard([], ["Docker"]) == 0.0
    assert jaccard(["Docker"], []) == 0.0
    assert jaccard([], []) == 0.0


def test_puntaje_combina_palabras_clave_y_categoria():
    """
    CP-205: misma categoria y mismas palabras clave da el puntaje maximo;
    misma categoria sin palabras compartidas da solo el peso de categoria.
    """
    maximo = puntuar_similitud(["Docker"], "DevOps", ["Docker"], "DevOps")
    solo_categoria = puntuar_similitud(["Docker"], "DevOps", ["Pandas"], "DevOps")
    nada = puntuar_similitud(["Docker"], "DevOps", ["Pandas"], "Data Science")

    assert maximo == 1.0
    assert solo_categoria == pytest.approx(0.25)
    assert nada == 0.0
    assert maximo > solo_categoria > nada


def test_palabras_compartidas_conserva_el_casing_del_origen():
    """
    CP-206: la evidencia mostrada al usuario usa el casing bonito del
    contenido consultado, no el normalizado interno.
    """
    compartidas = palabras_compartidas(
        ["Spring Boot", "Docker", "Java"], ["docker", "spring boot"]
    )

    assert compartidas == ["Spring Boot", "Docker"]
    assert es_relevante(UMBRAL_MINIMO_RELEVANCIA) is True
    assert es_relevante(UMBRAL_MINIMO_RELEVANCIA - 0.01) is False


# ===========================================================================
# CP-210 .. CP-218  |  Endpoint de recomendaciones
# ===========================================================================


@pytest.fixture
def catalogo_relacionado(client):
    """
    Historial con dos grupos tematicos claros (DevOps y Data Science).

    Devuelve el mapa titulo -> id para que las aserciones no dependan del
    orden de insercion.
    """
    entradas = [
        {
            "titulo": "Docker para Principiantes",
            "texto": "Contenedores, imagenes, Dockerfile y despliegue sobre Linux.",
            "origen": "Alura",
        },
        {
            "titulo": "Kubernetes en Produccion",
            "texto": "Orquestacion de contenedores con Kubernetes, Docker y monitoreo.",
            "origen": "Comunidad",
        },
        {
            "titulo": "Machine Learning con Python",
            "texto": "Modelos con Scikit-Learn, Pandas y NLP usando TF-IDF.",
            "origen": "Oracle Next Education",
        },
        {
            "titulo": "Analisis de Datos con Pandas",
            "texto": "Limpieza y transformacion de datasets con Pandas y Python.",
            "origen": "Alura",
        },
    ]

    ids = {}
    for entrada in entradas:
        respuesta = client.post("/contenido", json=entrada)
        assert respuesta.status_code == 200
        ids[entrada["titulo"]] = respuesta.json()["id"]
    return ids


def test_recomendaciones_devuelve_200_y_el_contrato(client, catalogo_relacionado):
    """CP-210: la respuesta expone referencia, estrategia, total e items."""
    id_docker = catalogo_relacionado["Docker para Principiantes"]
    respuesta = client.get(f"/contenidos/{id_docker}/recomendaciones")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["contenido_id"] == id_docker
    assert cuerpo["titulo"] == "Docker para Principiantes"
    assert cuerpo["estrategia"] == "keywords-jaccard-v1"
    assert cuerpo["total"] == len(cuerpo["items"])


def test_recomendaciones_priorizan_el_contenido_mas_parecido(client, catalogo_relacionado):
    """
    CP-211: para un curso de Docker, el de Kubernetes debe encabezar la lista
    por encima de los de Data Science.
    """
    id_docker = catalogo_relacionado["Docker para Principiantes"]
    items = client.get(f"/contenidos/{id_docker}/recomendaciones").json()["items"]

    assert items, "Deberia haber al menos una recomendacion"
    assert items[0]["titulo"] == "Kubernetes en Produccion"


def test_recomendaciones_nunca_incluyen_el_propio_contenido(client, catalogo_relacionado):
    """CP-212: el contenido consultado se excluye de sus propias sugerencias."""
    for titulo, contenido_id in catalogo_relacionado.items():
        items = client.get(f"/contenidos/{contenido_id}/recomendaciones").json()["items"]
        assert all(i["id"] != contenido_id for i in items), f"Se recomendo a si mismo: {titulo}"


def test_recomendaciones_incluyen_las_palabras_compartidas(client, catalogo_relacionado):
    """
    CP-213: cada sugerencia explica por que se recomendo.

    Es lo que permite a la UI decir "porque ambos hablan de Docker" en vez de
    mostrar un puntaje opaco.
    """
    id_docker = catalogo_relacionado["Docker para Principiantes"]
    items = client.get(f"/contenidos/{id_docker}/recomendaciones").json()["items"]

    kubernetes = next(i for i in items if i["titulo"] == "Kubernetes en Produccion")
    assert "Docker" in kubernetes["palabras_compartidas"]


def test_recomendaciones_ordenadas_por_puntaje_descendente(client, catalogo_relacionado):
    """CP-214: la lista viene ordenada de mayor a menor relevancia."""
    id_docker = catalogo_relacionado["Docker para Principiantes"]
    items = client.get(f"/contenidos/{id_docker}/recomendaciones").json()["items"]

    puntajes = [i["puntaje"] for i in items]
    assert puntajes == sorted(puntajes, reverse=True)
    assert all(0.0 <= p <= 1.0 for p in puntajes)


def test_recomendaciones_respetan_el_limite(client, catalogo_relacionado):
    """CP-215: el parametro `limite` acota la cantidad devuelta."""
    id_docker = catalogo_relacionado["Docker para Principiantes"]
    cuerpo = client.get(f"/contenidos/{id_docker}/recomendaciones", params={"limite": 1}).json()

    assert cuerpo["total"] <= 1
    assert len(cuerpo["items"]) <= 1


@pytest.mark.parametrize("limite", [0, -1, 21, "abc"], ids=["cero", "negativo", "excede", "texto"])
def test_recomendaciones_limite_invalido_devuelve_422(client, catalogo_relacionado, limite):
    """CP-216: un `limite` fuera de rango o no numerico es error de validacion."""
    id_docker = catalogo_relacionado["Docker para Principiantes"]
    respuesta = client.get(
        f"/contenidos/{id_docker}/recomendaciones", params={"limite": limite}
    )
    assert respuesta.status_code == 422


def test_recomendaciones_de_contenido_inexistente_devuelve_404(client):
    """CP-217: un id que no existe responde 404 con formato `ErrorResponse`."""
    respuesta = client.get("/contenidos/999999/recomendaciones")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "http_404"


def test_contenido_sin_relacionados_devuelve_lista_vacia(client):
    """
    CP-218: un unico contenido en el historial no tiene con que compararse.

    No es un error: `total: 0` con lista vacia.
    """
    creado = client.post(
        "/contenido",
        json={"titulo": "Receta de arepas", "texto": "Mezclar harina, agua y sal."},
    ).json()

    cuerpo = client.get(f"/contenidos/{creado['id']}/recomendaciones").json()

    assert cuerpo["total"] == 0
    assert cuerpo["items"] == []


# ===========================================================================
# CP-220 .. CP-221  |  Arquitectura: el motor es sustituible
# ===========================================================================


def test_recomendador_cumple_el_protocol_estructuralmente():
    """
    CP-220 (DIP): `RecomendadorPorKeywords` satisface `MotorRecomendaciones`
    sin heredar de el — tipado estructural, acoplamiento cero.
    """
    from app.domain.protocols import MotorRecomendaciones

    assert isinstance(RecomendadorPorKeywords(), MotorRecomendaciones)


def test_dip_la_ruta_usa_el_recomendador_inyectado(client, catalogo_relacionado):
    """
    CP-221 (DIP/OCP): sustituir el motor via `dependency_overrides` cambia la
    respuesta del endpoint sin tocar la ruta.

    Simula el motor de embeddings de la Semana 5: otra estrategia, misma
    interfaz, cero cambios en `routers/contenido.py`.
    """
    from app.dependencies import get_recomendador
    from app.main import app

    class RecomendadorFalso:
        nombre = "embeddings-semana5"

        def recomendar(self, contenido, candidatos, limite=5):
            return [
                {
                    "id": 999,
                    "titulo": "Sugerencia inyectada",
                    "categoria": "Categoria-Doble",
                    "probabilidad": 0.5,
                    "resumen": "",
                    "origen": None,
                    "puntaje": 0.9,
                    "palabras_compartidas": ["evidencia-dip"],
                }
            ]

    id_docker = catalogo_relacionado["Docker para Principiantes"]

    app.dependency_overrides[get_recomendador] = lambda: RecomendadorFalso()
    try:
        cuerpo = client.get(f"/contenidos/{id_docker}/recomendaciones").json()
    finally:
        app.dependency_overrides.pop(get_recomendador, None)

    assert cuerpo["estrategia"] == "embeddings-semana5"
    assert cuerpo["items"][0]["titulo"] == "Sugerencia inyectada"


def test_recomendador_acota_el_limite_defensivamente():
    """
    CP-222: el motor nunca devuelve mas de `LIMITE_MAXIMO` aunque se le pida
    mas, incluso si se le llama directamente saltandose la validacion HTTP.
    """
    from app.recomendador import LIMITE_MAXIMO

    referencia = {"id": 1, "categoria": "DevOps", "informacion_adicional": ["Docker"]}
    candidatos = [
        {
            "id": i,
            "titulo": f"Curso {i}",
            "categoria": "DevOps",
            "probabilidad": 0.8,
            "resumen": "",
            "origen": None,
            "informacion_adicional": ["Docker"],
        }
        for i in range(2, 60)
    ]

    resultado = RecomendadorPorKeywords().recomendar(referencia, candidatos, limite=999)

    assert len(resultado) == LIMITE_MAXIMO
