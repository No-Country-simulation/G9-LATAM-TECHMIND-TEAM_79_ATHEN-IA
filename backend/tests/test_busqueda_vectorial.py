"""
Pruebas de la busqueda vectorial de cursos.
============================================

Cubren las tres capas por separado:

  1. `busqueda.limpieza`  saneado del dataset (funciones puras).
  2. `busqueda.servicio`  umbral, orden y contrato, con un almacen falso.
  3. `GET /cursos/buscar` la ruta completa, con la dependencia sustituida.

Ninguna prueba necesita ChromaDB, la base vectorial de 26 MB ni el modelo de
embeddings: el `Protocol` `AlmacenVectorial` permite inyectar un doble en
memoria. Por eso la suite sigue corriendo en segundos en el CI.

Cada bloque referencia el fallo concreto de la version original que impide
que vuelva a aparecer.
"""

from __future__ import annotations

import pytest

from app.busqueda.limpieza import (
    construir_metadatos,
    primer_titulo,
    construir_texto_indexable,
    es_solo_duracion,
    es_texto_indexable,
    es_valor_nulo,
    preparar_lote,
    primer_valor,
    texto_limpio,
)
from app.busqueda.servicio import BuscadorCursos, distancia_a_puntaje
from app.dependencies import get_buscador_cursos
from app.main import app


# ===========================================================================
# Doble de prueba
# ===========================================================================


class AlmacenFalso:
    """
    `AlmacenVectorial` en memoria.

    Devuelve los cursos que se le configuren, ordenados por distancia
    creciente — igual que ChromaDB. Cumple el `Protocol` por forma, sin
    heredar de el: es tipado estructural.
    """

    nombre = "falso"

    def __init__(self, cursos: list[dict] | None = None, disponible: bool = True):
        self._cursos = sorted(cursos or [], key=lambda c: c["distancia"])
        self._disponible = disponible
        self.consultas: list[tuple[str, int]] = []

    def esta_disponible(self) -> bool:
        return self._disponible and bool(self._cursos)

    def total(self) -> int:
        return len(self._cursos) if self._disponible else 0

    def consultar(self, texto: str, limite: int) -> list[dict]:
        self.consultas.append((texto, limite))
        return self._cursos[:limite]

    def listar(self, categoria=None, limite: int = 24, desplazamiento: int = 0) -> list[dict]:
        pool = self._cursos
        if categoria:
            pool = [c for c in pool if c["metadatos"].get("categoria") == categoria]
        # Sin consulta no hay distancia que medir.
        return [{**c, "distancia": None} for c in pool[desplazamiento : desplazamiento + limite]]

    def categorias(self) -> dict:
        conteo: dict = {}
        for c in self._cursos:
            nombre = c["metadatos"].get("categoria") or "Otras Areas"
            conteo[nombre] = conteo.get(nombre, 0) + 1
        return dict(sorted(conteo.items(), key=lambda kv: -kv[1]))


def curso(id_: str, distancia: float, titulo: str = "Curso", **meta) -> dict:
    """Construye un resultado crudo con la forma que devuelve el almacen."""
    metadatos = {
        "titulo": titulo,
        "descripcion": "Descripcion del curso.",
        "categoria": "Ciencia de Datos y Analitica",
        "url": f"https://ejemplo.com/{id_}",
        "sitio": "Coursera",
    }
    metadatos.update(meta)
    return {"id": id_, "distancia": distancia, "metadatos": metadatos, "documento": titulo}


CATALOGO = [
    curso("curso_1", 0.10, "Python para Ciencia de Datos"),   # score 0.90
    curso("curso_2", 0.28, "Pandas y NumPy desde cero"),      # score 0.72
    curso("curso_3", 0.55, "Estadistica aplicada"),           # score 0.45
    curso("curso_4", 0.80, "Cocina mediterranea"),            # score 0.20
    curso("curso_5", 0.95, "Historia del arte barroco"),      # score 0.05
]


@pytest.fixture
def buscador() -> BuscadorCursos:
    return BuscadorCursos(AlmacenFalso(CATALOGO))


@pytest.fixture
def cliente_con_catalogo(client, buscador):
    """`TestClient` con `/cursos/buscar` apuntando al almacen falso."""
    app.dependency_overrides[get_buscador_cursos] = lambda: buscador
    yield client
    app.dependency_overrides.pop(get_buscador_cursos, None)


# ===========================================================================
# 1. Limpieza del dataset
# ===========================================================================


