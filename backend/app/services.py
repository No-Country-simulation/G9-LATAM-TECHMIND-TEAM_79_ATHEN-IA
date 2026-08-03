"""
Capa de servicios de AthenIA.
=============================

Contiene toda la logica de negocio, aislada de HTTP:

  1. **Taxonomia**        - categorias y tecnologias que reconoce el MVP.
  2. **Clasificacion**    - `ClasificadorReglas` (fallback) y `ClasificadorML`.
  3. **Keywords**         - extraccion de tecnologias presentes en el texto.
  4. **Persistencia**     - `RepositorioContenidos`, historial en memoria.
  5. **Metricas**         - agregados que alimentan el Dashboard.

Motores de clasificacion
------------------------
| Motor                 | Clase                | Cuando se usa                    |
|-----------------------|----------------------|----------------------------------|
| `modelo_ml_real`      | `ClasificadorML`     | Hay un artefacto valido cargado.  |
| `clasificador_reglas` | `ClasificadorReglas` | Fallback en cualquier otro caso.  |

`GET /salud` reporta cual esta activo en el campo `motor`.

Mecanismo de fallback (4 etapas)
--------------------------------
`obtener_clasificador()` degrada a reglas si falla cualquiera de estas etapas:

  1. **Localizar**    el artefacto en `backend/models/`.
  2. **Deserializar** con joblib y, si falla, con pickle.
  3. **Adaptar**      la estructura entregada (Pipeline, dict o tupla).
  4. **Sondear**      con una prediccion de prueba antes de exponerlo.

Ademas, `ClasificadorML.clasificar()` captura los errores de inferencia en
tiempo de ejecucion. La API nunca devuelve 500 por culpa del modelo.

Integracion del modelo real (Semana 3)
--------------------------------------
Basta con dejar `clasificador_cursos.pkl` en `backend/models/`. No hay que
tocar rutas, esquemas ni frontend. Ver `backend/models/README.md`.
"""

from __future__ import annotations

import logging
import re
import threading
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import settings

logger = logging.getLogger("athenia.services")

# Probabilidad reportada cuando el modelo real no expone `predict_proba`.
PROBABILIDAD_SIN_PROBA = 0.75

# Confianza asignada cuando no se detecta ninguna tecnologia conocida.
PROBABILIDAD_SIN_EVIDENCIA = 0.35

# Cuantas categorias alternativas se reportan y con que probabilidad minima.
# Por debajo del umbral la alternativa es ruido y solo confunde al usuario.
MAX_CATEGORIAS_RELACIONADAS = 3
UMBRAL_CATEGORIA_RELACIONADA = 0.05

CATEGORIA_POR_DEFECTO = "Otros"


# ===========================================================================
# 1. Taxonomia del MVP
# ===========================================================================
# Cada categoria mapea a las tecnologias que la delatan. Las claves internas
# son las palabras clave EXACTAS que se devuelven en `informacion_adicional`
# (con el casing bonito para la UI); los valores son los patrones en
# minusculas y sin acentos que se buscan en el texto normalizado.

