"""
Suite de pruebas de QA - Nivel de confianza y robustez ante entradas ambiguas
=============================================================================

Semana 5. Cubre el campo `nivel_confianza` de `POST /contenido` y el
comportamiento de la API ante texto sin senal (ruido, simbolos, contenido no
tecnico), que es lo que un jurado escribira para "romper" la demo.

    CP-300 .. CP-305   Unidad: bandas de confianza (domain/confianza.py)
    CP-310 .. CP-316   Integracion: nivel_confianza en la respuesta
    CP-320 .. CP-323   Robustez ante entradas ambiguas o adversarias
    CP-330 .. CP-331   Taxonomia de Ciberseguridad

Ejecutar solo esta suite:

    pytest backend/tests/test_confianza.py -v
"""

import pytest

from app.domain.confianza import (
    FRANJAS_CONFIANZA,
    UMBRAL_CONFIANZA_BAJA,
    etiqueta_de_franja,
    etiquetas_ordenadas,
    nivel_de_confianza,
)


# ===========================================================================
# CP-300 .. CP-305  |  Bandas de confianza (unidad)
# ===========================================================================


@pytest.mark.parametrize(
    "probabilidad,esperado",
    [
        (1.00, "alta"),
        (0.93, "alta"),
        (0.75, "alta"),      # limite inferior exacto de "alta"
        (0.7499, "media"),
        (0.60, "media"),
        (0.50, "media"),     # limite inferior exacto de "media"
        (0.4999, "baja"),
        (0.37, "baja"),      # suelo observado del modelo real
        (0.00, "baja"),
    ],
)
def test_nivel_de_confianza_por_franja(probabilidad, esperado):
    """CP-300: cada probabilidad cae en su franja, incluidos los limites."""
    assert nivel_de_confianza(probabilidad) == esperado


def test_etiqueta_de_franja_coincide_con_el_nivel():
    """CP-301: la etiqueta legible corresponde al mismo nivel."""
    assert etiqueta_de_franja(0.93).startswith("Alta")
    assert etiqueta_de_franja(0.60).startswith("Media")
    assert etiqueta_de_franja(0.20).startswith("Baja")


def test_etiquetas_en_orden_fijo():
    """
    CP-302: siempre Alta -> Media -> Baja, sin importar los datos.

    El panel de analiticas las pinta en este orden; una leyenda que se
    reordena segun las cantidades es confusa de leer.
    """
    assert etiquetas_ordenadas() == ["Alta (≥75%)", "Media (50-74%)", "Baja (<50%)"]


def test_las_franjas_cubren_todo_el_rango_sin_huecos():
    """
    CP-303: no hay ninguna probabilidad entre 0 y 1 que quede sin franja.

    Un hueco produciria un `nivel_confianza` invalido que Pydantic rechazaria
    con un 500 en produccion.
    """
    for centesima in range(0, 101):
        assert nivel_de_confianza(centesima / 100) in {"alta", "media", "baja"}


def test_umbral_de_confianza_baja_es_coherente_con_las_franjas():
    """CP-304: el umbral de aviso coincide con el suelo de la franja media."""
    assert nivel_de_confianza(UMBRAL_CONFIANZA_BAJA) == "media"
    assert nivel_de_confianza(UMBRAL_CONFIANZA_BAJA - 0.01) == "baja"


def test_franjas_declaradas_de_mayor_a_menor():
    """
    CP-305: el orden de `FRANJAS_CONFIANZA` importa — se evalua la primera que
    coincide, asi que una franja mal ordenada capturaria valores ajenos.
    """
    minimos = [minimo for _nivel, _etiqueta, minimo in FRANJAS_CONFIANZA]
    assert minimos == sorted(minimos, reverse=True)


# ===========================================================================
# CP-310 .. CP-316  |  `nivel_confianza` en la respuesta de la API
# ===========================================================================


def test_respuesta_incluye_nivel_de_confianza(client, payload_valido):
    """CP-310: `POST /contenido` devuelve siempre el nivel de confianza."""
    cuerpo = client.post("/contenido", json=payload_valido).json()

    assert "nivel_confianza" in cuerpo
    assert cuerpo["nivel_confianza"] in {"alta", "media", "baja"}


def test_nivel_coincide_con_la_probabilidad_devuelta(client, payload_valido):
    """CP-311: el nivel no puede contradecir a la probabilidad del mismo JSON."""
    cuerpo = client.post("/contenido", json=payload_valido).json()

    assert cuerpo["nivel_confianza"] == nivel_de_confianza(cuerpo["probabilidad"])


def test_texto_sin_senal_reporta_confianza_baja(client):
    """
    CP-312: contenido sin ninguna tecnologia reconocible no se presenta como
    una clasificacion firme.

    Con el motor de reglas, un texto no tecnico cae en "Otros" con 0.35, que
    es franja baja. Es exactamente lo que debe ver el usuario: una advertencia,
    no un resultado con apariencia de certeza.
    """
    cuerpo = client.post(
        "/contenido",
        json={"titulo": "Receta de arepas", "texto": "Mezclar harina, agua y sal."},
    ).json()

    assert cuerpo["nivel_confianza"] == "baja"
    assert cuerpo["informacion_adicional"] == []


