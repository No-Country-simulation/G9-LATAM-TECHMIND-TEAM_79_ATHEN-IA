"""
Configuracion compartida de pytest - QA AthenIA.
================================================

Responsabilidades:

  1. Desactivar la semilla de demo ANTES de importar la app, para que cada
     prueba parta de un historial vacio y predecible.
  2. Agregar `backend/` al `sys.path` para que `from app.main import app`
     funcione sin instalar el backend como paquete.
  3. Forzar el motor por reglas como estado por defecto de la suite, de modo
     que las pruebas de clasificacion no cambien de resultado el dia que Data
     Science deje su `.pkl` en `backend/models/`.
  4. Exponer el `TestClient`, payloads de referencia y artefactos de modelo
     entrenados al vuelo como fixtures.
"""

import os
import sys
from pathlib import Path

# --- 1. El entorno debe quedar fijado ANTES de importar la aplicacion ------
# `config.Settings` se resuelve en tiempo de import, asi que este orden importa.
os.environ.setdefault("ATHENIA_SEED_DEMO", "false")
os.environ.setdefault("ATHENIA_ENV", "test")
os.environ.setdefault("ATHENIA_LOG_LEVEL", "WARNING")

# --- 2. Rutas --------------------------------------------------------------
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import services  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402


# ===========================================================================
# Estado base de la suite
# ===========================================================================


@pytest.fixture(scope="session", autouse=True)
def motor_por_reglas(tmp_path_factory):
    """
    Apunta la busqueda de modelos a una carpeta vacia durante toda la suite.

    Sin esto, las pruebas de clasificacion (CP-13 a CP-15) pasarian a evaluar
    la precision del modelo de Data Science en cuanto apareciera el `.pkl`, y
    romperian sin que nadie hubiera tocado el backend. Las pruebas que SI
    necesitan el modelo real lo montan explicitamente con `modelo_ml_real`.
    """
    vacia = tmp_path_factory.mktemp("modelos_vacios")

    modelos_dir_original = settings.MODELOS_DIR
    modelo_path_original = settings.MODELO_PATH

    settings.MODELOS_DIR = vacia
    settings.MODELO_PATH = None
    services.recargar_clasificador()

    yield

    settings.MODELOS_DIR = modelos_dir_original
    settings.MODELO_PATH = modelo_path_original
    services.recargar_clasificador()


@pytest.fixture(scope="session")
def client(motor_por_reglas) -> TestClient:
    """Cliente HTTP contra la app FastAPI, sin levantar un servidor real."""
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture(autouse=True)
def historial_limpio():
    """
    Vacia el historial antes de cada prueba.

    `autouse` para que ninguna prueba dependa del orden de ejecucion ni de los
    contenidos que hayan guardado las anteriores.
    """
    services.repositorio.limpiar()
    yield
    services.repositorio.limpiar()


# ===========================================================================
# Payloads de referencia
# ===========================================================================


@pytest.fixture
def payload_valido() -> dict:
    """Payload de referencia de QA (caso feliz: contenido de Backend)."""
    return {
        "titulo": "Introduccion a Spring Boot",
        "texto": (
            "En este curso aprenderas a desarrollar APIs REST con Spring Boot, "
            "implementando buenas practicas, autenticacion con JWT, manejo de "
            "excepciones y conexion a bases de datos con Spring Data JPA."
        ),
    }


@pytest.fixture
def historial_poblado(client, payload_valido) -> list:
    """
    Crea tres analisis de categorias distintas y devuelve sus respuestas.

    Base comun para las pruebas de `GET /contenidos` y `GET /metricas`.
    """
    entradas = [
        payload_valido,
        {
            "titulo": "Docker para Principiantes",
            "texto": "Conceptos de contenedores, Dockerfile, Kubernetes y CI/CD.",
        },
        {
            "titulo": "Machine Learning con Python",
            "texto": "Modelos con Scikit-Learn, Pandas y NLP usando TF-IDF.",
        },
    ]
    return [client.post("/contenido", json=entrada).json() for entrada in entradas]


# ===========================================================================
# Artefactos de modelo para las pruebas de integracion ML
# ===========================================================================

# Corpus minimo pero linealmente separable: basta para que el pipeline aprenda
# a distinguir las tres categorias y las aserciones sean estables.
CORPUS_ENTRENAMIENTO = [
    ("APIs REST con Java y Spring Boot, seguridad con JWT y JPA", "Backend"),
    ("Servicios backend en Spring Boot con endpoints REST y Maven", "Backend"),
    ("Microservicios Java, Spring Security y bases de datos JPA", "Backend"),
    ("Construir endpoints REST seguros con Java y Spring", "Backend"),
    ("Modelos de machine learning con Python, Pandas y Scikit-Learn", "Data Science"),
    ("Analisis de datos en Python usando Pandas, NumPy y TF-IDF", "Data Science"),
    ("Entrenamiento de modelos predictivos con Scikit-Learn y NLP", "Data Science"),
    ("Ciencia de datos con Python: Pandas, estadistica y modelos", "Data Science"),
    ("Contenedores Docker, Kubernetes y pipelines CI/CD", "DevOps"),
    ("Orquestacion con Kubernetes, Dockerfile y despliegue continuo", "DevOps"),
    ("Docker, Jenkins y automatizacion de despliegues en Linux", "DevOps"),
    ("Infraestructura con Docker, Kubernetes y monitoreo", "DevOps"),
]