TAXONOMIA: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "Backend": {
        "Java": ("java", "jdk", "jvm"),
        "Spring Boot": ("spring boot", "springboot", "spring-boot"),
        "Spring Security": ("spring security",),
        "Spring Data JPA": ("spring data", "jpa", "hibernate"),
        # Se incluyen plurales y la forma suelta "rest": los limites de palabra
        # de `_contiene` impiden que "api rest" matchee dentro de "apis rest".
        "API REST": (
            "api rest",
            "apis rest",
            "rest api",
            "rest",
            "restful",
            "endpoint",
            "endpoints",
        ),
        "Microservicios": ("microservicio", "microservicios", "microservice"),
        "Node.js": ("node.js", "nodejs", "express"),
        "Autenticacion": ("jwt", "oauth", "autenticacion", "authentication"),
        "Maven": ("maven", "gradle"),
    },
    "Frontend": {
        "React": ("react", "jsx", "hooks"),
        "JavaScript": ("javascript", "typescript", "ecmascript"),
        "Tailwind CSS": ("tailwind",),
        "CSS": ("css", "flexbox", "grid layout"),
        "HTML": ("html",),
        "UI/UX": ("ui", "ux", "interfaz", "usabilidad", "responsive"),
        "Vite": ("vite", "webpack", "bundler"),
        "Angular": ("angular", "vue", "svelte"),
    },
    "Data Science": {
        "Python": ("python",),
        "Machine Learning": (
            "machine learning",
            "aprendizaje automatico",
            "modelo predictivo",
            "entrenamiento",
        ),
        "Scikit-Learn": ("scikit", "sklearn"),
        "Pandas": ("pandas", "dataframe", "numpy"),
        "NLP": ("nlp", "procesamiento de lenguaje", "tf-idf", "tokenizacion"),
        "Deep Learning": ("deep learning", "red neuronal", "tensorflow", "pytorch"),
        "Analitica": ("analitica", "estadistica", "visualizacion de datos"),
    },
    "DevOps": {
        "Docker": ("docker", "contenedor", "contenedores", "dockerfile"),
        "Kubernetes": ("kubernetes", "k8s", "orquestacion"),
        "CI/CD": ("ci/cd", "cicd", "integracion continua", "jenkins", "github actions"),
        "Nginx": ("nginx", "apache", "proxy inverso"),
        "Linux": ("linux", "bash", "shell"),
        "Monitoreo": ("monitoreo", "observabilidad", "prometheus", "grafana", "logs"),
    },
    "Cloud": {
        "Oracle Cloud": ("oracle cloud", "oci", "autonomous database"),
        "AWS": ("aws", "amazon web services", "s3", "lambda"),
        "Azure": ("azure",),
        "Object Storage": ("object storage", "almacenamiento de objetos", "bucket"),
        "Serverless": ("serverless", "sin servidor", "functions"),
        "Escalabilidad": ("escalabilidad", "alta disponibilidad", "load balancer"),
    },
    "Base de Datos": {
        "SQL": ("sql", "consulta", "consultas", "join"),
        "Oracle Database": ("oracle database", "oracle db", "pl/sql"),
        "PostgreSQL": ("postgresql", "postgres"),
        "MySQL": ("mysql", "mariadb"),
        "MongoDB": ("mongodb", "nosql"),
        "Modelado": ("modelado de datos", "normalizacion", "entidad relacion"),
    },
}


# ===========================================================================
# 2. Utilidades de texto
# ===========================================================================

_ACENTOS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def normalizar(texto: str) -> str:
    """Minusculas, sin acentos y con espacios colapsados."""
    return re.sub(r"\s+", " ", texto.translate(_ACENTOS).lower()).strip()


def _contiene(texto_norm: str, patron: str) -> bool:
    """
    Busca `patron` respetando limites de palabra.

    Evita falsos positivos clasicos: que "java" haga match dentro de
    "javascript", o que "ui" aparezca dentro de "construir".
    """
    return re.search(rf"(?<![a-z0-9]){re.escape(patron)}(?![a-z0-9])", texto_norm) is not None


def extraer_palabras_clave(
    titulo: str,
    texto: str,
    categoria: Optional[str] = None,
    limite: int = 8,
) -> List[str]:
    """
    Extrae las tecnologias presentes en el contenido.

    Si se indica `categoria`, solo devuelve las palabras clave de esa rama de
    la taxonomia (es lo que interesa mostrar junto a la prediccion). Sin
    categoria, recorre toda la taxonomia.

    Se usa tanto con el clasificador por reglas como con el modelo real, ya que
    un clasificador de scikit-learn devuelve la categoria pero no las
    tecnologias detectadas.
    """
    titulo_norm, texto_norm = normalizar(titulo), normalizar(texto)
    ramas = (
        {categoria: TAXONOMIA[categoria]}
        if categoria in TAXONOMIA
        else TAXONOMIA
    )

    encontradas: List[str] = []
    for keywords in ramas.values():
        for etiqueta, patrones in keywords.items():
            if any(
                _contiene(titulo_norm, p) or _contiene(texto_norm, p) for p in patrones
            ):
                encontradas.append(etiqueta)

    return encontradas[:limite]