def test_contenido_tecnico_claro_no_marca_confianza_baja(client, payload_valido):
    """CP-313: un curso de Spring Boot bien identificado no lleva advertencia."""
    cuerpo = client.post("/contenido", json=payload_valido).json()

    assert cuerpo["nivel_confianza"] in {"alta", "media"}


def test_nivel_se_conserva_en_el_historial(client, payload_valido):
    """CP-314: el nivel viaja al historial, no solo a la respuesta inmediata."""
    creado = client.post("/contenido", json=payload_valido).json()
    item = client.get(f"/contenidos/{creado['id']}").json()

    assert item["nivel_confianza"] == creado["nivel_confianza"]


def test_nivel_presente_en_el_listado(client, payload_valido):
    """CP-315: `GET /contenidos` incluye el nivel en cada item."""
    client.post("/contenido", json=payload_valido)
    items = client.get("/contenidos").json()["items"]

    assert items
    assert all(i["nivel_confianza"] in {"alta", "media", "baja"} for i in items)


def test_contrato_del_hackathon_sigue_intacto(client, payload_valido):
    """
    CP-316: agregar `nivel_confianza` no rompio el contrato oficial.

    Regresion explicita: los tres campos exigidos siguen presentes y con el
    mismo tipo.
    """
    cuerpo = client.post("/contenido", json=payload_valido).json()

    assert isinstance(cuerpo["categoria"], str)
    assert isinstance(cuerpo["probabilidad"], float)
    assert isinstance(cuerpo["informacion_adicional"], list)


# ===========================================================================
# CP-320 .. CP-323  |  Robustez ante entradas ambiguas o adversarias
# ===========================================================================


@pytest.mark.parametrize(
    "titulo,texto",
    [
        ("x", "y"),
        ("???", "!!! @@@ ### $$$"),
        ("123", "456 789 000"),
        ("El clima de hoy", "Hace sol y la temperatura es agradable."),
    ],
    ids=["letras-sueltas", "simbolos", "numeros", "texto-no-tecnico"],
)
def test_entradas_ambiguas_devuelven_json_valido(client, titulo, texto):
    """
    CP-320: ninguna entrada sin sentido rompe la API.

    Siempre 200 con el contrato completo y valores por defecto seguros: la
    categoria nunca es nula y `informacion_adicional` siempre es una lista.
    """
    respuesta = client.post("/contenido", json={"titulo": titulo, "texto": texto})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["categoria"]
    assert isinstance(cuerpo["informacion_adicional"], list)
    assert 0.0 <= cuerpo["probabilidad"] <= 1.0
    assert cuerpo["nivel_confianza"] in {"alta", "media", "baja"}


def test_html_y_script_no_rompen_ni_se_ejecutan(client):
    """
    CP-321: una carga con HTML/JS se trata como texto plano.

    FastAPI serializa a JSON, asi que el marcado viaja escapado; la prueba
    confirma que no provoca un 500 ni altera la estructura de la respuesta.
    """
    respuesta = client.post(
        "/contenido",
        json={
            "titulo": "<script>alert(1)</script>",
            "texto": "<img src=x onerror=alert(1)> Curso de Docker y contenedores.",
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["categoria"], str)
    assert "Docker" in cuerpo["informacion_adicional"]


def test_texto_con_acentos_emojis_y_enes(client):
    """
    CP-322: UTF-8 completo de extremo a extremo.

    Las clases del modelo llevan tilde ("Ciencia de Datos y Analitica"), asi
    que este caso protege la serializacion en ambos sentidos.
    """
    respuesta = client.post(
        "/contenido",
        json={
            "titulo": "Diseño de módulos en Python 🚀",
            "texto": "Programación orientada a objetos, análisis y diseño de código. 🐍",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["categoria"]


def test_texto_muy_largo_no_degrada_el_contrato(client):
    """CP-323: un texto masivo se procesa o se rechaza, pero nunca da 500."""
    respuesta = client.post(
        "/contenido",
        json={
            "titulo": "Curso extenso",
            "texto": "Docker, Kubernetes y despliegue continuo. " * 400,
        },
    )

    assert respuesta.status_code in {200, 413, 422}
    if respuesta.status_code == 200:
        assert respuesta.json()["nivel_confianza"] in {"alta", "media", "baja"}


# ===========================================================================
# CP-330 .. CP-331  |  Taxonomia de Ciberseguridad
# ===========================================================================


def test_contenido_de_seguridad_extrae_palabras_clave(client):
    """
    CP-330: el contenido de ciberseguridad ya no sale con la lista vacia.

    El modelo entrenado tiene una clase "Ciberseguridad y Redes", pero la
    taxonomia no tenia rama equivalente: un curso de firewalls y pentesting se
    mostraba sin ninguna tecnologia en la tarjeta.
    """
    cuerpo = client.post(
        "/contenido",
        json={
            "titulo": "Seguridad de redes",
            "texto": "Firewalls, VPN, pentesting y hardening de servidores con TLS.",
        },
    ).json()

    assert cuerpo["informacion_adicional"], "Deberia detectar tecnologias de seguridad"
    assert "Firewall" in cuerpo["informacion_adicional"]


def test_ciberseguridad_esta_en_el_catalogo_de_reglas(client):
    """CP-331: la categoria nueva se expone en `GET /categorias` (motor reglas)."""
    categorias = client.get("/categorias").json()["categorias"]
    assert "Ciberseguridad" in categorias
