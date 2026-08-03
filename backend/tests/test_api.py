"""
Suite de pruebas automatizadas de QA - AthenIA API
==================================================

Cubre el contrato exigido por el Hackathon ONE Alura + Oracle y las
extensiones de historial y metricas del MVP.

    POST   /contenido        200 con payload valido / 422 con payload invalido
    GET    /salud            200 (verificacion de uptime)
    GET    /contenidos       historial con filtros
    GET    /contenidos/{id}  detalle / 404
    GET    /metricas         agregados del Dashboard

Ejecutar desde la raiz del repositorio:

    pytest

Ver `docs/QA_TESTING_GUIDE.md` para la guia completa.
"""

from pathlib import Path

import pytest

# ===========================================================================
# CP-01 .. CP-03  |  Meta y uptime
# ===========================================================================


def test_salud_responde_200(client):
    """CP-01: el health check responde 200 mientras el servicio este vivo."""
    respuesta = client.get("/salud")
    assert respuesta.status_code == 200


def test_salud_reporta_estado_ok(client):
    """CP-02: el health check informa estado, version y modelo cargado."""
    cuerpo = client.get("/salud").json()

    assert cuerpo["estado"] == "ok"
    assert cuerpo["version"]
    assert cuerpo["modelo_cargado"]
    assert isinstance(cuerpo["es_mock"], bool)
    assert isinstance(cuerpo["contenidos_en_historial"], int)


def test_salud_reporta_el_motor_de_clasificacion(client):
    """CP-04: `motor` identifica que engine responde las predicciones."""
    cuerpo = client.get("/salud").json()

    assert cuerpo["motor"] in {"modelo_ml_real", "clasificador_reglas"}
    # `es_mock` y `motor` no pueden contradecirse.
    assert cuerpo["es_mock"] is (cuerpo["motor"] == "clasificador_reglas")


def test_root_lista_endpoints(client):
    """CP-03: la raiz documenta los endpoints disponibles."""
    cuerpo = client.get("/").json()

    assert cuerpo["nombre"] == "AthenIA API"
    assert "POST /contenido" in cuerpo["endpoints"]


# ===========================================================================
# CP-10 .. CP-16  |  POST /contenido  (caso feliz)
# ===========================================================================


def test_contenido_payload_valido_devuelve_200(client, payload_valido):
    """CP-10: un payload valido responde 200."""
    respuesta = client.post("/contenido", json=payload_valido)
    assert respuesta.status_code == 200


def test_contenido_respeta_el_contrato_del_hackathon(client, payload_valido):
    """
    CP-11: la respuesta contiene las tres claves exigidas por el Hackathon,
    con los tipos correctos.
    """
    cuerpo = client.post("/contenido", json=payload_valido).json()

    assert "categoria" in cuerpo
    assert "probabilidad" in cuerpo
    assert "informacion_adicional" in cuerpo

    assert isinstance(cuerpo["categoria"], str)
    assert isinstance(cuerpo["probabilidad"], float)
    assert isinstance(cuerpo["informacion_adicional"], list)
    assert all(isinstance(k, str) for k in cuerpo["informacion_adicional"])


def test_probabilidad_esta_entre_0_y_1(client, payload_valido):
    """CP-12: la probabilidad es una confianza normalizada."""
    cuerpo = client.post("/contenido", json=payload_valido).json()
    assert 0.0 <= cuerpo["probabilidad"] <= 1.0


def test_contenido_de_backend_se_clasifica_como_backend(client, payload_valido):
    """CP-13: un curso de Spring Boot se clasifica como 'Backend'."""
    cuerpo = client.post("/contenido", json=payload_valido).json()

    assert cuerpo["categoria"] == "Backend"
    assert "Spring Boot" in cuerpo["informacion_adicional"]


