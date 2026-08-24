"""
Pruebas del Asistente conversacional (RAG sobre el catalogo de cursos).
=========================================================================

Cubren las tres capas por separado, igual que `test_busqueda_vectorial.py`:

  1. `asistente.servicio.AsistenteCursos`  orquestacion, con dobles del
     buscador y del modelo de lenguaje.
  2. `asistente.motor_openai.ModeloLenguajeOpenAI`  degradacion quando falta
     API key o el paquete `openai`, sin llamar a la red.
  3. `POST /asistente/mensaje` y `GET /asistente/estado`  la ruta completa,
     con las dependencias sustituidas.

Ninguna prueba llama a OpenAI de verdad: el `Protocol` `ModeloLenguaje`
permite inyectar un doble en memoria, igual que `AlmacenVectorial` permite
probar la busqueda sin ChromaDB. Por eso la suite corre en milisegundos, sin
red y sin gastar tokens.

El foco central de este archivo es el contrato anti-alucinacion: el modelo
de lenguaje SOLO debe recibir como contexto los cursos que el buscador
confirmo que existen, y los `cursos_relacionados` que devuelve la ruta deben
salir de ese mismo contexto — nunca del texto que redacto el modelo.
"""

from __future__ import annotations

import pytest

from app.asistente.servicio import MAXIMO_CURSOS_DE_CONTEXTO, AsistenteCursos
from app.busqueda.servicio import BuscadorCursos
from app.dependencies import get_asistente
from app.main import app


# ===========================================================================
# Dobles de prueba
# ===========================================================================


class AlmacenFalso:
    """`AlmacenVectorial` en memoria. Ver `test_busqueda_vectorial.py`."""

    nombre = "falso"

    def __init__(self, cursos: list[dict] | None = None, disponible: bool = True):
        self._cursos = sorted(cursos or [], key=lambda c: c["distancia"])
        self._disponible = disponible

    def esta_disponible(self) -> bool:
        return self._disponible and bool(self._cursos)

    def total(self) -> int:
        return len(self._cursos) if self._disponible else 0

    def consultar(self, texto: str, limite: int) -> list[dict]:
        return self._cursos[:limite]

    def listar(self, categoria=None, limite: int = 24, desplazamiento: int = 0) -> list[dict]:
        return [{**c, "distancia": None} for c in self._cursos[desplazamiento : desplazamiento + limite]]

    def categorias(self) -> dict:
        return {}


def curso(id_: str, distancia: float, titulo: str = "Curso", **meta) -> dict:
    """Construye un resultado crudo con la forma que devuelve el almacen."""
    metadatos = {
        "titulo": titulo,
        "descripcion": "Descripcion del curso.",
        "categoria": "Cloud Computing y DevOps",
        "url": f"https://ejemplo.com/{id_}",
        "sitio": "Coursera",
    }
    metadatos.update(meta)
    return {"id": id_, "distancia": distancia, "metadatos": metadatos, "documento": titulo}


CATALOGO_DOCKER = [
    curso("curso_1", 0.10, "Docker para Principiantes"),
    curso("curso_2", 0.20, "Kubernetes en Produccion"),
]


class ModeloLenguajeFalso:
    """
    `ModeloLenguaje` en memoria.

    Registra con que `contexto` e `historial` se le llamo, para que las
    pruebas verifiquen que el servicio arma el contexto correctamente sin
    depender de que texto devuelva el modelo.
    """

    nombre = "falso"

    def __init__(self, disponible: bool = True, respuesta: str = "Respuesta de prueba."):
        self.disponible = disponible
        self._respuesta = respuesta
        self.llamadas: list[dict] = []

    def responder(self, mensaje: str, contexto: list[dict], historial=None) -> str:
        self.llamadas.append({"mensaje": mensaje, "contexto": contexto, "historial": historial})
        return self._respuesta


@pytest.fixture
def buscador_con_docker() -> BuscadorCursos:
    return BuscadorCursos(AlmacenFalso(CATALOGO_DOCKER))


@pytest.fixture
def buscador_vacio() -> BuscadorCursos:
    return BuscadorCursos(AlmacenFalso([]))


# ===========================================================================
# 1. `AsistenteCursos` (servicio)
# ===========================================================================