class TestDeteccionDeNulos:
    """
    El fallo raiz: `item.get("full_text") or respaldo` no protegia de nada,
    porque `" "` y `"nan"` son truthy en Python. 378 cursos del dataset real
    se indexaron con una cadena de espacios.
    """

    @pytest.mark.parametrize(
        "valor",
        [None, "", "   ", "\n\t ", "nan", "NaN", "NAN", "none", "None", "null", "N/A", "-"],
        ids=[
            "none", "vacio", "espacios", "tabs", "nan", "NaN", "NAN",
            "none-str", "None-str", "null", "n/a", "guion",
        ],
    )
    def test_reconoce_los_marcadores_de_ausencia(self, valor):
        assert es_valor_nulo(valor) is True

    def test_reconoce_el_nan_de_pandas(self):
        # Un NaN real llega asi cuando Data exporta con pandas sin `fillna`.
        assert es_valor_nulo(float("nan")) is True

    @pytest.mark.parametrize("valor", ["Python", "  Machine Learning  ", "0", 0, 3.5])
    def test_no_confunde_contenido_valido_con_nulo(self, valor):
        assert es_valor_nulo(valor) is False

    def test_texto_limpio_colapsa_espacios_y_aplica_defecto(self):
        assert texto_limpio("  Machine   Learning \n") == "Machine Learning"
        assert texto_limpio("   ", defecto="Sin titulo") == "Sin titulo"
        assert texto_limpio("nan", defecto="Sin titulo") == "Sin titulo"


class TestSeleccionDeCampos:
    def test_salta_los_campos_nulos_hasta_el_primero_con_contenido(self):
        # Exactamente lo que el `or` original no hacia.
        item = {"clean_title": "   ", "Title": "nan", "Course Title": "Deep Learning"}
        assert primer_valor(item, "clean_title", "Title", "Course Title") == "Deep Learning"

    def test_devuelve_el_defecto_si_todos_son_nulos(self):
        item = {"clean_title": " ", "Title": None}
        assert primer_valor(item, "clean_title", "Title", defecto="Sin titulo") == "Sin titulo"


class TestTextoIndexable:
    @pytest.mark.parametrize(
        "texto", ["4 hours", "3 Hours", "2.5 hrs", "45 min", "6 semanas", "1 year", "10 days"]
    )
    def test_detecta_las_duraciones_que_se_colaron_en_el_etl(self, texto):
        # ~200 registros del dataset traen una duracion en la columna de texto.
        assert es_solo_duracion(texto) is True
        assert es_texto_indexable(texto) is False

    def test_no_confunde_una_duracion_dentro_de_una_frase(self):
        assert es_solo_duracion("Curso de Python en 4 hours") is False

    @pytest.mark.parametrize("texto", ["", "   ", "nan", "MBA", "PMP 2024", "AI"])
    def test_rechaza_textos_sin_senal_semantica(self, texto):
        assert es_texto_indexable(texto) is False

    def test_acepta_un_texto_con_contenido_real(self):
        assert es_texto_indexable("Introduccion a Machine Learning con Python") is True

    def test_usa_el_respaldo_cuando_full_text_son_espacios(self):
        item = {
            "full_text": "   ",
            "clean_title": "Redes Neuronales Convolucionales",
            "target_category": "Inteligencia Artificial y ML",
        }
        texto = construir_texto_indexable(item)
        assert texto is not None
        assert "Redes Neuronales" in texto
        assert "  " not in texto  # espacios colapsados

    def test_usa_el_respaldo_cuando_full_text_es_una_duracion(self):
        item = {"full_text": "4 hours", "clean_title": "Kubernetes en Produccion"}
        assert construir_texto_indexable({**item, "clean_intro": "Orquestacion de contenedores."})

    def test_descarta_el_curso_cuando_no_hay_nada_aprovechable(self):
        item = {"full_text": "  ", "clean_title": "nan", "Title": None, "clean_intro": ""}
        assert construir_texto_indexable(item) is None

    def test_el_texto_indexado_nunca_contiene_la_palabra_nan(self):
        item = {"full_text": "nan", "clean_title": "Docker Avanzado", "clean_skills": "nan",
                "clean_intro": "Contenedores y despliegue continuo en la nube."}
        texto = construir_texto_indexable(item)
        assert "nan" not in texto.lower().split()


class TestMetadatos:
    def test_incluye_descripcion_que_la_version_original_omitia(self):
        # Sin `descripcion` la tarjeta del Dashboard quedaba con el cuerpo vacio.
        meta = construir_metadatos({"clean_title": "Go", "clean_intro": "Concurrencia."})
        assert meta["descripcion"] == "Concurrencia."

    def test_nunca_devuelve_none_porque_chroma_lo_rechaza(self):
        meta = construir_metadatos({})
        assert all(v is not None for v in meta.values())
        assert meta["titulo"] == "Sin titulo"

    def test_recorta_los_campos_largos(self):
        meta = construir_metadatos({"clean_title": "X", "clean_intro": "a" * 900})
        assert len(meta["descripcion"]) == 500