@pytest.mark.parametrize(
    "titulo,texto,categoria_esperada",
    [
        (
            "Machine Learning con Python",
            "Entrenamiento de modelos con Scikit-Learn, Pandas y NLP usando TF-IDF.",
            "Data Science",
        ),
        (
            "Docker para Principiantes",
            "Conceptos basicos de contenedores, Dockerfile, Kubernetes y CI/CD.",
            "DevOps",
        ),
        (
            "React desde Cero",
            "Componentes, hooks y estilos con Tailwind CSS para construir una UI responsive.",
            "Frontend",
        ),
        (
            "Despliegue en Oracle Cloud",
            "Uso de OCI, Object Storage y Autonomous Database con alta disponibilidad.",
            "Cloud",
        ),
    ],
)
def test_clasificacion_multicategoria(client, titulo, texto, categoria_esperada):
    """CP-14: el clasificador distingue entre las categorias del catalogo."""
    respuesta = client.post("/contenido", json={"titulo": titulo, "texto": texto})

    assert respuesta.status_code == 200
    assert respuesta.json()["categoria"] == categoria_esperada


def test_texto_sin_terminos_tecnicos_cae_en_otros(client):
    """CP-15: contenido no tecnico no se fuerza a una categoria tecnica."""
    respuesta = client.post(
        "/contenido",
        json={"titulo": "Receta de arepas", "texto": "Mezclar harina, agua y sal."},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["categoria"] == "Otros"


def test_clasificacion_es_determinista(client, payload_valido):
    """
    CP-16: dos llamadas identicas producen la misma clasificacion.

    Se excluye `id`, que es distinto por diseno: cada llamada crea una entrada
    nueva en el historial.
    """
    primera = client.post("/contenido", json=payload_valido).json()
    segunda = client.post("/contenido", json=payload_valido).json()

    primera.pop("id")
    segunda.pop("id")

    assert primera == segunda


# ===========================================================================
# CP-20 .. CP-27  |  POST /contenido  (validaciones -> 422)
# ===========================================================================


def test_falta_el_campo_texto_devuelve_422(client):
    """CP-20: falta un parametro obligatorio -> 422."""
    respuesta = client.post("/contenido", json={"titulo": "Solo titulo"})
    assert respuesta.status_code == 422


def test_falta_el_campo_titulo_devuelve_422(client):
    """CP-21: falta un parametro obligatorio -> 422."""
    respuesta = client.post("/contenido", json={"texto": "Solo texto"})
    assert respuesta.status_code == 422


def test_payload_vacio_devuelve_422(client):
    """CP-22: body vacio -> 422."""
    respuesta = client.post("/contenido", json={})
    assert respuesta.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"titulo": "", "texto": "Contenido valido sobre Java."},
        {"titulo": "Titulo valido", "texto": ""},
        {"titulo": "", "texto": ""},
    ],
    ids=["titulo-vacio", "texto-vacio", "ambos-vacios"],
)
def test_cadenas_vacias_devuelven_422(client, payload):
    """CP-23: cadenas vacias -> 422 (regla de negocio: no se acepta vacio)."""
    assert client.post("/contenido", json=payload).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"titulo": "   ", "texto": "Contenido valido sobre Java."},
        {"titulo": "Titulo valido", "texto": "\n\t  "},
    ],
    ids=["titulo-espacios", "texto-espacios"],
)
def test_solo_espacios_en_blanco_devuelve_422(client, payload):
    """CP-24: cadenas con solo espacios -> 422."""
    assert client.post("/contenido", json=payload).status_code == 422


def test_tipos_incorrectos_devuelven_422(client):
    """CP-25: tipos de dato invalidos -> 422."""
    respuesta = client.post("/contenido", json={"titulo": 123, "texto": ["lista"]})
    assert respuesta.status_code == 422


def test_error_422_incluye_detalle_del_campo(client):
    """CP-26: el error identifica el campo que fallo (util para el frontend)."""
    cuerpo = client.post("/contenido", json={"titulo": "Solo titulo"}).json()

    assert "detail" in cuerpo
    campos = {campo for error in cuerpo["detail"] for campo in error["loc"]}
    assert "texto" in campos


def test_error_422_usa_el_formato_error_response(client):
    """CP-27: los errores siguen el esquema `ErrorResponse` (error + mensaje)."""
    cuerpo = client.post("/contenido", json={}).json()

    assert cuerpo["error"] == "validacion"
    assert isinstance(cuerpo["mensaje"], str) and cuerpo["mensaje"]


# ===========================================================================
# CP-30 .. CP-33  |  Metodos, rutas y catalogo
# ===========================================================================


def test_metodo_get_no_permitido_en_contenido(client):
    """CP-30: /contenido solo acepta POST."""
    assert client.get("/contenido").status_code == 405


