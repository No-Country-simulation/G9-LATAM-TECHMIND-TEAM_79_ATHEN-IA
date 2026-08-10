"""
Suite de pruebas de QA - Analiticas del dashboard (Semana 4)
=============================================================

Cubre `GET /analiticas`, el panel completo que alimenta el Dashboard.

    CP-230 .. CP-232   Estado vacio y contrato
    CP-240 .. CP-247   Agregados con datos
    CP-250 .. CP-251   Coexistencia con `GET /metricas`

Ejecutar solo esta suite:

    pytest backend/tests/test_analiticas.py -v
"""

import pytest


@pytest.fixture
def catalogo_variado(client):
    """
    Historial con categorias y origenes distintos, incluyendo un contenido
    sin `origen` para ejercitar la etiqueta "Sin origen".
    """
    entradas = [
        {
            "titulo": "Docker para Principiantes",
            "texto": "Contenedores, Dockerfile, Kubernetes y despliegue en Linux.",
            "origen": "Alura",
        },
        {
            "titulo": "Kubernetes en Produccion",
            "texto": "Orquestacion con Kubernetes, Docker, monitoreo y CI/CD.",
            "origen": "Alura",
        },
        {
            "titulo": "Machine Learning con Python",
            "texto": "Modelos con Scikit-Learn, Pandas y NLP usando TF-IDF.",
            "origen": "Oracle",
        },
        {
            "titulo": "Receta de arepas",
            "texto": "Mezclar harina, agua y sal.",
        },
    ]
    for entrada in entradas:
        assert client.post("/contenido", json=entrada).status_code == 200
    return entradas


# ===========================================================================
# CP-230 .. CP-232  |  Estado vacio y contrato
# ===========================================================================


def test_analiticas_responde_200(client):
    """CP-230: el endpoint responde 200 incluso sin datos."""
    assert client.get("/analiticas").status_code == 200


def test_analiticas_con_historial_vacio_devuelve_ceros(client):
    """CP-231: sin contenidos, todo en cero y listas vacias — nunca falla."""
    cuerpo = client.get("/analiticas").json()

    assert cuerpo["total_contenidos"] == 0
    assert cuerpo["total_categorias"] == 0
    assert cuerpo["total_palabras_clave"] == 0
    assert cuerpo["confianza_promedio"] == 0.0
    assert cuerpo["distribucion_categorias"] == []
    assert cuerpo["distribucion_confianza"] == []
    assert cuerpo["distribucion_origenes"] == []
    assert cuerpo["top_palabras_clave"] == []
    assert cuerpo["actividad_reciente"] == []


def test_analiticas_reporta_el_motor_activo(client):
    """CP-232: el panel informa que engine produjo las clasificaciones."""
    cuerpo = client.get("/analiticas").json()

    assert cuerpo["motor_activo"] in {"modelo_ml_real", "clasificador_reglas"}
    assert cuerpo["modelo_cargado"]
    # Debe coincidir con lo que reporta /salud: una sola verdad.
    assert cuerpo["motor_activo"] == client.get("/salud").json()["motor"]


# ===========================================================================
# CP-240 .. CP-247  |  Agregados con datos
# ===========================================================================


def test_analiticas_cuenta_los_totales(client, catalogo_variado):
    """CP-240: los totales reflejan el historial."""
    cuerpo = client.get("/analiticas").json()

    assert cuerpo["total_contenidos"] == 4
    assert cuerpo["total_categorias"] >= 1
    assert cuerpo["total_palabras_clave"] > 0
    assert 0.0 <= cuerpo["confianza_promedio"] <= 1.0


def test_distribucion_categorias_cubre_el_total(client, catalogo_variado):
    """CP-241: la suma de la distribucion por categoria iguala el total."""
    cuerpo = client.get("/analiticas").json()

    suma = sum(s["cantidad"] for s in cuerpo["distribucion_categorias"])
    assert suma == cuerpo["total_contenidos"]
    assert all(0.0 <= s["porcentaje"] <= 100.0 for s in cuerpo["distribucion_categorias"])


def test_distribucion_categorias_ordenada_de_mayor_a_menor(client, catalogo_variado):
    """CP-242: los segmentos vienen ordenados por cantidad descendente."""
    cantidades = [s["cantidad"] for s in client.get("/analiticas").json()["distribucion_categorias"]]
    assert cantidades == sorted(cantidades, reverse=True)


def test_distribucion_confianza_tiene_las_tres_franjas_en_orden_fijo(client, catalogo_variado):
    """
    CP-243: siempre se devuelven las 3 franjas, en orden Alta -> Media -> Baja.

    El orden es fijo por diseno (no por cantidad): una leyenda que se
    reordena segun los datos es confusa de leer en el dashboard.
    """
    franjas = client.get("/analiticas").json()["distribucion_confianza"]

    assert [f["etiqueta"] for f in franjas] == ["Alta (≥75%)", "Media (50-74%)", "Baja (<50%)"]
    assert sum(f["cantidad"] for f in franjas) == 4


