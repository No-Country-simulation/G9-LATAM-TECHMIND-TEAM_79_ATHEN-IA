"""
Carga del artefacto entrenado (proveedor "modelo-ml").
=========================================================

Unico punto del backend que toca el sistema de archivos para el modelo de
IA. Expone `cargar_modelo_entrenado()`, la funcion que `ml/__init__.py`
registra en `ml.registro` con prioridad alta.

Mecanismo de fallback (4 etapas)
---------------------------------
`cargar_modelo_entrenado()` devuelve `None` (en vez de lanzar) si falla
cualquiera de estas etapas — asi el registro sigue con el siguiente
proveedor, o cae al clasificador por reglas si este era el unico:

  1. **Localizar**    el artefacto en `ATHENIA_MODELOS_DIR`.
  2. **Deserializar**  con joblib y, si falla, con pickle.
  3. **Adaptar**      la estructura entregada (Pipeline, dict o tupla).
  4. **Sondear**      con una prediccion de prueba antes de exponerlo.

Solo si las cuatro etapas pasan se construye `ClasificadorML`. Esto evita el
peor escenario de la demo: un modelo que carga pero revienta en la primera
peticion real del jurado.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..config import settings
from ..domain.protocols import Clasificador
from .adaptador import AdaptadorModelo
from .modelo import ClasificadorML

logger = logging.getLogger("athenia.ml.carga")

# Extensiones que se consideran un artefacto de modelo.
EXTENSIONES_ARTEFACTO = ("*.pkl", "*.joblib")

# Nombres conocidos, en orden de preferencia. Ya NO deciden por si solos cual
# se carga (eso lo hace la fecha de modificacion): sirven como desempate
# determinista cuando dos artefactos tienen la misma marca temporal, algo
# habitual tras un `git clone` o un `docker build`, donde todos los archivos
# quedan con un mtime casi identico.
NOMBRES_ARTEFACTO = (
    "clasificador_cursos.pkl",
    "clasificador_cursos.joblib",
    "classifier.joblib",
    "classifier.pkl",
    "modelo_athenia.joblib",
)

# Texto usado para verificar el artefacto justo despues de cargarlo.
TEXTO_SONDA = "Curso de introduccion a Python y analisis de datos."


def _prioridad_por_nombre(ruta: Path) -> int:
    """
    Posicion del archivo en `NOMBRES_ARTEFACTO` (menor = mas preferido).

    Los nombres desconocidos van al final. Solo se usa como desempate cuando
    dos artefactos comparten marca temporal.
    """
    try:
        return NOMBRES_ARTEFACTO.index(ruta.name)
    except ValueError:
        return len(NOMBRES_ARTEFACTO)


def artefactos_disponibles() -> list[Path]:
    """
    Todos los artefactos de la carpeta de modelos, del mas nuevo al mas viejo.

    Empata por el orden de `NOMBRES_ARTEFACTO` y, en ultima instancia, por
    nombre alfabetico: la seleccion nunca depende del orden en que el sistema
    de archivos devuelva las entradas.
    """
    directorio = settings.MODELOS_DIR
    if not directorio.is_dir():
        return []

    encontrados: list[Path] = []
    for patron in EXTENSIONES_ARTEFACTO:
        encontrados.extend(directorio.glob(patron))

    return sorted(
        encontrados,
        key=lambda p: (-p.stat().st_mtime, _prioridad_por_nombre(p), p.name),
    )


def localizar_modelo() -> Optional[Path]:
    """
    Encuentra el artefacto entrenado que debe cargarse.

    Orden de busqueda:
      1. `ATHENIA_MODELO_PATH`, si esta definido y el archivo existe.
      2. El artefacto **mas reciente** de `ATHENIA_MODELOS_DIR`.

    Por que gana la fecha y no el nombre
    -------------------------------------
    Antes se recorria `NOMBRES_ARTEFACTO` y se tomaba el primero que existiera.
    Eso hacia que un modelo nuevo entregado con otro nombre —el caso tipico,
    `clasificador_v2.pkl` junto al anterior— **quedara ignorado en silencio**:
    la API seguia sirviendo el viejo sin ningun aviso. Al ordenar por fecha de
    modificacion, dejar el artefacto nuevo en la carpeta basta para activarlo.

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

    disponibles = artefactos_disponibles()
    if not disponibles:
        return None

    elegido = disponibles[0]

    if len(disponibles) > 1:
        # Con varios artefactos conviene dejar constancia de cual gano: si la
        # demo responde con un modelo inesperado, el log lo explica.
        logger.info(
            "%d artefactos en %s. Se carga el mas reciente: %s (descartados: %s)",
            len(disponibles),
            settings.MODELOS_DIR,
            elegido.name,
            ", ".join(p.name for p in disponibles[1:]),
        )
    elif elegido.name not in NOMBRES_ARTEFACTO:
        logger.warning(
            "Artefacto con nombre no estandar: %s. Se usara de todos modos.",
            elegido.name,
        )

    return elegido


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


def cargar_modelo_entrenado() -> Optional[Clasificador]:
    """
    Proveedor registrado en `ml.registro` para el motor "modelo-ml".

    Devuelve `None` en cualquier etapa que falle (nunca lanza), para que
    `RegistroProveedores.resolver()` pueda seguir con el siguiente proveedor
    o caer al clasificador por reglas sin logica especial de por medio.
    """
    ruta = localizar_modelo()
    if ruta is None:
        logger.info(
            "No se encontro artefacto en %s. Proveedor 'modelo-ml' no disponible.",
            settings.MODELOS_DIR,
        )
        return None

    try:
        artefacto = _deserializar(ruta)
    except Exception:  # noqa: BLE001 - la demo no debe caerse por el modelo
        logger.exception("No se pudo deserializar %s.", ruta)
        return None

    try:
        adaptador = AdaptadorModelo(artefacto)
    except Exception:  # noqa: BLE001
        logger.exception("Estructura de %s no reconocida.", ruta)
        return None

    # Sonda: confirma que el modelo predice de verdad antes de exponerlo.
    try:
        adaptador.predict([TEXTO_SONDA])
    except Exception:  # noqa: BLE001
        logger.exception("%s cargo pero fallo la prediccion de prueba.", ruta.name)
        return None

    clasificador_ml = ClasificadorML(adaptador, ruta)
    logger.info(
        "Modelo real cargado desde %s (%s). Clases: %s",
        ruta,
        clasificador_ml.detalle,
        adaptador.clases or "no expuestas",
    )
    return clasificador_ml