def test_ruta_inexistente_devuelve_404(client):
    """CP-31: rutas no definidas -> 404."""
    assert client.get("/ruta-que-no-existe").status_code == 404


def test_categorias_devuelve_catalogo(client):
    """CP-32: el catalogo de categorias esta disponible para el frontend."""
    cuerpo = client.get("/categorias").json()

    assert isinstance(cuerpo["categorias"], list)
    assert "Backend" in cuerpo["categorias"]


def test_respuesta_incluye_tiempo_de_proceso(client, payload_valido):
    """CP-33: el middleware expone `X-Process-Time` para medicion de QA."""
    respuesta = client.post("/contenido", json=payload_valido)
    assert respuesta.headers.get("X-Process-Time", "").endswith("ms")


# ===========================================================================
# CP-40  |  CORS (integracion Frontend <-> Backend)
# ===========================================================================


def test_cors_permite_el_origen_del_frontend(client, payload_valido):
    """CP-40: el backend acepta peticiones desde el dev server de Vite."""
    respuesta = client.post(
        "/contenido",
        json=payload_valido,
        headers={"Origin": "http://localhost:5173"},
    )

    assert respuesta.status_code == 200
    assert respuesta.headers.get("access-control-allow-origin") == "*"


# ===========================================================================
# CP-50 .. CP-58  |  GET /contenidos  (historial)
# ===========================================================================


def test_historial_vacio_al_inicio(client):
    """CP-50: sin analisis previos el historial esta vacio."""
    cuerpo = client.get("/contenidos").json()

    assert cuerpo["total"] == 0
    assert cuerpo["items"] == []


def test_analizar_guarda_en_el_historial(client, payload_valido):
    """CP-51: cada analisis queda registrado en el historial."""
    client.post("/contenido", json=payload_valido)
    cuerpo = client.get("/contenidos").json()

    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["titulo"] == payload_valido["titulo"]


def test_historial_incluye_texto_y_fecha(client, payload_valido):
    """CP-52: el item del historial conserva el contenido original y su fecha."""
    client.post("/contenido", json=payload_valido)
    item = client.get("/contenidos").json()["items"][0]

    assert item["texto"] == payload_valido["texto"]
    assert item["creado_en"]
    assert item["categoria"] == "Backend"


def test_historial_ordena_del_mas_reciente_al_mas_antiguo(client, historial_poblado):
    """CP-53: el ultimo analisis aparece primero."""
    items = client.get("/contenidos").json()["items"]

    assert [i["id"] for i in items] == sorted((i["id"] for i in items), reverse=True)
    assert items[0]["titulo"] == "Machine Learning con Python"


def test_historial_filtra_por_categoria(client, historial_poblado):
    """CP-54: el filtro por categoria devuelve solo esa categoria."""
    cuerpo = client.get("/contenidos", params={"categoria": "DevOps"}).json()

    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["categoria"] == "DevOps"


def test_historial_busca_por_texto_libre(client, historial_poblado):
    """CP-55: la busqueda libre encuentra por titulo, texto o palabra clave."""
    cuerpo = client.get("/contenidos", params={"buscar": "docker"}).json()

    assert cuerpo["total"] == 1
    assert "Docker" in cuerpo["items"][0]["titulo"]


def test_historial_busca_sin_distinguir_acentos_ni_mayusculas(client, historial_poblado):
    """CP-56: la busqueda es insensible a mayusculas y acentos."""
    assert client.get("/contenidos", params={"buscar": "PYTHON"}).json()["total"] == 1


def test_historial_respeta_el_limite(client, historial_poblado):
    """CP-57: el parametro `limite` acota la cantidad devuelta."""
    cuerpo = client.get("/contenidos", params={"limite": 2}).json()
    assert cuerpo["total"] == 2


def test_historial_sin_coincidencias_devuelve_lista_vacia(client, historial_poblado):
    """CP-58: una busqueda sin resultados no es un error."""
    cuerpo = client.get("/contenidos", params={"buscar": "zzzzzz"}).json()

    assert cuerpo["total"] == 0
    assert cuerpo["items"] == []


# ===========================================================================
# CP-60 .. CP-63  |  GET /contenidos/{id} y DELETE /contenidos
# ===========================================================================