class TestPreparacionDelLote:
    def test_documentos_metadatos_e_ids_quedan_alineados(self):
        # La preocupacion de "index drift": aqui se garantiza por construccion,
        # porque las tres listas crecen en el mismo paso del bucle.
        cursos = [
            {"clean_title": "Python Basico", "clean_intro": "Variables y funciones."},
            {"full_text": "   "},  # se descarta
            {"clean_title": "Java Avanzado", "clean_intro": "Streams y concurrencia."},
        ]
        docs, metas, ids, descartados = preparar_lote(cursos)

        assert len(docs) == len(metas) == len(ids) == 2
        assert descartados == 1
        assert metas[0]["titulo"] == "Python Basico"
        assert metas[1]["titulo"] == "Java Avanzado"

    def test_los_ids_conservan_la_posicion_original_del_dataset(self):
        # `curso_2` debe seguir apuntando al registro 2 aunque el 1 se descarte.
        cursos = [
            {"clean_title": "Uno", "clean_intro": "Primer curso de la lista."},
            {"full_text": "  "},
            {"clean_title": "Tres", "clean_intro": "Tercer curso de la lista."},
        ]
        _, _, ids, _ = preparar_lote(cursos)
        assert ids == ["curso_0", "curso_2"]

    def test_los_ids_son_unicos(self):
        cursos = [{"clean_title": f"Curso {i}", "clean_intro": "Contenido de prueba."}
                  for i in range(50)]
        _, _, ids, _ = preparar_lote(cursos)
        assert len(set(ids)) == 50

    def test_un_lote_totalmente_invalido_no_produce_nada(self):
        docs, metas, ids, descartados = preparar_lote([{"full_text": "  "}, {"Title": "nan"}])
        assert (docs, metas, ids) == ([], [], [])
        assert descartados == 2


# ===========================================================================
# 2. Conversion de distancia a puntaje
# ===========================================================================


class TestPuntaje:
    """
    Solo tiene sentido si la coleccion usa `hnsw:space="cosine"`. El indice
    original quedo en L2 (distancia no acotada), por lo que era imposible
    derivar un `match_score` en [0, 1] — y de hecho no se calculaba ninguno.
    """

    @pytest.mark.parametrize(
        "distancia, esperado",
        [(0.0, 1.0), (0.25, 0.75), (0.5, 0.5), (1.0, 0.0)],
    )
    def test_invierte_la_distancia_coseno(self, distancia, esperado):
        assert distancia_a_puntaje(distancia) == pytest.approx(esperado)

    @pytest.mark.parametrize("distancia", [1.5, 2.0, 99.0])
    def test_acota_en_cero_las_distancias_grandes(self, distancia):
        # Con un indice mal construido (L2) las distancias se disparan; el
        # puntaje satura en 0 en vez de volverse negativo.
        assert distancia_a_puntaje(distancia) == 0.0

    def test_acota_en_uno_las_distancias_negativas(self):
        assert distancia_a_puntaje(-0.3) == 1.0


# ===========================================================================
# 3. Servicio de busqueda
# ===========================================================================


class TestBusquedaDevuelveLosCursosCorrectos:
    def test_devuelve_los_cursos_relevantes(self, buscador):
        resultados = buscador.buscar("ciencia de datos con python")
        titulos = [r["title"] for r in resultados]
        assert "Python para Ciencia de Datos" in titulos
        assert "Pandas y NumPy desde cero" in titulos

    def test_ordena_de_mayor_a_menor_afinidad(self, buscador):
        puntajes = [r["match_score"] for r in buscador.buscar("python")]
        assert puntajes == sorted(puntajes, reverse=True)
        assert puntajes[0] == pytest.approx(0.90)

    def test_respeta_el_limite(self, buscador):
        assert len(buscador.buscar("python", limite=2)) == 2

    def test_pide_candidatos_de_mas_para_compensar_los_filtrados(self, buscador):
        # Sin sobremuestreo, pedir 2 y filtrar 1 devolveria 1 solo resultado.
        buscador.buscar("python", limite=2)
        _, pedidos = buscador._almacen.consultas[-1]
        assert pedidos > 2

    def test_el_contrato_trae_todas_las_claves_del_dashboard(self, buscador):
        resultado = buscador.buscar("python")[0]
        assert set(resultado) == {
            "id", "title", "description", "category", "url", "site", "image", "match_score"
        }

    def test_tolera_metadatos_incompletos_de_un_indice_antiguo(self):
        # Un indice construido con el script viejo no trae `descripcion`.
        almacen = AlmacenFalso([{"id": "c1", "distancia": 0.1, "metadatos": {"titulo": "X"}}])
        resultado = BuscadorCursos(almacen).buscar("algo")[0]
        assert resultado["description"] == ""
        assert resultado["category"] == "Otras Areas"
        assert resultado["title"] == "X"