def resumir(texto: str, limite: int = 180) -> str:
    """Recorte en el limite de palabra. Placeholder del resumen abstractivo."""
    limpio = re.sub(r"\s+", " ", texto).strip()
    if len(limpio) <= limite:
        return limpio
    return limpio[:limite].rsplit(" ", 1)[0] + "..."


def categorias_soportadas() -> List[str]:
    """Catalogo de categorias que la API puede devolver."""
    return sorted(TAXONOMIA.keys()) + [CATEGORIA_POR_DEFECTO]


# ===========================================================================
# 3. Clasificadores
# ===========================================================================


class ClasificadorBase(ABC):
    """Contrato que debe cumplir cualquier clasificador de AthenIA."""

    #: Identificador del artefacto o de la version de reglas.
    nombre: str = "base"
    #: Motor reportado por `GET /salud`: "modelo_ml_real" | "clasificador_reglas".
    motor: str = "clasificador_reglas"
    #: True mientras no haya un modelo entrenado real en uso.
    es_mock: bool = True
    #: Descripcion corta del artefacto, para diagnostico.
    detalle: str = ""

    @abstractmethod
    def clasificar(self, titulo: str, texto: str) -> dict:
        """
        Devuelve un dict compatible con `schemas.AnalisisOutput`.

        Claves obligatorias: `categoria`, `probabilidad`, `informacion_adicional`.
        """

    def categorias(self) -> List[str]:
        return categorias_soportadas()


class ClasificadorReglas(ClasificadorBase):
    """
    Clasificador por coincidencia de palabras clave.

    Es el **fallback**: se usa mientras el modelo real no este disponible, y
    tambien si la carga o la inferencia del artefacto fallan. Determinista por
    diseno, para que QA pueda escribir aserciones estables.
    """

    nombre = "reglas-keywords-v1"
    motor = "clasificador_reglas"
    es_mock = True
    detalle = "taxonomia de palabras clave"

    # El titulo suele ser mas informativo que el cuerpo, asi que sus
    # coincidencias pesan mas al puntuar.
    PESO_TITULO = 3
    PESO_TEXTO = 1

    def clasificar(self, titulo: str, texto: str) -> dict:
        titulo_norm = normalizar(titulo)
        texto_norm = normalizar(texto)

        puntajes: Counter = Counter()
        keywords_por_categoria: Dict[str, List[str]] = {}

        for categoria, keywords in TAXONOMIA.items():
            encontradas: List[str] = []
            for etiqueta, patrones in keywords.items():
                golpe_titulo = any(_contiene(titulo_norm, p) for p in patrones)
                golpe_texto = any(_contiene(texto_norm, p) for p in patrones)
                if not (golpe_titulo or golpe_texto):
                    continue
                encontradas.append(etiqueta)
                puntajes[categoria] += (self.PESO_TITULO if golpe_titulo else 0) + (
                    self.PESO_TEXTO if golpe_texto else 0
                )
            if encontradas:
                keywords_por_categoria[categoria] = encontradas

        # Sin evidencia no se fuerza una categoria tecnica.
        if not puntajes:
            return {
                "categoria": CATEGORIA_POR_DEFECTO,
                "probabilidad": PROBABILIDAD_SIN_EVIDENCIA,
                "informacion_adicional": [],
                "resumen": resumir(texto),
                "categorias_relacionadas": [],
                "modelo": self.nombre,
            }

        ordenadas = puntajes.most_common()
        categoria, mejor_puntaje = ordenadas[0]
        total = sum(puntajes.values())

        # La confianza combina cuanto domina la categoria ganadora sobre el
        # resto (`share`) y cuanta evidencia absoluta hay (`evidencia`).
        share = mejor_puntaje / total
        evidencia = min(mejor_puntaje / 12, 1.0)
        probabilidad = round(min(0.55 + 0.35 * share + 0.10 * evidencia, 0.99), 2)

        return {
            "categoria": categoria,
            "probabilidad": probabilidad,
            "informacion_adicional": keywords_por_categoria.get(categoria, [])[:8],
            "resumen": resumir(texto),
            "categorias_relacionadas": [c for c, _ in ordenadas[1:4]],
            "modelo": self.nombre,
        }