def test_detalle_de_contenido_devuelve_200(client, payload_valido):
    """CP-60: se puede recuperar un analisis por su id."""
    creado = client.post("/contenido", json=payload_valido).json()
    respuesta = client.get(f"/contenidos/{creado['id']}")

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creado["id"]
    assert respuesta.json()["titulo"] == payload_valido["titulo"]


def test_detalle_de_contenido_inexistente_devuelve_404(client):
    """CP-61: un id que no existe responde 404 con formato `ErrorResponse`."""
    respuesta = client.get("/contenidos/9999")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "http_404"


def test_detalle_con_id_no_numerico_devuelve_422(client):
    """CP-62: un id no numerico es un error de validacion."""
    assert client.get("/contenidos/abc").status_code == 422


def test_limpiar_historial_lo_vacia(client, historial_poblado):
    """CP-63: DELETE /contenidos vacia el historial (utilidad de QA)."""
    respuesta = client.delete("/contenidos")

    assert respuesta.status_code == 200
    assert respuesta.json()["eliminados"] == 3
    assert client.get("/contenidos").json()["total"] == 0


# ===========================================================================
# CP-70 .. CP-73  |  GET /metricas  (Dashboard)
# ===========================================================================


def test_metricas_con_historial_vacio(client):
    """CP-70: sin datos, las metricas son cero y no fallan."""
    cuerpo = client.get("/metricas").json()

    assert cuerpo["total_cursos"] == 0
    assert cuerpo["total_categorias"] == 0
    assert cuerpo["distribucion"] == []


def test_metricas_cuentan_cursos_y_categorias(client, historial_poblado):
    """CP-71: las metricas reflejan el historial."""
    cuerpo = client.get("/metricas").json()

    assert cuerpo["total_cursos"] == 3
    assert cuerpo["total_categorias"] == 3
    assert cuerpo["total_palabras_clave"] > 0


def test_metricas_distribucion_suma_el_total(client, historial_poblado):
    """CP-72: la distribucion por categoria cubre todos los contenidos."""
    cuerpo = client.get("/metricas").json()

    assert sum(d["cantidad"] for d in cuerpo["distribucion"]) == cuerpo["total_cursos"]
    assert all(0 <= d["porcentaje"] <= 100 for d in cuerpo["distribucion"])


def test_metricas_confianza_promedio_normalizada(client, historial_poblado):
    """CP-73: la confianza promedio es un valor entre 0 y 1."""
    assert 0.0 <= client.get("/metricas").json()["confianza_promedio"] <= 1.0


# ===========================================================================
# CP-80 .. CP-81  |  Mecanismo de fallback del modelo
# ===========================================================================


def test_fallback_activo_sin_modelo_entrenado(client):
    """
    CP-80: sin artefacto en `backend/models/`, la API responde con el
    clasificador por reglas en lugar de fallar.
    """
    cuerpo = client.get("/salud").json()

    assert cuerpo["motor"] == "clasificador_reglas"
    assert cuerpo["es_mock"] is True
    assert cuerpo["modelo_cargado"] == "reglas-keywords-v1"


def test_metadatos_opcionales_se_conservan(client):
    """CP-81: `origen` y `url` son opcionales y se guardan en el historial."""
    respuesta = client.post(
        "/contenido",
        json={
            "titulo": "Curso de Docker",
            "texto": "Contenedores, imagenes y Dockerfile paso a paso.",
            "origen": "Alura",
            "url": "https://ejemplo.com/docker",
        },
    )

    assert respuesta.status_code == 200

    item = client.get(f"/contenidos/{respuesta.json()['id']}").json()
    assert item["origen"] == "Alura"
    assert item["url"] == "https://ejemplo.com/docker"


# ===========================================================================
# CP-90 .. CP-99  |  Integracion del modelo real (Semana 3)
# ===========================================================================
#
# Estas pruebas entrenan un Pipeline REAL de scikit-learn al vuelo y lo
# serializan igual que lo hara Data Science. No dependen de que el artefacto
# de produccion exista en el repositorio, pero ejercitan exactamente el mismo
# camino de carga, adaptacion e inferencia.


def test_modelo_real_activa_el_motor_ml(client, modelo_ml_real):
    """CP-90: con el artefacto presente, `GET /salud` reporta el motor real."""
    cuerpo = client.get("/salud").json()

    assert cuerpo["motor"] == "modelo_ml_real"
    assert cuerpo["es_mock"] is False
    assert cuerpo["modelo_cargado"] == "clasificador_cursos.pkl"
    assert cuerpo["detalle_modelo"] == "Pipeline"