class TestConsultasVacias:
    """
    Vectorizar una cadena vacia produce un vector arbitrario que casa con
    cursos al azar. La version original la enviaba tal cual al indice.
    """

    @pytest.mark.parametrize("consulta", ["", "   ", "\n\t", None])
    def test_no_consulta_el_indice_y_devuelve_lista_vacia(self, buscador, consulta):
        assert buscador.buscar(consulta) == []
        assert buscador._almacen.consultas == []  # ni siquiera se toco el indice


class TestConsultasDeBajaRelevancia:
    """El `min_score` que faltaba: sin el, los 5 cursos volvian siempre."""

    def test_descarta_los_cursos_bajo_el_umbral_por_defecto(self, buscador):
        titulos = [r["title"] for r in buscador.buscar("aprender a programar")]
        assert "Cocina mediterranea" not in titulos       # score 0.20
        assert "Historia del arte barroco" not in titulos  # score 0.05

    def test_todos_los_resultados_superan_el_umbral(self, buscador):
        for r in buscador.buscar("datos", min_score=0.5):
            assert r["match_score"] >= 0.5

    def test_un_umbral_alto_puede_no_devolver_nada(self, buscador):
        assert buscador.buscar("datos", min_score=0.95) == []

    def test_una_consulta_sin_coincidencias_devuelve_lista_vacia_no_error(self):
        almacen = AlmacenFalso([curso("c1", 0.99, "Jardineria")])
        assert BuscadorCursos(almacen).buscar("kubernetes") == []

    def test_umbral_cero_desactiva_el_filtro_para_depurar(self, buscador):
        assert len(buscador.buscar("cualquier cosa", limite=10, min_score=0.0)) == 5

    def test_un_indice_vacio_no_revienta(self):
        buscador = BuscadorCursos(AlmacenFalso([]))
        assert buscador.buscar("python") == []
        assert buscador.disponible is False


# ===========================================================================
# 4. Ruta HTTP
# ===========================================================================


class TestRutaBuscarCursos:
    def test_responde_200_con_el_contrato_completo(self, cliente_con_catalogo):
        respuesta = cliente_con_catalogo.get("/cursos/buscar", params={"q": "python"})
        assert respuesta.status_code == 200

        cuerpo = respuesta.json()
        assert cuerpo["busqueda"] == "python"
        assert cuerpo["total"] == len(cuerpo["resultados"])
        assert cuerpo["total_indexado"] == 5

        primero = cuerpo["resultados"][0]
        assert set(primero) == {
            "id", "title", "description", "category", "url", "site", "image", "match_score"
        }
        assert 0.0 <= primero["match_score"] <= 1.0

    def test_la_ruta_esta_declarada_una_sola_vez(self):
        # Estaba duplicada en `routers/contenido.py`: la segunda definicion
        # quedaba inalcanzable y ensuciaba el OpenAPI.
        rutas = [r for r in app.routes if getattr(r, "path", None) == "/cursos/buscar"]
        assert len(rutas) == 1

    def test_acepta_el_parametro_min_score(self, cliente_con_catalogo):
        estricta = cliente_con_catalogo.get(
            "/cursos/buscar", params={"q": "python", "min_score": 0.85}
        ).json()
        laxa = cliente_con_catalogo.get(
            "/cursos/buscar", params={"q": "python", "min_score": 0.0}
        ).json()
        assert estricta["total"] < laxa["total"]
        assert estricta["min_score"] == 0.85

    def test_respeta_el_limite(self, cliente_con_catalogo):
        cuerpo = cliente_con_catalogo.get(
            "/cursos/buscar", params={"q": "python", "limite": 1}
        ).json()
        assert cuerpo["total"] == 1

    @pytest.mark.parametrize(
        "params",
        [{}, {"q": ""}, {"q": "python", "limite": 0}, {"q": "python", "limite": 99},
         {"q": "python", "min_score": 1.5}, {"q": "python", "min_score": -0.1}],
        ids=["sin-q", "q-vacia", "limite-0", "limite-99", "score-alto", "score-negativo"],
    )
    def test_rechaza_parametros_invalidos_con_422(self, cliente_con_catalogo, params):
        assert cliente_con_catalogo.get("/cursos/buscar", params=params).status_code == 422

    def test_sin_coincidencias_responde_200_con_lista_vacia(self, client):
        # "No encontre nada" es un estado normal, no un error.
        app.dependency_overrides[get_buscador_cursos] = lambda: BuscadorCursos(
            AlmacenFalso([curso("c1", 0.99, "Jardineria")])
        )
        try:
            respuesta = client.get("/cursos/buscar", params={"q": "kubernetes"})
            assert respuesta.status_code == 200
            assert respuesta.json()["total"] == 0
            assert respuesta.json()["resultados"] == []
        finally:
            app.dependency_overrides.pop(get_buscador_cursos, None)

    def test_sin_indice_disponible_responde_200_vacio_y_no_500(self, client):
        # En OCI sin la base vectorial montada, el Dashboard debe seguir vivo.
        app.dependency_overrides[get_buscador_cursos] = lambda: BuscadorCursos(
            AlmacenFalso([], disponible=False)
        )
        try:
            respuesta = client.get("/cursos/buscar", params={"q": "python"})
            assert respuesta.status_code == 200
            assert respuesta.json() == {
                "busqueda": "python",
                "total": 0,
                "min_score": pytest.approx(0.35),
                "total_indexado": 0,
                "resultados": [],
            }
        finally:
            app.dependency_overrides.pop(get_buscador_cursos, None)