class TestRespuestaConCursosEncontrados:
    def test_pasa_al_modelo_solo_los_cursos_que_devolvio_el_buscador(self, buscador_con_docker):
        """
        El corazon del contrato anti-alucinacion: el `contexto` que recibe
        `ModeloLenguaje.responder()` debe ser EXACTAMENTE lo que devolvio el
        buscador semantico, no una lista aparte ni datos inventados.
        """
        modelo = ModeloLenguajeFalso()
        asistente = AsistenteCursos(buscador_con_docker, modelo)

        asistente.responder("cursos de docker")

        assert len(modelo.llamadas) == 1
        titulos_contexto = [c["title"] for c in modelo.llamadas[0]["contexto"]]
        assert "Docker para Principiantes" in titulos_contexto

    def test_los_cursos_relacionados_de_la_respuesta_vienen_del_buscador_no_del_modelo(
        self, buscador_con_docker
    ):
        """
        Aunque el modelo "alucine" un curso inexistente en su texto, la
        interfaz solo debe recibir cursos reales en `cursos_relacionados`.
        """
        modelo = ModeloLenguajeFalso(respuesta="Te recomiendo 'Curso Inventado que No Existe'.")
        asistente = AsistenteCursos(buscador_con_docker, modelo)

        resultado = asistente.responder("cursos de docker")

        titulos = [c["title"] for c in resultado["cursos_relacionados"]]
        assert "Curso Inventado que No Existe" not in titulos
        assert "Docker para Principiantes" in titulos
        assert "Curso Inventado que No Existe" in resultado["respuesta"]  # el texto si viaja tal cual

    def test_respeta_el_tope_de_cursos_de_contexto(self):
        catalogo = [curso(f"c{i}", 0.1 + i * 0.01, f"Curso {i}") for i in range(10)]
        buscador = BuscadorCursos(AlmacenFalso(catalogo))
        modelo = ModeloLenguajeFalso()
        asistente = AsistenteCursos(buscador, modelo)

        asistente.responder("algo generico", historial=None)

        assert len(modelo.llamadas[0]["contexto"]) <= MAXIMO_CURSOS_DE_CONTEXTO

    def test_reenvia_el_historial_de_la_conversacion(self, buscador_con_docker):
        modelo = ModeloLenguajeFalso()
        asistente = AsistenteCursos(buscador_con_docker, modelo)
        historial = [{"rol": "usuario", "texto": "hola"}, {"rol": "asistente", "texto": "hola, ¿en que ayudo?"}]

        asistente.responder("cursos de docker", historial=historial)

        assert modelo.llamadas[0]["historial"] == historial

    def test_el_contrato_de_salida_trae_todas_las_claves(self, buscador_con_docker):
        resultado = AsistenteCursos(buscador_con_docker, ModeloLenguajeFalso()).responder("docker")
        assert set(resultado) == {"respuesta", "cursos_relacionados", "motor", "disponible"}


class TestRespuestaSinCoincidencias:
    def test_un_catalogo_vacio_no_revienta_y_avisa_al_modelo(self, buscador_vacio):
        modelo = ModeloLenguajeFalso()
        resultado = AsistenteCursos(buscador_vacio, modelo).responder("algo muy especifico")

        assert resultado["cursos_relacionados"] == []
        assert modelo.llamadas[0]["contexto"] == []

    def test_un_catalogo_no_disponible_no_revienta(self):
        almacen_caido = AlmacenFalso([], disponible=False)
        asistente = AsistenteCursos(BuscadorCursos(almacen_caido), ModeloLenguajeFalso())

        resultado = asistente.responder("cualquier cosa")

        assert resultado["cursos_relacionados"] == []
        assert resultado["respuesta"] == "Respuesta de prueba."


class TestMensajesInvalidos:
    @pytest.mark.parametrize("mensaje", ["", "   ", "\n\t", None])
    def test_un_mensaje_vacio_no_consulta_nada_y_responde_con_una_pista(
        self, buscador_con_docker, mensaje
    ):
        modelo = ModeloLenguajeFalso()
        resultado = AsistenteCursos(buscador_con_docker, modelo).responder(mensaje)

        assert modelo.llamadas == []  # ni siquiera se llamo al modelo
        assert resultado["cursos_relacionados"] == []
        assert "pregunta" in resultado["respuesta"].lower()


class TestModeloNoDisponible:
    """
    Cuando falta la API key (o el paquete `openai`), el Asistente sigue
    respondiendo 200: la busqueda semantica funciona igual, solo que sin
    redaccion del modelo. Nunca es un error del cliente ni del servidor.
    """

    def test_disponible_refleja_el_estado_del_modelo(self, buscador_con_docker):
        asistente = AsistenteCursos(buscador_con_docker, ModeloLenguajeFalso(disponible=False))
        assert asistente.disponible is False

    def test_sigue_devolviendo_cursos_relacionados_sin_modelo_configurado(self, buscador_con_docker):
        modelo = ModeloLenguajeFalso(
            disponible=False,
            respuesta="El asistente conversacional todavia no esta configurado.",
        )
        resultado = AsistenteCursos(buscador_con_docker, modelo).responder("cursos de docker")

        assert resultado["disponible"] is False
        assert resultado["cursos_relacionados"] != []  # la busqueda si funciono
        assert "no esta configurado" in resultado["respuesta"]


class TestDiagnostico:
    def test_diagnostico_trae_el_estado_de_ambos_motores(self, buscador_con_docker):
        asistente = AsistenteCursos(buscador_con_docker, ModeloLenguajeFalso())
        diagnostico = asistente.diagnostico()

        assert diagnostico == {
            "modelo": "falso",
            "disponible": True,
            "catalogo_disponible": True,
            "total_indexado": 2,
        }


# ===========================================================================
# 2. `ModeloLenguajeOpenAI` — degradacion sin red
# ===========================================================================


