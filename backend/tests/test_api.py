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
    CP-80: sin `classifier.joblib`, la API responde con el clasificador por
    reglas en lugar de fallar.
    """
    cuerpo = client.get("/salud").json()

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