# ===========================================================================
# 5. Almacen ChromaDB (sin depender de que la base exista)
# ===========================================================================


class TestAlmacenChroma:
    def test_degrada_sin_lanzar_si_no_existe_el_indice(self, tmp_path):
        from app.busqueda.almacen import AlmacenChroma

        almacen = AlmacenChroma(ruta=str(tmp_path / "no_existe"))
        assert almacen.esta_disponible() is False
        assert almacen.total() == 0
        assert almacen.consultar("python", 5) == []

    def test_solo_intenta_abrir_el_indice_una_vez(self, tmp_path):
        # Sin memorizar el fallo, cada peticion reintentaria cargar el modelo.
        from app.busqueda.almacen import AlmacenChroma

        almacen = AlmacenChroma(ruta=str(tmp_path / "no_existe"))
        almacen.total()
        almacen.total()
        assert almacen._intentado is True

    def test_normaliza_la_respuesta_anidada_de_chroma(self):
        from app.busqueda.almacen import AlmacenChroma

        crudo = {
            "ids": [["c1", "c2"]],
            "distances": [[0.1, 0.4]],
            "metadatas": [[{"titulo": "A"}, {"titulo": "B"}]],
            "documents": [["texto A", "texto B"]],
        }
        normalizado = AlmacenChroma._normalizar(crudo)
        assert normalizado[0] == {
            "id": "c1", "distancia": 0.1,
            "metadatos": {"titulo": "A"}, "documento": "texto A",
        }

    def test_no_empareja_mal_cuando_chroma_omite_documents(self):
        from app.busqueda.almacen import AlmacenChroma

        crudo = {
            "ids": [["c1", "c2"]],
            "distances": [[0.1, 0.4]],
            "metadatas": [[{"titulo": "A"}, {"titulo": "B"}]],
            "documents": [[]],
        }
        normalizado = AlmacenChroma._normalizar(crudo)
        assert len(normalizado) == 2
        assert [r["id"] for r in normalizado] == ["c1", "c2"]
        assert [r["metadatos"]["titulo"] for r in normalizado] == ["A", "B"]

    def test_una_respuesta_vacia_no_revienta(self):
        from app.busqueda.almacen import AlmacenChroma

        assert AlmacenChroma._normalizar({}) == []
        assert AlmacenChroma._normalizar({"ids": [[]]}) == []


# ===========================================================================
# 6. Contrato real contra ChromaDB
# ===========================================================================