# ---------------------------------------------------------------------------
# Adaptador del artefacto entregado por Data Science
# ---------------------------------------------------------------------------


class AdaptadorModelo:
    """
    Normaliza las formas en que Data Science puede entregar el artefacto.

    El backend no puede asumir una sola estructura: segun como se haya guardado
    el modelo, `pickle.load` devuelve cosas distintas. Este adaptador detecta
    cual llego y expone siempre la misma interfaz (`predict`, `predict_proba`,
    `clases`).

    Formas soportadas
    -----------------
    1. `Pipeline` de scikit-learn que ya incluye el vectorizador:
           pipeline.predict(["texto crudo"])
    2. `dict` con el modelo y el vectorizador por separado:
           {"modelo": clf, "vectorizador": tfidf}
       (se aceptan las claves habituales en ingles y espanol)
    3. `tuple` / `list` de dos elementos, en cualquier orden:
           (tfidf, clf)  o  (clf, tfidf)
    """

    # Claves habituales con las que un notebook guarda cada pieza.
    CLAVES_MODELO = ("modelo", "model", "clf", "classifier", "clasificador", "estimator")
    CLAVES_VECTORIZADOR = ("vectorizador", "vectorizer", "tfidf", "vec", "transformer")

    def __init__(self, artefacto) -> None:
        self._modelo, self._vectorizador = self._descomponer(artefacto)

        if not hasattr(self._modelo, "predict"):
            raise TypeError(
                "El artefacto no expone `.predict()`. Revisa como se guardo el modelo."
            )

    # --- Deteccion de la forma del artefacto -------------------------------

    @classmethod
    def _descomponer(cls, artefacto):
        """Devuelve `(modelo, vectorizador_o_None)` segun la forma recibida."""
        if isinstance(artefacto, dict):
            modelo = cls._primero_con(artefacto, cls.CLAVES_MODELO, "predict")
            vectorizador = cls._primero_con(artefacto, cls.CLAVES_VECTORIZADOR, "transform")
            if modelo is None:
                # Ultimo recurso: cualquier valor del dict que sepa predecir.
                modelo = next(
                    (v for v in artefacto.values() if hasattr(v, "predict")), None
                )
            return modelo, vectorizador

        if isinstance(artefacto, (tuple, list)) and len(artefacto) == 2:
            primero, segundo = artefacto
            # El orden no esta garantizado: se identifica por capacidades.
            if hasattr(primero, "predict"):
                return primero, segundo if hasattr(segundo, "transform") else None
            return segundo, primero if hasattr(primero, "transform") else None

        # Caso mas comun y recomendado: un Pipeline que acepta texto crudo.
        return artefacto, None

    @staticmethod
    def _primero_con(diccionario: dict, claves, metodo: str):
        """Primer valor cuya clave este en `claves` y que exponga `metodo`."""
        for clave in claves:
            valor = diccionario.get(clave)
            if valor is not None and hasattr(valor, metodo):
                return valor
        return None

    # --- Interfaz uniforme --------------------------------------------------

    @property
    def requiere_vectorizador(self) -> bool:
        return self._vectorizador is not None

    def _preparar(self, textos: List[str]):
        """Aplica el vectorizador si el modelo no lo trae embebido."""
        if self._vectorizador is None:
            return textos
        return self._vectorizador.transform(textos)

    def predict(self, textos: List[str]):
        return self._modelo.predict(self._preparar(textos))

    def predict_proba(self, textos: List[str]):
        if not hasattr(self._modelo, "predict_proba"):
            return None
        return self._modelo.predict_proba(self._preparar(textos))

    @property
    def clases(self) -> Optional[List[str]]:
        clases = getattr(self._modelo, "classes_", None)
        return None if clases is None else [str(c) for c in clases]

    def describir(self) -> str:
        """Descripcion corta del artefacto, para logs y `GET /salud`."""
        tipo = type(self._modelo).__name__
        return f"{tipo}+vectorizador" if self.requiere_vectorizador else tipo


