"""
Recomendador por matriz de similitud (Modelo Relacional).
==========================================================

Carga `Data/matriz_similitud_cursos.pkl` (matriz NumPy de similitud coseno
entre cursos) y `Data/mapeo_cursos.json` (indice -> metadatos del curso) una
sola vez por instancia, y expone `recomendar()` para el endpoint
`/cursos/{id}/relacionados-matriz`.

Diagnostico del puntero de Git LFS
-----------------------------------
`Data/matriz_similitud_cursos.pkl` pesa ~190 MB y esta declarado en
`.gitattributes` como `filter=lfs`. Si alguien clona el repo sin `git-lfs`
instalado, o sin correr `git lfs pull` (el caso por defecto en la mayoria de
CI, y en el `Dockerfile` de OCI actual, que no instala git-lfs), el archivo
en disco NO es el pickle real: es el puntero de texto de Git LFS

    version https://git-lfs.github.com/spec/v1
    oid sha256:...
    size 199280889

Antes de este cambio, `joblib.load()` sobre ese puntero lanzaba una excepcion
generica que el `except Exception` de mas abajo se tragaba sin distinguirla
de "el .pkl esta corrupto" o "el .pkl tiene un formato viejo". Con
`_es_puntero_lfs()` el motivo queda claro y accionable (`git lfs pull`) en vez
de un traceback opaco.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

logger = logging.getLogger("athenia.ml.matrix_recommender")

# Calcula la ruta absoluta apuntando a la carpeta 'Data' en la raíz del proyecto.
#
# CURRENT_DIR es .../backend/app/ml. En local (sin Docker, `npm run dev`)
# 'Data/' vive TRES niveles arriba de aqui: ml -> app -> backend -> raiz del
# repo. Este calculo antes subia solo dos niveles y se quedaba en
# .../backend/, asi que el recomendador por matriz nunca encontraba el .pkl
# ni el mapeo y quedaba "no disponible" en silencio (visible recien en
# `GET /cursos/estado`, nunca como error). `ATHENIA_DATA_DIR` permite apuntar
# a otra ruta -por ejemplo si un futuro Dockerfile copia 'Data/' dentro de la
# imagen- sin tocar este calculo.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # .../backend/app/ml
_RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
ROOT_DIR = os.getenv("ATHENIA_DATA_DIR", _RAIZ_PROYECTO)

MODEL_PATH = os.path.join(ROOT_DIR, "Data", "matriz_similitud_cursos.pkl")
MAPEO_PATH = os.path.join(ROOT_DIR, "Data", "mapeo_cursos.json")

#: Firma de un puntero de Git LFS no resuelto. Los archivos reales de joblib
#: nunca empiezan asi, asi que basta leer los primeros bytes.
_FIRMA_LFS = b"version https://git-lfs.github.com/spec/v1"


def _es_puntero_lfs(ruta: str) -> bool:
    try:
        with open(ruta, "rb") as f:
            return f.read(len(_FIRMA_LFS)) == _FIRMA_LFS
    except OSError:
        return False


class MatrixRecommender:
    def __init__(self):
        self.matriz_similitud = None
        self.mapeo_cursos: Dict[str, Any] = {}
        self.ultimo_error: Optional[str] = None
        self._cargar_recursos()

    def _cargar_recursos(self) -> None:
        if not os.path.exists(MODEL_PATH) or not os.path.exists(MAPEO_PATH):
            self.ultimo_error = f"Archivos no encontrados en: {MODEL_PATH} o {MAPEO_PATH}"
            logger.warning(self.ultimo_error)
            return

        if _es_puntero_lfs(MODEL_PATH):
            self.ultimo_error = (
                f"{MODEL_PATH} es un puntero de Git LFS sin resolver, no el "
                "archivo real (~190 MB). Corre 'git lfs install && git lfs pull' "
                "en este clon (y asegurate de que el Dockerfile/CI de OCI haga lo "
                "mismo antes de construir la imagen)."
            )
            logger.error(self.ultimo_error)
            return

        try:
            self.matriz_similitud = joblib.load(MODEL_PATH)
            with open(MAPEO_PATH, "r", encoding="utf-8") as f:
                self.mapeo_cursos = json.load(f)
            self.ultimo_error = None
            logger.info(
                "Modelo relacional .pkl y mapeo cargados: %d cursos.",
                len(self.matriz_similitud),
            )
        except Exception as exc:
            self.ultimo_error = f"Error al cargar el modelo relacional: {type(exc).__name__}: {exc}"
            logger.error(self.ultimo_error)

    def diagnostico(self) -> dict:
        """Snapshot del estado del recomendador para `GET /cursos/estado`."""
        return {
            "disponible": self.matriz_similitud is not None,
            "total_cursos": None if self.matriz_similitud is None else len(self.matriz_similitud),
            "ruta_matriz": MODEL_PATH,
            "ruta_mapeo": MAPEO_PATH,
            "motivo": self.ultimo_error,
        }

    def recomendar(self, curso_idx: int, top_n: int = 4) -> List[Dict[str, Any]]:
        if self.matriz_similitud is None or curso_idx >= len(self.matriz_similitud):
            return []

        # Extraer similitudes de la matriz NumPy
        similitudes = self.matriz_similitud[curso_idx]
        indices_ordenados = np.argsort(similitudes)[::-1]

        # Filtrar para no recomendar el mismo curso
        indices_filtrados = [int(i) for i in indices_ordenados if i != curso_idx][:top_n]

        resultados = []
        for idx in indices_filtrados:
            score = int(round(similitudes[idx] * 100))
            info = self.mapeo_cursos.get(str(idx), self.mapeo_cursos.get(idx, {}))

            if isinstance(info, dict):
                titulo = info.get("titulo", f"Curso {idx}")
                categoria = info.get("categoria", "Desarrollo y Tecnología")
                proveedor = info.get("proveedor", "Plataforma")
                tags = info.get("tags", [])
                # `url` y `descripcion` los agrega
                # `scripts/enriquecer_mapeo_cursos.py`, cruzando por titulo
                # contra `Data/cursos_dataset.json` (el mismo dataset que usa
                # el buscador). Un `mapeo_cursos.json` viejo, generado antes
                # de correr ese script, puede no tenerlos todavia — de ahi el
                # default a "".
                url = info.get("url", "")
                descripcion = info.get("descripcion", "")
            else:
                titulo = str(info)
                categoria = "Desarrollo y Tecnología"
                proveedor = "Plataforma"
                tags = []
                url = ""
                descripcion = ""

            resultados.append(
                {
                    "id": idx,
                    "titulo": titulo,
                    "categoria": categoria,
                    "proveedor": proveedor,
                    "match_score": score,
                    "tags": tags,
                    "url": url,
                    "descripcion": descripcion,
                }
            )

        return resultados


# Instancia global accesible desde los routers.
#
# IMPORTANTE: usar SIEMPRE esta instancia (`recomendador_matriz`), nunca
# `MatrixRecommender()` suelto dentro de una ruta. La version original
# instanciaba la clase de nuevo en CADA peticion a
# `/cursos/{id}/relacionados-matriz` y a `/recomendaciones-matriz/{id}`, es
# decir: deserializaba los ~190 MB de la matriz con `joblib.load()` en cada
# request — cientos de milisegundos extra (o presion de memoria bajo carga)
# por cada click en el detalle de un curso.
recomendador_matriz = MatrixRecommender()