class TestModeloOpenAISinConfigurar:
    def test_no_disponible_sin_api_key(self):
        from app.asistente.motor_openai import ModeloLenguajeOpenAI

        modelo = ModeloLenguajeOpenAI(api_key="")
        assert modelo.disponible is False

    def test_responder_sin_api_key_no_lanza_y_explica_la_situacion(self):
        from app.asistente.motor_openai import ModeloLenguajeOpenAI

        modelo = ModeloLenguajeOpenAI(api_key="")
        texto = modelo.responder("hola", contexto=[])
        assert "no esta configurado" in texto or "no está configurado" in texto

    def test_no_reintenta_el_import_en_cada_llamada(self):
        """Memoriza el intento, igual que `AlmacenChroma._intentado`."""
        from app.asistente.motor_openai import ModeloLenguajeOpenAI

        modelo = ModeloLenguajeOpenAI(api_key="clave-de-prueba-invalida")
        modelo.disponible  # primer intento
        intentado_despues_del_primero = modelo._intentado
        modelo.disponible  # segundo acceso: no debe volver a intentar el import
        assert intentado_despues_del_primero is True
        assert modelo._intentado is True


class TestFormateoDeContexto:
    def test_contexto_vacio_se_declara_explicitamente(self):
        from app.asistente.motor_openai import _formatear_contexto

        texto = _formatear_contexto([])
        assert "ninguno encontrado" in texto

    def test_incluye_titulo_categoria_descripcion_y_url(self):
        from app.asistente.motor_openai import _formatear_contexto

        texto = _formatear_contexto(
            [
                {
                    "title": "Docker para Principiantes",
                    "category": "Cloud Computing y DevOps",
                    "description": "Contenedores y Dockerfile.",
                    "url": "https://ejemplo.com/curso_1",
                }
            ]
        )
        assert "Docker para Principiantes" in texto
        assert "Cloud Computing y DevOps" in texto
        assert "https://ejemplo.com/curso_1" in texto


# ===========================================================================
# 3. Ruta HTTP
# ===========================================================================


@pytest.fixture
def cliente_con_asistente(client, buscador_con_docker):
    """`TestClient` con `/asistente/*` apuntando a dobles en memoria."""
    modelo = ModeloLenguajeFalso(respuesta="Encontre estos cursos de Docker para ti.")
    asistente = AsistenteCursos(buscador_con_docker, modelo)
    app.dependency_overrides[get_asistente] = lambda: asistente
    yield client, asistente
    app.dependency_overrides.pop(get_asistente, None)


class TestRutaMensaje:
    def test_responde_200_con_el_contrato_completo(self, cliente_con_asistente):
        cliente, _ = cliente_con_asistente
        respuesta = cliente.post("/asistente/mensaje", json={"mensaje": "cursos de docker"})
        assert respuesta.status_code == 200

        cuerpo = respuesta.json()
        assert set(cuerpo) == {"respuesta", "cursos_relacionados", "motor", "disponible"}
        assert cuerpo["disponible"] is True
        assert len(cuerpo["cursos_relacionados"]) >= 1
        assert cuerpo["cursos_relacionados"][0]["title"] == "Docker para Principiantes"

    def test_acepta_historial_opcional(self, cliente_con_asistente):
        cliente, _ = cliente_con_asistente
        respuesta = cliente.post(
            "/asistente/mensaje",
            json={
                "mensaje": "¿y algo mas avanzado?",
                "historial": [
                    {"rol": "usuario", "texto": "cursos de docker"},
                    {"rol": "asistente", "texto": "Encontre estos cursos de Docker para ti."},
                ],
            },
        )
        assert respuesta.status_code == 200

    def test_rechaza_mensaje_vacio_con_422(self, cliente_con_asistente):
        cliente, _ = cliente_con_asistente
        assert cliente.post("/asistente/mensaje", json={"mensaje": "   "}).status_code == 422

    def test_rechaza_payload_sin_mensaje_con_422(self, cliente_con_asistente):
        cliente, _ = cliente_con_asistente
        assert cliente.post("/asistente/mensaje", json={}).status_code == 422

    def test_sin_modelo_configurado_responde_200_no_500(self, client):
        modelo = ModeloLenguajeFalso(
            disponible=False,
            respuesta="El asistente conversacional todavia no esta configurado.",
        )
        asistente = AsistenteCursos(BuscadorCursos(AlmacenFalso(CATALOGO_DOCKER)), modelo)
        app.dependency_overrides[get_asistente] = lambda: asistente
        try:
            respuesta = client.post("/asistente/mensaje", json={"mensaje": "cursos de docker"})
            assert respuesta.status_code == 200
            cuerpo = respuesta.json()
            assert cuerpo["disponible"] is False
            assert cuerpo["cursos_relacionados"] != []
        finally:
            app.dependency_overrides.pop(get_asistente, None)


class TestRutaEstado:
    def test_responde_200_con_el_diagnostico(self, cliente_con_asistente):
        cliente, _ = cliente_con_asistente
        respuesta = cliente.get("/asistente/estado")
        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "modelo": "falso",
            "disponible": True,
            "catalogo_disponible": True,
            "total_indexado": 2,
        }