class ClasificadorML(ClasificadorBase):
    """
    Motor de inferencia real: envuelve el modelo entrenado por Data Science.

    Delega la extraccion de palabras clave en la taxonomia por reglas, porque
    un clasificador de scikit-learn predice la categoria pero no las
    tecnologias presentes en el texto.

    Resiliencia: si `predict` lanza en tiempo de ejecucion (texto inesperado,
    incompatibilidad de versiones de sklearn, vectorizador desalineado), el
    metodo responde con el clasificador por reglas en lugar de propagar el
    error. La API nunca devuelve 500 por culpa del modelo.
    """

    motor = "modelo_ml_real"
    es_mock = False

    def __init__(self, adaptador: AdaptadorModelo, ruta: Path) -> None:
        self._adaptador = adaptador
        self._fallback = ClasificadorReglas()
        self.ruta = ruta
        self.nombre = ruta.name
        self.detalle = adaptador.describir()

    @staticmethod
    def preparar_entrada(titulo: str, texto: str) -> str:
        """
        Construye el texto que recibe el modelo.

        Debe coincidir con la concatenacion usada durante el entrenamiento
        (ver `backend/models/README.md`).
        """
        return f"{titulo}. {texto}".strip()

    def clasificar(self, titulo: str, texto: str) -> dict:
        entrada = self.preparar_entrada(titulo, texto)

        try:
            proba = self._adaptador.predict_proba([entrada])
            clases = self._adaptador.clases

            if proba is not None and clases:
                # Con probabilidades se obtiene todo de una vez: la clase
                # ganadora, su confianza y las alternativas mas probables.
                ranking = sorted(zip(clases, proba[0]), key=lambda par: par[1], reverse=True)
                categoria = str(ranking[0][0])
                probabilidad = round(float(ranking[0][1]), 2)
                relacionadas = [
                    str(clase)
                    for clase, p in ranking[1 : 1 + MAX_CATEGORIAS_RELACIONADAS]
                    if p >= UMBRAL_CATEGORIA_RELACIONADA
                ]
            else:
                categoria = str(self._adaptador.predict([entrada])[0])
                probabilidad = PROBABILIDAD_SIN_PROBA
                relacionadas = []
        except Exception:  # noqa: BLE001 - un fallo de inferencia no tumba la API
            logger.exception(
                "Fallo la inferencia de %s. Se responde con el clasificador por reglas.",
                self.nombre,
            )
            resultado = self._fallback.clasificar(titulo, texto)
            resultado["modelo"] = f"{self._fallback.nombre} (fallback en inferencia)"
            return resultado

        return {
            "categoria": categoria,
            "probabilidad": probabilidad,
            # Las palabras clave siguen saliendo de la taxonomia: el modelo
            # entrega la categoria, no las tecnologias presentes en el texto.
            "informacion_adicional": extraer_palabras_clave(titulo, texto, categoria),
            "resumen": resumir(texto),
            # Salen del propio modelo, no de las reglas: mezclar dos taxonomias
            # distintas en una misma respuesta confunde al usuario.
            "categorias_relacionadas": relacionadas,
            "modelo": self.nombre,
        }

    def categorias(self) -> List[str]:
        """Clases reales del modelo; si no las expone, cae al catalogo local."""
        return self._adaptador.clases or super().categorias()


# ---------------------------------------------------------------------------
# Carga del artefacto
# ---------------------------------------------------------------------------

# Nombres que se buscan en `MODELOS_DIR`, en orden de preferencia. El primero
# es el acordado con Data Science para la Semana 3; los demas se mantienen por
# compatibilidad con entregas anteriores.
NOMBRES_ARTEFACTO = (
    "clasificador_cursos.pkl",
    "clasificador_cursos.joblib",
    "classifier.joblib",
    "classifier.pkl",
    "modelo_athenia.joblib",
)

# Texto usado para verificar el artefacto justo despues de cargarlo.
TEXTO_SONDA = "Curso de introduccion a Python y analisis de datos."


