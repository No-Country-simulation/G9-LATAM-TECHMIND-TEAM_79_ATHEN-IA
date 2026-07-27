"""
Capa de servicios de AthenIA.
=============================

Contiene toda la logica de negocio, aislada de HTTP:

  1. **Taxonomia**        - categorias y tecnologias que reconoce el MVP.
  2. **Clasificacion**    - `ClasificadorReglas` (fallback) y `ClasificadorML`.
  3. **Keywords**         - extraccion de tecnologias presentes en el texto.
  4. **Persistencia**     - `RepositorioContenidos`, historial en memoria.
  5. **Metricas**         - agregados que alimentan el Dashboard.

Mecanismo de fallback
---------------------
`obtener_clasificador()` intenta cargar el artefacto entrenado
(`backend/models/classifier.joblib`). Si no existe, no se puede leer, o falla
al predecir, la API **sigue funcionando** con el clasificador por reglas. La
demo nunca se cae por un problema del modelo; `GET /salud` reporta cual esta
activo mediante `es_mock`.

Integracion del modelo real (Semana 3)
--------------------------------------
Basta con dejar el `.joblib` en `backend/models/`. No hay que tocar rutas,
esquemas, frontend ni pruebas. Ver `backend/models/README.md`.
"""

from __future__ import annotations

import logging
import re
import threading
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime, timezone
from itertools import count
from typing import Dict, List, Optional, Tuple

from .config import settings

logger = logging.getLogger("athenia.services")

# Probabilidad reportada cuando el modelo real no expone `predict_proba`.
PROBABILIDAD_SIN_PROBA = 0.75

# Confianza asignada cuando no se detecta ninguna tecnologia conocida.
PROBABILIDAD_SIN_EVIDENCIA = 0.35

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

    nombre: str = "base"
    es_mock: bool = True

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
    tambien si la carga del artefacto falla. Determinista por diseno, para que
    QA pueda escribir aserciones estables.
    """

    nombre = "reglas-keywords-v1"
    es_mock = True

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


class ClasificadorML(ClasificadorBase):
    """
    Envoltorio del modelo entrenado por el equipo de Data Science.

    Delega la extraccion de palabras clave en la taxonomia por reglas, porque
    un `Pipeline` de scikit-learn predice la categoria pero no las tecnologias.
    """

    es_mock = False

    def __init__(self, modelo, ruta) -> None:
        self._modelo = modelo
        self._fallback = ClasificadorReglas()
        self.nombre = f"sklearn:{ruta.name}"

    def clasificar(self, titulo: str, texto: str) -> dict:
        entrada = f"{titulo}. {texto}"

        try:
            categoria = str(self._modelo.predict([entrada])[0])

            probabilidad = PROBABILIDAD_SIN_PROBA
            if hasattr(self._modelo, "predict_proba"):
                probabilidad = round(float(max(self._modelo.predict_proba([entrada])[0])), 2)
        except Exception:  # noqa: BLE001 - un fallo de inferencia no tumba la API
            logger.exception("Fallo la inferencia del modelo. Se responde con reglas.")
            return self._fallback.clasificar(titulo, texto)

        base = self._fallback.clasificar(titulo, texto)

        return {
            "categoria": categoria,
            "probabilidad": probabilidad,
            "informacion_adicional": extraer_palabras_clave(titulo, texto, categoria),
            "resumen": resumir(texto),
            "categorias_relacionadas": base["categorias_relacionadas"],
            "modelo": self.nombre,
        }

    def categorias(self) -> List[str]:
        clases = getattr(self._modelo, "classes_", None)
        if clases is not None:
            return sorted(str(c) for c in clases)
        return super().categorias()


def obtener_clasificador() -> ClasificadorBase:
    """
    Devuelve el clasificador activo aplicando el mecanismo de fallback.

    Orden de preferencia:
      1. Modelo entrenado (`ATHENIA_MODELO_PATH`), si existe y carga bien.
      2. `ClasificadorReglas` en cualquier otro caso.
    """
    ruta = settings.MODELO_PATH

    if not ruta.exists():
        logger.info("Modelo no encontrado en %s. Fallback: clasificador por reglas.", ruta)
        return ClasificadorReglas()

    try:
        import joblib  # import diferido: no es dependencia del MVP por reglas

        modelo = joblib.load(ruta)
        logger.info("Modelo cargado desde %s", ruta)
        return ClasificadorML(modelo, ruta)
    except Exception:  # noqa: BLE001 - la demo no debe caerse por el modelo
        logger.exception("Fallo al cargar %s. Fallback: clasificador por reglas.", ruta)
        return ClasificadorReglas()


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