def test_modelo_real_produce_la_prediccion(client, modelo_ml_real):
    """CP-91: la categoria proviene del modelo entrenado, no de las reglas."""
    respuesta = client.post(
        "/contenido",
        json={
            "titulo": "Curso de Kubernetes",
            "texto": "Docker, Kubernetes, pipelines CI/CD y despliegue continuo.",
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["categoria"] == "DevOps"
    # `modelo` deja rastro del artefacto que respondio (trazabilidad para QA).
    assert cuerpo["modelo"] == "clasificador_cursos.pkl"


def test_modelo_real_respeta_el_contrato_del_hackathon(client, modelo_ml_real, payload_valido):
    """CP-92: el contrato de respuesta no cambia al activar el modelo real."""
    cuerpo = client.post("/contenido", json=payload_valido).json()

    assert isinstance(cuerpo["categoria"], str)
    assert isinstance(cuerpo["probabilidad"], float)
    assert 0.0 <= cuerpo["probabilidad"] <= 1.0
    assert isinstance(cuerpo["informacion_adicional"], list)
    # Las palabras clave se siguen extrayendo por taxonomia.
    assert "Spring Boot" in cuerpo["informacion_adicional"]


def test_modelo_real_expone_sus_clases(client, modelo_ml_real):
    """CP-93: `GET /categorias` devuelve las clases del modelo entrenado."""
    categorias = client.get("/categorias").json()["categorias"]

    assert categorias == ["Backend", "Data Science", "DevOps"]


def test_modelo_real_valida_payloads_invalidos(client, modelo_ml_real):
    """CP-94: la validacion sigue devolviendo 422 con el motor real activo."""
    assert client.post("/contenido", json={}).status_code == 422
    assert client.post("/contenido", json={"titulo": "Solo titulo"}).status_code == 422
    assert client.post("/contenido", json={"titulo": " ", "texto": " "}).status_code == 422


def test_modelo_real_tolera_textos_minimos(client, modelo_ml_real):
    """CP-95: un texto de una sola palabra no rompe la inferencia."""
    respuesta = client.post("/contenido", json={"titulo": "x", "texto": "y"})

    assert respuesta.status_code == 200
    assert respuesta.json()["categoria"]


@pytest.mark.parametrize(
    "usar_pickle,formato",
    [(False, "joblib"), (True, "pickle")],
    ids=["joblib", "pickle"],
)
def test_carga_desde_joblib_y_pickle(client, activar_artefacto, tmp_path, usar_pickle, formato):
    """
    CP-96: el artefacto se carga tanto si Data Science uso `joblib.dump` como
    `pickle.dump`.
    """
    pytest.importorskip("sklearn")
    from conftest import _construir_pipeline

    ruta = tmp_path / f"clasificador_cursos_{formato}.pkl"
    activar_artefacto(_construir_pipeline(), ruta, usar_pickle=usar_pickle)

    assert client.get("/salud").json()["motor"] == "modelo_ml_real"


@pytest.mark.parametrize(
    "envolver",
    [
        lambda modelo, vec: {"modelo": modelo, "vectorizador": vec},
        lambda modelo, vec: {"model": modelo, "vectorizer": vec},
        lambda modelo, vec: (vec, modelo),
        lambda modelo, vec: [modelo, vec],
    ],
    ids=["dict-es", "dict-en", "tupla-vec-primero", "lista-modelo-primero"],
)
def test_artefacto_con_vectorizador_separado(client, activar_artefacto, tmp_path, envolver):
    """
    CP-97: si el notebook guarda el vectorizador aparte del clasificador, el
    adaptador los recompone en lugar de fallar.
    """
    pytest.importorskip("sklearn")
    from conftest import _construir_piezas_sueltas

    modelo, vectorizador = _construir_piezas_sueltas()
    ruta = tmp_path / "clasificador_cursos.pkl"
    activar_artefacto(envolver(modelo, vectorizador), ruta)

    assert client.get("/salud").json()["motor"] == "modelo_ml_real"

    cuerpo = client.post(
        "/contenido",
        json={"titulo": "Pandas y NumPy", "texto": "Analisis de datos con Python y Pandas."},
    ).json()
    assert cuerpo["categoria"] == "Data Science"


def test_autodeteccion_del_artefacto_por_nombre(client, activar_artefacto, tmp_path):
    """
    CP-98: sin `ATHENIA_MODELO_PATH`, el backend encuentra
    `clasificador_cursos.pkl` dentro de la carpeta de modelos.
    """
    pytest.importorskip("sklearn")
    from conftest import _construir_pipeline

    ruta = tmp_path / "models" / "clasificador_cursos.pkl"
    activar_artefacto(_construir_pipeline(), ruta, autodetectar=True)

    assert client.get("/salud").json()["modelo_cargado"] == "clasificador_cursos.pkl"


def test_probabilidad_del_modelo_real_es_coherente(client, modelo_ml_real):
    """CP-99: la confianza reportada coincide con el maximo de `predict_proba`."""
    import joblib

    pipeline = joblib.load(modelo_ml_real)

    entrada = {
        "titulo": "Curso de Spring Boot",
        "texto": "APIs REST con Java, Spring Security y JPA.",
    }
    esperado = round(float(max(pipeline.predict_proba([f"{entrada['titulo']}. {entrada['texto']}"])[0])), 2)

    assert client.post("/contenido", json=entrada).json()["probabilidad"] == esperado


# ===========================================================================
# CP-100 .. CP-104  |  Resiliencia del mecanismo de fallback
# ===========================================================================


def test_artefacto_corrupto_cae_a_reglas(client, activar_artefacto, tmp_path):
    """CP-100: un `.pkl` ilegible no tumba la API; se degrada a reglas."""
    ruta = tmp_path / "clasificador_cursos.pkl"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(b"esto no es un pickle valido")

    from app import services
    from app.config import settings as ajustes

    ajustes.MODELO_PATH = ruta
    services.recargar_clasificador()

    cuerpo = client.get("/salud").json()
    assert cuerpo["motor"] == "clasificador_reglas"

    # Y la API sigue clasificando.
    respuesta = client.post(
        "/contenido",
        json={"titulo": "Curso de Docker", "texto": "Contenedores y Dockerfile."},
    )
    assert respuesta.status_code == 200

    ajustes.MODELO_PATH = None
    services.recargar_clasificador()


def test_artefacto_sin_predict_cae_a_reglas(client, activar_artefacto, tmp_path):
    """CP-101: un objeto que no sabe predecir se rechaza y se usa el fallback."""
    activar_artefacto({"notas": "esto no es un modelo"}, tmp_path / "clasificador_cursos.pkl")

    assert client.get("/salud").json()["motor"] == "clasificador_reglas"


def test_ruta_de_modelo_inexistente_cae_a_reglas(client):
    """CP-102: `ATHENIA_MODELO_PATH` apuntando a la nada no rompe el arranque."""
    from app import services
    from app.config import settings as ajustes
    from pathlib import Path as _Path

    ajustes.MODELO_PATH = _Path("/ruta/que/no/existe/clasificador_cursos.pkl")
    services.recargar_clasificador()

    assert client.get("/salud").json()["motor"] == "clasificador_reglas"

    ajustes.MODELO_PATH = None
    services.recargar_clasificador()


def test_fallo_de_inferencia_en_caliente_cae_a_reglas():
    """
    CP-103: si `predict` lanza durante una peticion real, `ClasificadorML`
    responde con reglas en vez de propagar el error.

    Se prueba a nivel de unidad porque el artefacto debe fallar *despues* de
    haber pasado la sonda de carga.
    """
    from app.services import AdaptadorModelo, ClasificadorML

    class ModeloQueFalla:
        """Pasa la sonda inicial y luego revienta."""

        def __init__(self):
            self.llamadas = 0

        def predict(self, textos):
            self.llamadas += 1
            if self.llamadas == 1:  # sonda de carga
                return ["Backend"]
            raise RuntimeError("El modelo exploto en inferencia")

    adaptador = AdaptadorModelo(ModeloQueFalla())
    adaptador.predict(["sonda"])  # consume la primera llamada

    motor = ClasificadorML(adaptador, Path("clasificador_cursos.pkl"))
    resultado = motor.clasificar("Curso de Docker", "Contenedores y Dockerfile.")

    assert resultado["categoria"] == "DevOps"  # vino de las reglas
    assert "fallback" in resultado["modelo"]


def test_categorias_relacionadas_salen_del_modelo(client, modelo_ml_real):
    """
    CP-105: las categorias relacionadas son las siguientes clases mas probables
    segun `predict_proba`, no una mezcla con la taxonomia de reglas.
    """
    cuerpo = client.post(
        "/contenido",
        json={"titulo": "Curso mixto", "texto": "Python, Docker y Spring Boot."},
    ).json()

    clases_modelo = set(client.get("/categorias").json()["categorias"])
    relacionadas = cuerpo["categorias_relacionadas"]

    assert set(relacionadas).issubset(clases_modelo)
    assert cuerpo["categoria"] not in relacionadas


def test_sonda_de_carga_descarta_modelos_inservibles(client, activar_artefacto, tmp_path):
    """
    CP-104: un modelo que carga pero no puede predecir texto crudo se descarta
    en la sonda, antes de exponerse a la primera peticion del jurado.
    """
    pytest.importorskip("sklearn")
    from sklearn.linear_model import LogisticRegression
    import numpy as np

    # Clasificador entrenado sobre vectores numericos y guardado SIN su
    # vectorizador: al recibir texto crudo lanzara.
    modelo = LogisticRegression(max_iter=1000)
    modelo.fit(np.array([[0.0, 1.0], [1.0, 0.0], [0.9, 0.1]]), ["A", "B", "B"])

    activar_artefacto(modelo, tmp_path / "clasificador_cursos.pkl")

    assert client.get("/salud").json()["motor"] == "clasificador_reglas"


# ===========================================================================
# CP-106 .. CP-107  |  Arquitectura SOLID (OCP y DIP en vivo)
# ===========================================================================
#
# Estas dos pruebas no verifican una regla de negocio: verifican la
# ARQUITECTURA misma. Sirven de evidencia reproducible para la auditoria
# SOLID de la Semana 3 (ver docs/GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md).


def test_ocp_nuevo_proveedor_se_integra_sin_tocar_el_registro(client):
    """
    CP-106 (OCP): un motor nuevo se suma con una linea de registro, sin
    editar `RegistroProveedores` ni ningun proveedor existente.

    Simula lo que hara el motor de embeddings/LLM de la Semana 4: una clase
    que cumple el `Protocol` `Clasificador` y una funcion `cargar()` que la
    construye. Se registra con prioridad mas alta que el modelo ML para
    demostrar que el registro respeta el orden sin logica especial por motor.
    """
    from app import services
    from app.domain.protocols import Clasificador
    from app.ml.registro import RegistroProveedores

    class ClasificadorFalsoSemana4:
        """Doble minimo que cumple el Protocol `Clasificador` estructuralmente."""

        nombre = "embeddings-demo-semana4"
        motor = "modelo_ml_real"
        es_mock = False
        detalle = "Prueba OCP"

        def clasificar(self, titulo: str, texto: str) -> dict:
            return {
                "categoria": "Categoria-Semana-4",
                "probabilidad": 0.99,
                "informacion_adicional": [],
            }

        def categorias(self):
            return ["Categoria-Semana-4"]

    # Verificacion estructural: el doble cumple el Protocol sin heredar de el.
    instancia = ClasificadorFalsoSemana4()
    assert isinstance(instancia, Clasificador)

    # Registro AISLADO: no se toca `app.ml.registro.registro` (el global de
    # produccion), se instancia una copia limpia para no afectar otras pruebas.
    registro_de_prueba = RegistroProveedores()
    registro_de_prueba.registrar("semana-4-embeddings", lambda: instancia, prioridad=1)
    registro_de_prueba.registrar("modelo-ml", lambda: None, prioridad=10)

    motor_resuelto = registro_de_prueba.resolver()

    assert motor_resuelto is instancia
    assert motor_resuelto.clasificar("x", "y")["categoria"] == "Categoria-Semana-4"

    # El registro de produccion no se toco: `services.clasificador` sigue igual.
    assert services.clasificador.nombre != "embeddings-demo-semana4"


def test_dip_las_rutas_dependen_del_protocol_no_de_la_implementacion(client, payload_valido):
    """
    CP-107 (DIP): `POST /contenido` usa el clasificador inyectado via
    `Depends(get_clasificador)`, no `services.clasificador` a pelo.

    La prueba sustituye la dependencia con `app.dependency_overrides` —el
    mecanismo estandar de FastAPI para invertir dependencias en pruebas— y
    confirma que la ruta responde con el resultado del doble, sin que
    `services.clasificador` (el global de produccion) haya cambiado.
    """
    from app.dependencies import get_clasificador
    from app.main import app

    class ClasificadorDoble:
        nombre = "doble-de-prueba"
        motor = "modelo_ml_real"
        es_mock = False
        detalle = "Doble DIP"

        def clasificar(self, titulo: str, texto: str) -> dict:
            return {
                "categoria": "Categoria-Inyectada",
                "probabilidad": 0.42,
                "informacion_adicional": ["evidencia-dip"],
            }

        def categorias(self):
            return ["Categoria-Inyectada"]

    app.dependency_overrides[get_clasificador] = lambda: ClasificadorDoble()
    try:
        respuesta = client.post("/contenido", json=payload_valido)
    finally:
        # Limpieza obligatoria: si otra prueba corre despues sin esto,
        # seguiria viendo el doble en vez del motor real.
        app.dependency_overrides.pop(get_clasificador, None)

    cuerpo = respuesta.json()
    assert cuerpo["categoria"] == "Categoria-Inyectada"
    assert cuerpo["probabilidad"] == 0.42

    # La sustitucion fue local a la peticion: el estado global no se toco.
    from app import services

    assert services.clasificador.nombre != "doble-de-prueba"


# ===========================================================================
# CP-110 .. CP-113  |  Artefacto REAL de Data Science
# ===========================================================================
#
# A diferencia de las CP-90+, estas pruebas cargan el `.pkl` que realmente
# entrego el equipo de Data Science. Se saltan solas si el archivo no esta
# presente (p. ej. en un clon limpio, porque los .pkl estan en .gitignore),
# de modo que la suite nunca falla por su ausencia.


def test_artefacto_real_carga_y_predice(client, artefacto_real):
    """CP-110: el `clasificador_cursos.pkl` entregado carga y activa el motor ML."""
    cuerpo = client.get("/salud").json()

    assert cuerpo["motor"] == "modelo_ml_real"
    assert cuerpo["es_mock"] is False
    assert cuerpo["modelo_cargado"] == "clasificador_cursos.pkl"


def test_artefacto_real_respeta_el_contrato(client, artefacto_real, payload_valido):
    """CP-111: el contrato del Hackathon se mantiene con el modelo real."""
    respuesta = client.post("/contenido", json=payload_valido)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert isinstance(cuerpo["categoria"], str) and cuerpo["categoria"]
    assert isinstance(cuerpo["probabilidad"], float)
    assert 0.0 <= cuerpo["probabilidad"] <= 1.0
    assert isinstance(cuerpo["informacion_adicional"], list)


def test_artefacto_real_predice_dentro_de_sus_clases(client, artefacto_real):
    """CP-112: toda prediccion pertenece al catalogo declarado por el modelo."""
    clases = set(client.get("/categorias").json()["categorias"])
    assert clases, "El modelo real debe exponer `classes_`"

    ejemplos = [
        {"titulo": "Spring Boot", "texto": "APIs REST con Java, Spring Security y JPA."},
        {"titulo": "Machine Learning", "texto": "Modelos con Scikit-Learn, Pandas y NLP."},
        {"titulo": "Docker", "texto": "Contenedores, Dockerfile, Kubernetes y CI/CD."},
        {"titulo": "Receta de arepas", "texto": "Mezclar harina, agua y sal."},
    ]

    for ejemplo in ejemplos:
        cuerpo = client.post("/contenido", json=ejemplo).json()
        assert cuerpo["categoria"] in clases


def test_artefacto_real_maneja_texto_no_ascii(client, artefacto_real):
    """
    CP-113: acentos y enes no rompen la inferencia ni la serializacion JSON.

    Las clases del modelo incluyen tildes ("Ciencia de Datos y Analitica"), asi
    que este caso protege el camino UTF-8 completo hasta el frontend.
    """
    respuesta = client.post(
        "/contenido",
        json={
            "titulo": "Diseño de módulos en Python",
            "texto": "Programación orientada a objetos, análisis y diseño de código.",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["categoria"]