def localizar_modelo() -> Optional[Path]:
    """
    Encuentra el artefacto entrenado.

    Orden de busqueda:
      1. `ATHENIA_MODELO_PATH`, si esta definido y el archivo existe.
      2. Los nombres conocidos dentro de `ATHENIA_MODELOS_DIR`.
      3. Cualquier `.pkl` o `.joblib` de esa carpeta (el mas reciente).

    Devuelve `None` si no hay ningun artefacto disponible.
    """
    if settings.MODELO_PATH:
        if settings.MODELO_PATH.exists():
            return settings.MODELO_PATH
        logger.warning(
            "ATHENIA_MODELO_PATH apunta a %s pero el archivo no existe.",
            settings.MODELO_PATH,
        )
        return None

    directorio = settings.MODELOS_DIR
    if not directorio.is_dir():
        return None

    for nombre in NOMBRES_ARTEFACTO:
        candidato = directorio / nombre
        if candidato.exists():
            return candidato

    # Red de seguridad: si Data Science entrega otro nombre, igual se detecta.
    sueltos = sorted(
        [*directorio.glob("*.pkl"), *directorio.glob("*.joblib")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if sueltos:
        logger.warning(
            "Artefacto con nombre no estandar: %s. Se usara de todos modos.",
            sueltos[0].name,
        )
        return sueltos[0]

    return None


def _deserializar(ruta: Path):
    """
    Carga el artefacto desde disco.

    Se intenta primero con `joblib` (formato habitual de scikit-learn, y el
    unico que maneja bien los arrays de numpy grandes) y, si falla, con
    `pickle` estandar. Asi da igual con cual de los dos lo haya guardado el
    notebook de Data Science.
    """
    try:
        import joblib

        return joblib.load(ruta)
    except ImportError:
        logger.warning("joblib no esta instalado; se intenta con pickle.")
    except Exception as error:  # noqa: BLE001 - se reintenta con pickle
        logger.warning("joblib no pudo leer %s (%s). Se intenta con pickle.", ruta.name, error)

    import pickle

    with open(ruta, "rb") as archivo:
        return pickle.load(archivo)


def obtener_clasificador() -> ClasificadorBase:
    """
    Devuelve el motor de clasificacion activo, con fallback en cada etapa.

    Etapas y comportamiento ante fallo:

      1. **Localizar** el artefacto  -> si no hay, reglas.
      2. **Deserializar**            -> si falla (pickle corrupto, version de
         sklearn incompatible, dependencia ausente), reglas.
      3. **Adaptar**                 -> si la estructura es desconocida o no
         expone `.predict()`, reglas.
      4. **Sonda de inferencia**     -> se ejecuta una prediccion de prueba; si
         lanza, el modelo no sirve en la practica y se usan reglas.

    Solo si las cuatro etapas pasan se activa `ClasificadorML`. Esto evita el
    peor escenario de la demo: un modelo que carga pero revienta en la primera
    peticion real del jurado.
    """
    ruta = localizar_modelo()

    if ruta is None:
        logger.info(
            "No se encontro artefacto en %s. Motor activo: clasificador por reglas.",
            settings.MODELOS_DIR,
        )
        return ClasificadorReglas()

    try:
        artefacto = _deserializar(ruta)
    except Exception:  # noqa: BLE001 - la demo no debe caerse por el modelo
        logger.exception(
            "No se pudo deserializar %s. Motor activo: clasificador por reglas.", ruta
        )
        return ClasificadorReglas()

    try:
        adaptador = AdaptadorModelo(artefacto)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Estructura de %s no reconocida. Motor activo: clasificador por reglas.", ruta
        )
        return ClasificadorReglas()

    # Sonda: confirma que el modelo predice de verdad antes de exponerlo.
    try:
        adaptador.predict([TEXTO_SONDA])
    except Exception:  # noqa: BLE001
        logger.exception(
            "%s cargo pero fallo la prediccion de prueba. "
            "Motor activo: clasificador por reglas.",
            ruta.name,
        )
        return ClasificadorReglas()

    clasificador_ml = ClasificadorML(adaptador, ruta)
    logger.info(
        "Modelo real cargado desde %s (%s). Clases: %s",
        ruta,
        clasificador_ml.detalle,
        adaptador.clases or "no expuestas",
    )
    return clasificador_ml


def recargar_clasificador() -> ClasificadorBase:
    """
    Vuelve a resolver el motor activo y lo publica en el modulo.

    Permite integrar el `.pkl` sin reiniciar el proceso, y es lo que usan las
    pruebas para alternar entre modelo real y fallback.
    """
    global clasificador
    clasificador = obtener_clasificador()
    return clasificador


# ===========================================================================
# 4. Persistencia - historial en memoria
# ===========================================================================


class RepositorioContenidos:
    """
    Historial de analisis en memoria.

    Suficiente para el MVP y para la demo: el jurado ve el historial crecer en
    vivo sin depender de una base de datos. En la Semana 3 esta clase se
    sustituye por un repositorio contra Oracle Autonomous Database
    manteniendo la misma interfaz publica (`agregar`, `listar`, `obtener`).

    Protegido con un lock porque uvicorn puede atender peticiones desde
    distintos hilos del threadpool.

    Nota: al ser en memoria, el historial se pierde al reiniciar el proceso.
    """

    def __init__(self, maximo: Optional[int] = None) -> None:
        self._items: List[dict] = []
        self._secuencia = count(1)
        self._lock = threading.Lock()
        self._maximo = maximo or settings.MAX_HISTORIAL

    # --- Escritura ---------------------------------------------------------

    def agregar(self, contenido: dict) -> dict:
        """Guarda un analisis y devuelve el registro con `id` y `creado_en`."""
        with self._lock:
            registro = {
                **contenido,
                "id": next(self._secuencia),
                "creado_en": datetime.now(timezone.utc),
            }
            self._items.append(registro)

            # Descarta los mas antiguos para acotar el uso de memoria.
            if len(self._items) > self._maximo:
                self._items = self._items[-self._maximo :]

            return registro

    def limpiar(self) -> None:
        """Vacia el historial. La usan las pruebas para aislarse entre casos."""
        with self._lock:
            self._items.clear()
            self._secuencia = count(1)

    # --- Lectura -----------------------------------------------------------

    def listar(
        self,
        categoria: Optional[str] = None,
        buscar: Optional[str] = None,
        limite: Optional[int] = None,
    ) -> List[dict]:
        """
        Devuelve el historial del mas reciente al mas antiguo.

        `buscar` hace coincidencia parcial, sin acentos, sobre titulo, texto,
        categoria y palabras clave — el mismo criterio que usa la vista
        "Buscar Contenidos" del frontend.
        """
        with self._lock:
            items = list(self._items)

        if categoria:
            objetivo = normalizar(categoria)
            items = [i for i in items if normalizar(i["categoria"]) == objetivo]

        if buscar:
            termino = normalizar(buscar)
            items = [i for i in items if termino in self._corpus(i)]

        items.sort(key=lambda i: i["id"], reverse=True)

        return items[:limite] if limite else items

    def obtener(self, contenido_id: int) -> Optional[dict]:
        """Devuelve un analisis por su id, o `None` si no existe."""
        with self._lock:
            return next((i for i in self._items if i["id"] == contenido_id), None)

    def total(self) -> int:
        with self._lock:
            return len(self._items)

    @staticmethod
    def _corpus(item: dict) -> str:
        """Texto normalizado sobre el que se aplica la busqueda libre."""
        partes = [
            item.get("titulo", ""),
            item.get("texto", ""),
            item.get("categoria", ""),
            *item.get("informacion_adicional", []),
        ]
        return normalizar(" ".join(partes))


# ===========================================================================
# 5. Metricas para el Dashboard
# ===========================================================================


def calcular_metricas(items: List[dict]) -> dict:
    """Agrega el historial en los numeros que muestra el Dashboard."""
    if not items:
        return {
            "total_cursos": 0,
            "total_categorias": 0,
            "total_palabras_clave": 0,
            "confianza_promedio": 0.0,
            "distribucion": [],
            "top_palabras_clave": [],
        }

    total = len(items)
    por_categoria = Counter(i["categoria"] for i in items)
    palabras = Counter(p for i in items for p in i.get("informacion_adicional", []))

    distribucion = [
        {
            "categoria": categoria,
            "cantidad": cantidad,
            "porcentaje": round(cantidad / total * 100),
        }
        for categoria, cantidad in por_categoria.most_common()
    ]

    return {
        "total_cursos": total,
        "total_categorias": len(por_categoria),
        "total_palabras_clave": len(palabras),
        "confianza_promedio": round(sum(i["probabilidad"] for i in items) / total, 2),
        "distribucion": distribucion,
        "top_palabras_clave": [
            {"palabra": palabra, "cantidad": cantidad}
            for palabra, cantidad in palabras.most_common(10)
        ],
    }


# ===========================================================================
# 6. Instancias compartidas + datos de demo
# ===========================================================================

clasificador: ClasificadorBase = obtener_clasificador()
repositorio = RepositorioContenidos()


def analizar_y_guardar(entrada: dict) -> dict:
    """
    Caso de uso principal: clasifica el contenido y lo persiste en el historial.

    Es lo que ejecuta `POST /contenido`; mantenerlo aqui deja la ruta HTTP
    reducida a validar y serializar.
    """
    resultado = clasificador.clasificar(entrada["titulo"], entrada["texto"])

    return repositorio.agregar(
        {
            **resultado,
            "titulo": entrada["titulo"],
            "texto": entrada["texto"],
            "origen": entrada.get("origen"),
            "url": entrada.get("url"),
        }
    )


# Contenido de ejemplo: da vida al Dashboard y a la busqueda en la primera
# carga, antes de que el usuario analice nada. Se desactiva con
# ATHENIA_SEED_DEMO=false (las pruebas lo hacen para aislarse).
CONTENIDO_DEMO: List[dict] = [
    {
        "titulo": "Introduccion a Spring Boot",
        "texto": (
            "Curso practico para construir APIs REST seguras con Java y Spring Boot, "
            "aplicando Spring Security, Spring Data JPA y autenticacion con JWT."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "Docker para Principiantes",
        "texto": (
            "Conceptos basicos de contenedores e imagenes, escritura de un Dockerfile "
            "y despliegue de aplicaciones sobre Linux."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "Machine Learning con Python",
        "texto": (
            "Entrenamiento de modelos de clasificacion con Scikit-Learn y Pandas, "
            "aplicando tecnicas de NLP y vectorizacion TF-IDF."
        ),
        "origen": "Oracle Next Education",
    },
    {
        "titulo": "React desde Cero",
        "texto": (
            "Componentes, hooks y manejo de estado en React, con estilos en "
            "Tailwind CSS para lograr una interfaz responsive."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "Despliegue de Apps en Oracle Cloud",
        "texto": (
            "Uso de OCI: Compute, Object Storage y Autonomous Database, con "
            "balanceo de carga y alta disponibilidad."
        ),
        "origen": "Oracle",
    },
    {
        "titulo": "Microservicios con Spring Cloud",
        "texto": (
            "Arquitectura distribuida con microservicios, service discovery, "
            "API Gateway y tolerancia a fallos sobre Spring Boot."
        ),
        "origen": "Alura",
    },
    {
        "titulo": "SQL y Modelado de Datos con Oracle",
        "texto": (
            "Consultas avanzadas con SQL, uso de join, normalizacion y modelado "
            "de datos sobre Oracle Database."
        ),
        "origen": "Oracle",
    },
    {
        "titulo": "Kubernetes en Produccion",
        "texto": (
            "Orquestacion de contenedores con Kubernetes, despliegues, escalado "
            "automatico, monitoreo y observabilidad."
        ),
        "origen": "Comunidad",
    },
]


def sembrar_demo(forzar: bool = False) -> int:
    """
    Precarga el historial con contenido de ejemplo.

    Se llama al arrancar la app. Devuelve cuantos items se insertaron; 0 si la
    semilla esta desactivada o el historial ya tenia datos.
    """
    if not (settings.SEED_DEMO or forzar):
        return 0
    if repositorio.total() > 0:
        return 0

    for demo in CONTENIDO_DEMO:
        analizar_y_guardar(demo)

    logger.info("Historial precargado con %d contenidos de demo.", len(CONTENIDO_DEMO))
    return len(CONTENIDO_DEMO)