class TestIntegracionChromaReal:
    """
    Verifica contra ChromaDB de verdad que la metrica coseno produce las
    distancias que `distancia_a_puntaje` asume.

    Se usa una funcion de embeddings determinista en vez del
    `SentenceTransformer` real: el contrato que hay que probar es
    "cosine -> distancia en [0,2] -> puntaje en [0,1]", no la calidad del
    modelo. Asi la prueba corre en milisegundos y sin descargar 2 GB.

    Se omite si `chromadb` no esta instalado, para que la suite siga verde en
    un entorno minimo.
    """

    @staticmethod
    def _indice(tmp_path, espacio: str):
        chromadb = pytest.importorskip("chromadb")
        from chromadb.api.types import EmbeddingFunction

        class EmbeddingsFijos(EmbeddingFunction):
            """Vectores 3D escogidos a mano para conocer los angulos exactos."""

            TABLA = {
                "python para datos": [1.0, 0.0, 0.0],
                "analisis de datos con python": [1.0, 0.0, 0.0],   # identico
                "pandas y numpy": [0.7071, 0.7071, 0.0],           # 45 grados
                "cocina mediterranea": [0.0, 1.0, 0.0],            # 90 grados
            }

            def __call__(self, input):
                return [self.TABLA.get(t, [0.0, 0.0, 1.0]) for t in input]

            def name(self):  # requerido por chromadb >= 1.x
                return "embeddings_fijos"

        cliente = chromadb.PersistentClient(path=str(tmp_path / espacio))
        coleccion = cliente.create_collection(
            name="athenex_courses",
            embedding_function=EmbeddingsFijos(),
            metadata={"hnsw:space": espacio},
        )
        coleccion.add(
            documents=["python para datos", "pandas y numpy", "cocina mediterranea"],
            metadatas=[
                {"titulo": "Python para Datos", "descripcion": "Curso base.",
                 "categoria": "Ciencia de Datos y Analitica", "url": "https://e.com/1",
                 "sitio": "Coursera"},
                {"titulo": "Pandas y NumPy", "descripcion": "Manipulacion.",
                 "categoria": "Ciencia de Datos y Analitica", "url": "https://e.com/2",
                 "sitio": "edX"},
                {"titulo": "Cocina Mediterranea", "descripcion": "Recetas.",
                 "categoria": "Otras Areas", "url": "https://e.com/3", "sitio": "Udemy"},
            ],
            ids=["curso_0", "curso_1", "curso_2"],
        )
        return coleccion

    def test_la_metrica_coseno_produce_los_puntajes_esperados(self, tmp_path):
        coleccion = self._indice(tmp_path, "cosine")
        assert coleccion.metadata.get("hnsw:space") == "cosine"

        crudo = coleccion.query(
            query_texts=["analisis de datos con python"],
            n_results=3,
            include=["metadatas", "distances", "documents"],
        )

        from app.busqueda.almacen import AlmacenChroma

        normalizado = AlmacenChroma._normalizar(crudo)
        puntajes = {r["metadatos"]["titulo"]: distancia_a_puntaje(r["distancia"])
                    for r in normalizado}

        # Vector identico -> distancia 0 -> puntaje 1.0
        assert puntajes["Python para Datos"] == pytest.approx(1.0, abs=1e-4)
        # 45 grados -> distancia 1-cos(45) ~= 0.293 -> puntaje ~= 0.707
        assert puntajes["Pandas y NumPy"] == pytest.approx(0.7071, abs=1e-3)
        # 90 grados -> distancia 1 -> puntaje 0.0
        assert puntajes["Cocina Mediterranea"] == pytest.approx(0.0, abs=1e-4)

    def test_el_umbral_por_defecto_descarta_lo_irrelevante(self, tmp_path):
        """El escenario del reporte: el curso de cocina no debe aparecer."""
        coleccion = self._indice(tmp_path, "cosine")

        class AlmacenSobreColeccion:
            nombre = "chromadb-prueba"

            def esta_disponible(self): return True
            def total(self): return coleccion.count()

            def consultar(self, texto, limite):
                from app.busqueda.almacen import AlmacenChroma
                return AlmacenChroma._normalizar(coleccion.query(
                    query_texts=[texto], n_results=min(limite, coleccion.count()),
                    include=["metadatas", "distances", "documents"],
                ))

        resultados = BuscadorCursos(AlmacenSobreColeccion()).buscar("analisis de datos con python")
        titulos = [r["title"] for r in resultados]

        assert titulos == ["Python para Datos", "Pandas y NumPy"]
        assert "Cocina Mediterranea" not in titulos
        assert all(r["description"] and r["url"] for r in resultados)

    def test_el_indice_l2_original_arruina_los_puntajes(self, tmp_path):
        """
        Demuestra por que habia que reconstruir el indice.

        Con la metrica L2 —la que quedo por defecto al omitir `metadata`— la
        distancia entre dos textos ortogonales es 2.0, que al convertirla
        satura en 0.0. Los puntajes dejan de ser interpretables y el umbral
        `min_score` no puede discriminar.
        """
        coleccion = self._indice(tmp_path, "l2")
        assert coleccion.metadata.get("hnsw:space") == "l2"

        crudo = coleccion.query(
            query_texts=["analisis de datos con python"], n_results=3,
            include=["metadatas", "distances"],
        )
        distancias = {m["titulo"]: d for m, d in
                      zip(crudo["metadatas"][0], crudo["distances"][0])}

        # Bajo L2 la distancia al texto ortogonal es 2.0, no 1.0 como en coseno.
        assert distancias["Cocina Mediterranea"] == pytest.approx(2.0, abs=1e-3)
        assert distancia_a_puntaje(distancias["Cocina Mediterranea"]) == 0.0

    def test_el_almacen_avisa_cuando_el_indice_no_es_coseno(self, tmp_path, caplog):
        """`AlmacenChroma` detecta en caliente el fallo de la base entregada."""
        import logging

        from app.busqueda.almacen import AlmacenChroma

        coleccion = self._indice(tmp_path, "l2")
        with caplog.at_level(logging.ERROR, logger="athenia.busqueda.almacen"):
            AlmacenChroma._verificar_metrica(coleccion)

        assert "l2" in caplog.text
        assert "build_embeddings" in caplog.text

    def test_no_avisa_cuando_el_indice_es_correcto(self, tmp_path, caplog):
        import logging

        from app.busqueda.almacen import AlmacenChroma

        coleccion = self._indice(tmp_path, "cosine")
        with caplog.at_level(logging.ERROR, logger="athenia.busqueda.almacen"):
            AlmacenChroma._verificar_metrica(coleccion)

        assert caplog.text == ""