def _construir_pipeline():
    """Entrena un `Pipeline` real de scikit-learn (TF-IDF + regresion logistica)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    textos = [texto for texto, _ in CORPUS_ENTRENAMIENTO]
    etiquetas = [etiqueta for _, etiqueta in CORPUS_ENTRENAMIENTO]

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(textos, etiquetas)
    return pipeline


def _construir_piezas_sueltas():
    """Entrena vectorizador y clasificador por separado, como los entrega un notebook."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    textos = [texto for texto, _ in CORPUS_ENTRENAMIENTO]
    etiquetas = [etiqueta for _, etiqueta in CORPUS_ENTRENAMIENTO]

    vectorizador = TfidfVectorizer(ngram_range=(1, 2))
    matriz = vectorizador.fit_transform(textos)

    modelo = LogisticRegression(max_iter=1000)
    modelo.fit(matriz, etiquetas)

    return modelo, vectorizador


@pytest.fixture
def activar_artefacto():
    """
    Fabrica que serializa un artefacto, lo activa y restaura el estado al final.

    Uso:
        def test_algo(activar_artefacto, client):
            activar_artefacto(mi_objeto, nombre="clasificador_cursos.pkl")
            ...
    """
    original_path = settings.MODELO_PATH
    original_dir = settings.MODELOS_DIR
    creados = []

    def _activar(artefacto, ruta: Path, usar_pickle: bool = False, autodetectar: bool = False):
        """
        Guarda `artefacto` en `ruta` y recarga el motor de clasificacion.

        `usar_pickle=True`   -> serializa con `pickle` en vez de `joblib`.
        `autodetectar=True`  -> no fija ATHENIA_MODELO_PATH; obliga al backend
                                a encontrar el archivo por nombre en la carpeta.
        """
        ruta.parent.mkdir(parents=True, exist_ok=True)

        if usar_pickle:
            import pickle

            with open(ruta, "wb") as archivo:
                pickle.dump(artefacto, archivo)
        else:
            import joblib

            joblib.dump(artefacto, ruta)

        creados.append(ruta)

        if autodetectar:
            settings.MODELO_PATH = None
            settings.MODELOS_DIR = ruta.parent
        else:
            settings.MODELO_PATH = ruta

        return services.recargar_clasificador()

    yield _activar

    # Restaura el motor por reglas para las pruebas siguientes.
    settings.MODELO_PATH = original_path
    settings.MODELOS_DIR = original_dir
    services.recargar_clasificador()


#: Ubicacion del artefacto que entrega Data Science.
ARTEFACTO_REAL = BACKEND / "models" / "clasificador_cursos.pkl"


@pytest.fixture
def artefacto_real():
    """
    Activa el `clasificador_cursos.pkl` REAL del repositorio.

    Se salta la prueba si el archivo no esta: los `.pkl` viven en `.gitignore`
    y se distribuyen por OCI Object Storage, asi que un clon limpio no lo
    tiene. La suite nunca debe fallar por eso.
    """
    if not ARTEFACTO_REAL.exists():
        pytest.skip(
            f"Artefacto real no disponible en {ARTEFACTO_REAL}. "
            "Descargalo de OCI Object Storage para ejecutar estas pruebas."
        )

    original_path = settings.MODELO_PATH
    original_dir = settings.MODELOS_DIR

    settings.MODELO_PATH = ARTEFACTO_REAL
    motor = services.recargar_clasificador()

    # Si el artefacto existe pero no supera la carga o la sonda, es un fallo
    # real que QA debe ver, no un motivo para saltar la prueba.
    assert motor.motor == "modelo_ml_real", (
        f"El artefacto real existe pero no se activo: motor={motor.motor}. "
        "Revisa los logs del backend (version de scikit-learn, estructura del pickle)."
    )

    yield ARTEFACTO_REAL

    settings.MODELO_PATH = original_path
    settings.MODELOS_DIR = original_dir
    services.recargar_clasificador()


@pytest.fixture
def modelo_ml_real(activar_artefacto, tmp_path):
    """
    Activa un `Pipeline` real entrenado, guardado como `clasificador_cursos.pkl`.

    Reproduce el escenario de la Semana 3: el artefacto de Data Science ya esta
    en su sitio y el backend debe usarlo.
    """
    pytest.importorskip("sklearn", reason="scikit-learn es necesario para las pruebas de ML")

    ruta = tmp_path / "models" / "clasificador_cursos.pkl"
    activar_artefacto(_construir_pipeline(), ruta)
    return ruta