def test_distribucion_origenes_incluye_sin_origen(client, catalogo_variado):
    """
    CP-244: el contenido sin `origen` se agrupa bajo "Sin origen" en vez de
    desaparecer del recuento.
    """
    origenes = client.get("/analiticas").json()["distribucion_origenes"]
    etiquetas = {o["etiqueta"] for o in origenes}

    assert "Alura" in etiquetas
    assert "Sin origen" in etiquetas
    assert sum(o["cantidad"] for o in origenes) == 4


def test_top_palabras_clave_ordenado_y_acotado(client, catalogo_variado):
    """CP-245: top 10 como maximo, de mayor a menor frecuencia."""
    top = client.get("/analiticas").json()["top_palabras_clave"]

    assert len(top) <= 10
    cantidades = [p["cantidad"] for p in top]
    assert cantidades == sorted(cantidades, reverse=True)


def test_actividad_reciente_en_orden_cronologico(client, catalogo_variado):
    """CP-246: la serie temporal viene ordenada de mas antiguo a mas reciente."""
    actividad = client.get("/analiticas").json()["actividad_reciente"]

    assert actividad, "Deberia haber al menos un dia con actividad"
    fechas = [p["fecha"] for p in actividad]
    assert fechas == sorted(fechas)
    assert sum(p["cantidad"] for p in actividad) == 4


def test_analiticas_refleja_contenido_nuevo(client, catalogo_variado):
    """CP-247: analizar contenido nuevo mueve los agregados de inmediato."""
    antes = client.get("/analiticas").json()["total_contenidos"]

    client.post(
        "/contenido",
        json={"titulo": "Spring Boot", "texto": "APIs REST con Java y Spring Security."},
    )

    assert client.get("/analiticas").json()["total_contenidos"] == antes + 1


# ===========================================================================
# CP-250 .. CP-251  |  Coexistencia con /metricas
# ===========================================================================


def test_analiticas_y_metricas_coinciden_en_los_totales(client, catalogo_variado):
    """
    CP-250: `/analiticas` es un superset de `/metricas`; donde se solapan
    deben decir exactamente lo mismo.
    """
    analiticas = client.get("/analiticas").json()
    metricas = client.get("/metricas").json()

    assert analiticas["total_contenidos"] == metricas["total_cursos"]
    assert analiticas["total_categorias"] == metricas["total_categorias"]
    assert analiticas["total_palabras_clave"] == metricas["total_palabras_clave"]
    assert analiticas["confianza_promedio"] == metricas["confianza_promedio"]


def test_metricas_sigue_funcionando_sin_cambios(client, catalogo_variado):
    """
    CP-251: agregar `/analiticas` no rompio el contrato de `/metricas`.

    Regresion explicita: hay clientes y pruebas de semanas anteriores que
    dependen de sus nombres de campo.
    """
    cuerpo = client.get("/metricas").json()

    for campo in (
        "total_cursos",
        "total_categorias",
        "total_palabras_clave",
        "confianza_promedio",
        "distribucion",
        "top_palabras_clave",
    ):
        assert campo in cuerpo, f"/metricas perdio el campo '{campo}'"


def test_calcular_analiticas_es_independiente_del_estado_global():
    """
    CP-252 (DIP): `calcular_analiticas` recibe el motor por parametro, asi que
    puede ejecutarse con un doble sin montar la app ni tocar `services`.
    """
    from datetime import datetime, timezone

    from app.services import calcular_analiticas

    class MotorDoble:
        motor = "clasificador_reglas"
        nombre = "doble-analiticas"

    items = [
        {
            "categoria": "DevOps",
            "probabilidad": 0.9,
            "informacion_adicional": ["Docker"],
            "origen": "Alura",
            "creado_en": datetime(2026, 8, 10, tzinfo=timezone.utc),
        },
        {
            "categoria": "DevOps",
            "probabilidad": 0.4,
            "informacion_adicional": ["Kubernetes"],
            "origen": None,
            "creado_en": datetime(2026, 8, 11, tzinfo=timezone.utc),
        },
    ]

    resultado = calcular_analiticas(items, MotorDoble())

    assert resultado["total_contenidos"] == 2
    assert resultado["modelo_cargado"] == "doble-analiticas"
    assert resultado["confianza_promedio"] == pytest.approx(0.65)
    assert resultado["actividad_reciente"] == [
        {"fecha": "2026-08-10", "cantidad": 1},
        {"fecha": "2026-08-11", "cantidad": 1},
    ]
    # Un item con probabilidad 0.9 (Alta) y otro con 0.4 (Baja).
    franjas = {f["etiqueta"]: f["cantidad"] for f in resultado["distribucion_confianza"]}
    assert franjas["Alta (≥75%)"] == 1
    assert franjas["Baja (<50%)"] == 1
    assert franjas["Media (50-74%)"] == 0