# ===========================================================================
# 7. Duplicados y titulos-duracion (detectados con el indice real)
# ===========================================================================


class TestTitulosDuracion:
    """
    ~200 cursos traen la duracion en la columna del titulo. Salian como
    tarjetas tituladas "4 hours" en el Dashboard.
    """

    @pytest.mark.parametrize("titulo", ["4 hours", "5 Hours", "45 min", "3 semanas"])
    def test_descarta_un_titulo_que_es_una_duracion(self, titulo):
        item = {"clean_title": titulo, "Title": "Introduccion a Kubernetes"}
        assert primer_titulo(item, "clean_title", "Title") == "Introduccion a Kubernetes"

    def test_conserva_una_duracion_dentro_de_un_titulo_real(self):
        item = {"clean_title": "Python en 4 hours: curso express"}
        assert primer_titulo(item, "clean_title") == "Python en 4 hours: curso express"

    def test_cae_al_defecto_si_todos_los_titulos_son_duraciones(self):
        assert primer_titulo({"clean_title": "4 hours", "Title": "2 hrs"},
                             "clean_title", "Title") == "Sin titulo"

    def test_los_metadatos_no_llevan_un_titulo_duracion(self):
        meta = construir_metadatos({"clean_title": "4 hours", "Title": "Docker Avanzado"})
        assert meta["titulo"] == "Docker Avanzado"


class TestDeduplicacion:
    def test_el_indexado_descarta_las_filas_con_texto_identico(self):
        # 3.293 filas del dataset repiten exactamente el texto de otra.
        curso_a = {"clean_title": "Ethical Hacking", "clean_intro": "Introduccion al hacking etico."}
        docs, metas, ids, descartados = preparar_lote([curso_a, dict(curso_a), dict(curso_a)])
        assert len(docs) == 1
        assert descartados == 2
        assert ids == ["curso_0"]  # se conserva la primera aparicion

    def test_el_indexado_conserva_cursos_distintos(self):
        docs, _, _, descartados = preparar_lote([
            {"clean_title": "Python Basico", "clean_intro": "Variables y funciones."},
            {"clean_title": "Java Basico", "clean_intro": "Clases y objetos."},
        ])
        assert len(docs) == 2 and descartados == 0

    def test_la_busqueda_no_repite_el_mismo_titulo(self):
        # Escenario real: "hacking etico" devolvia 3 copias del mismo curso.
        repetidos = [
            curso("c1", 0.10, "Ethical Hacking: An Introduction"),
            curso("c2", 0.11, "Ethical Hacking: An Introduction"),
            curso("c3", 0.12, "ETHICAL HACKING: an introduction"),  # distinto case
            curso("c4", 0.20, "Network Security Basics"),
        ]
        resultados = BuscadorCursos(AlmacenFalso(repetidos)).buscar("hacking etico")
        titulos = [r["title"] for r in resultados]
        assert len(titulos) == 2
        assert titulos[0] == "Ethical Hacking: An Introduction"
        assert titulos[1] == "Network Security Basics"

    def test_la_deduplicacion_conserva_el_de_mayor_puntaje(self):
        repetidos = [
            curso("c1", 0.40, "Docker", url="https://peor.com"),
            curso("c2", 0.10, "Docker", url="https://mejor.com"),
        ]
        resultado = BuscadorCursos(AlmacenFalso(repetidos)).buscar("docker")[0]
        assert resultado["url"] == "https://mejor.com"
        assert resultado["match_score"] == pytest.approx(0.90)


# ===========================================================================
# 8. Navegacion del catalogo (GET /cursos)
# ===========================================================================


CLAVES_CURSO = {"id", "title", "description", "category", "url", "site", "image", "match_score"}


