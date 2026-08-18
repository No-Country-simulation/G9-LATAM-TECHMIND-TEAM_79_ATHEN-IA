"""
Taxonomia y utilidades de texto del dominio AthenIA.
=====================================================

Conocimiento de negocio puro: que categorias existen, que tecnologias las
delatan y como se comparan cadenas de texto. **Cero dependencias de FastAPI,
scikit-learn o I/O** — por eso vive en `domain/` y no en `ml/`.

`ml.reglas.ClasificadorReglas` y `ml.modelo.ClasificadorML` importan de aqui
para puntuar categorias y extraer palabras clave; ninguno de los dos posee su
propia copia de la taxonomia.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

CATEGORIA_POR_DEFECTO = "Otros"

# ---------------------------------------------------------------------------
# Taxonomia del MVP
# ---------------------------------------------------------------------------
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
    # El modelo entrenado tiene una clase "Ciberseguridad y Redes", pero la
    # taxonomia no tenia rama equivalente: un curso de firewalls y pentesting
    # se clasificaba bien pero salia con `informacion_adicional: []`, sin
    # ninguna tecnologia que mostrar en la tarjeta.
    "Ciberseguridad": {
        "Seguridad": ("seguridad", "ciberseguridad", "hardening", "vulnerabilidad"),
        "Firewall": ("firewall", "firewalls", "waf", "iptables"),
        "VPN": ("vpn", "tunel seguro", "ipsec"),
        "Pentesting": ("pentesting", "pentest", "ethical hacking", "owasp"),
        "Criptografia": ("criptografia", "cifrado", "encriptacion", "tls", "ssl"),
        "Redes": ("redes", "tcp/ip", "dns", "subred", "enrutamiento"),
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


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

_ACENTOS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def normalizar(texto: str) -> str:
    """Minusculas, sin acentos y con espacios colapsados."""
    return re.sub(r"\s+", " ", texto.translate(_ACENTOS).lower()).strip()


def contiene(texto_norm: str, patron: str) -> bool:
    """
    Busca `patron` respetando limites de palabra.

    Evita falsos positivos clasicos: que "java" haga match dentro de
    "javascript", o que "ui" aparezca dentro de "construir". Publica (sin
    guion bajo) porque `ml.reglas` la usa fuera de este modulo para su
    puntuacion ponderada por titulo/texto.
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

    La usan tanto `ClasificadorReglas` como `ClasificadorML`: un clasificador
    de scikit-learn devuelve la categoria pero no las tecnologias detectadas.
    """
    titulo_norm, texto_norm = normalizar(titulo), normalizar(texto)
    ramas = {categoria: TAXONOMIA[categoria]} if categoria in TAXONOMIA else TAXONOMIA

    encontradas: List[str] = []
    for keywords in ramas.values():
        for etiqueta, patrones in keywords.items():
            if any(contiene(titulo_norm, p) or contiene(texto_norm, p) for p in patrones):
                encontradas.append(etiqueta)

    return encontradas[:limite]


def resumir(texto: str, limite: int = 180) -> str:
    """Recorte en el limite de palabra. Placeholder del resumen abstractivo."""
    limpio = re.sub(r"\s+", " ", texto).strip()
    if len(limpio) <= limite:
        return limpio
    return limpio[:limite].rsplit(" ", 1)[0] + "..."


def categorias_soportadas() -> List[str]:
    """Catalogo de categorias que el clasificador por reglas puede devolver."""
    return sorted(TAXONOMIA.keys()) + [CATEGORIA_POR_DEFECTO]