class TestNavegacionDelCatalogo:
    """
    El endpoint que faltaba. Sin el, una vista sin consulta caia a
    `GET /contenidos` —el historial, con 8 registros de demo— y parecia que el
    catalogo de +8.000 cursos no estuviera conectado al frontend.
    """

    def test_devuelve_cursos_sin_consulta(self, buscador):
        items = buscador.listar(limite=3)
        assert len(items) == 3
        assert all(set(i) == CLAVES_CURSO for i in items)

    def test_el_puntaje_es_nulo_al_navegar(self, buscador):
        # `None` significa "no se midio", que no es lo mismo que 0.0
        # ("se midio y no se parece"). La tarjeta oculta el badge con `None`.
        assert all(i["match_score"] is None for i in buscador.listar())

    def test_filtra_por_categoria(self):
        almacen = AlmacenFalso([
            curso("c1", 0.1, "Kubernetes", categoria="Cloud Computing y DevOps"),
            curso("c2", 0.2, "Pandas", categoria="Ciencia de Datos y Analitica"),
        ])
        items = BuscadorCursos(almacen).listar(categoria="Cloud Computing y DevOps")
        assert [i["title"] for i in items] == ["Kubernetes"]

    def test_pagina_con_desplazamiento(self, buscador):
        primera = buscador.listar(limite=2, desplazamiento=0)
        segunda = buscador.listar(limite=2, desplazamiento=2)
        assert [i["id"] for i in primera] != [i["id"] for i in segunda]

    def test_un_indice_vacio_devuelve_lista_vacia(self):
        assert BuscadorCursos(AlmacenFalso([])).listar() == []

    def test_agrega_las_categorias_con_su_conteo(self):
        almacen = AlmacenFalso([
            curso("c1", 0.1, "A", categoria="Cloud Computing y DevOps"),
            curso("c2", 0.2, "B", categoria="Cloud Computing y DevOps"),
            curso("c3", 0.3, "C", categoria="Ciberseguridad y Redes"),
        ])
        assert BuscadorCursos(almacen).categorias() == [
            {"nombre": "Cloud Computing y DevOps", "total": 2},
            {"nombre": "Ciberseguridad y Redes", "total": 1},
        ]


class TestRutaCatalogo:
    def test_get_cursos_responde_200_con_el_contrato(self, cliente_con_catalogo):
        respuesta = cliente_con_catalogo.get("/cursos", params={"limite": 3})
        assert respuesta.status_code == 200

        cuerpo = respuesta.json()
        assert cuerpo["total"] == len(cuerpo["items"]) == 3
        assert cuerpo["total_indexado"] == 5
        assert cuerpo["categoria"] is None
        assert set(cuerpo["items"][0]) == CLAVES_CURSO
        assert cuerpo["items"][0]["match_score"] is None

    def test_get_cursos_categorias_responde_200(self, cliente_con_catalogo):
        cuerpo = cliente_con_catalogo.get("/cursos/categorias").json()
        assert cuerpo["total"] == len(cuerpo["items"]) >= 1
        assert set(cuerpo["items"][0]) == {"nombre", "total"}

    def test_la_ruta_de_categorias_no_la_captura_una_ruta_con_parametro(self):
        # `/cursos/categorias` y `/cursos/buscar` deben resolverse como rutas
        # literales. Starlette resuelve por orden de registro: si algun dia se
        # anade `/cursos/{curso_id}` antes, capturaria ambas como si fueran ids.
        rutas = [getattr(r, "path", "") for r in app.routes]
        for literal in ("/cursos/buscar", "/cursos/categorias"):
            assert rutas.count(literal) == 1
            con_parametro = [r for r in rutas if r.startswith("/cursos/{")]
            if con_parametro:
                assert rutas.index(literal) < min(rutas.index(p) for p in con_parametro)

    @pytest.mark.parametrize(
        "params",
        [{"limite": 0}, {"limite": 101}, {"desplazamiento": -1}],
        ids=["limite-0", "limite-101", "desplazamiento-negativo"],
    )
    def test_rechaza_parametros_invalidos_con_422(self, cliente_con_catalogo, params):
        assert cliente_con_catalogo.get("/cursos", params=params).status_code == 422

    def test_sin_indice_responde_200_vacio_y_no_500(self, client):
        app.dependency_overrides[get_buscador_cursos] = lambda: BuscadorCursos(
            AlmacenFalso([], disponible=False)
        )
        try:
            respuesta = client.get("/cursos")
            assert respuesta.status_code == 200
            assert respuesta.json()["items"] == []
        finally:
            app.dependency_overrides.pop(get_buscador_cursos, None)


class TestCampoImagen:
    """
    `image` forma parte del contrato aunque el dataset entregado por Data no
    traiga ninguna columna de imagen (se revisaron las 52). Viaja vacio para
    que el frontend no tenga que cambiar cuando el ETL la incorpore.
    """

    def test_viaja_vacio_cuando_el_dataset_no_la_trae(self, buscador):
        assert all(i["image"] == "" for i in buscador.buscar("python"))

    def test_se_propaga_si_el_indice_la_tiene(self):
        almacen = AlmacenFalso([curso("c1", 0.1, "Go", imagen="https://cdn.com/go.png")])
        assert BuscadorCursos(almacen).buscar("go")[0]["image"] == "https://cdn.com/go.png"
