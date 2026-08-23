"""
Implementacion del `AlmacenVectorial` sobre ChromaDB.
======================================================

Concentra TODO el acoplamiento a ChromaDB del proyecto. Ningun otro modulo
importa `chromadb`.

Correcciones respecto a la version original
-------------------------------------------

1. **Metrica de distancia.** La coleccion se creaba con
   `get_or_create_collection(name=..., embedding_function=...)` sin
   `metadata`. Chroma entonces usa `hnsw:space="l2"` (euclidiana al
   cuadrado), no coseno. Verificado en la base entregada: la tabla
   `collection_metadata` esta vacia. Con L2 sobre vectores sin normalizar,
   la magnitud del texto (largo de la descripcion) pesa tanto como su
   contenido, y la distancia no tiene cota superior, asi que tampoco se puede
   derivar un `match_score` en [0, 1]. Aqui se fuerza `hnsw:space="cosine"`.

2. **Cliente por peticion.** Se abria un `PersistentClient` y se instanciaba
   el modelo de embeddings en CADA request. Ahora ambos son perezosos y
   unicos por proceso.

3. **Sin distancias.** El `query()` original no pedia `distances`, asi que era
   imposible puntuar o filtrar los resultados. Ahora se piden explicitamente.

4. **Fallo ruidoso.** Un `print()` a stdout y una lista vacia hacian
   indistinguible "no hay resultados" de "la base no existe". Ahora se
   registra en el logger y `esta_disponible()` lo expone a la ruta.

5. **Diagnostico mudo (Semana 5).** Antes de este cambio, si el modelo de
   embeddings no cargaba (paquete ausente, sin red la primera vez que
   `sentence-transformers` intenta bajar el modelo de Hugging Face, o una
   version de `sentence-transformers` incompatible con la que fijo
   `requirements.txt`), el UNICO rastro era una linea de WARNING en el log del
   proceso. `/cursos` y `/cursos/buscar` respondian 200 con 0 resultados sin
   forma de distinguir "no hay coincidencias" de "el indice nunca se abrio".
   Eso fue exactamente lo que paso en un entorno local con la copia de
   `feature/Modelo_Relacional`: el indice de Chroma tenia los 5.066 cursos
   (igual que OCI) y el modelo de embeddings estaba descargado en cache, pero
   la excepcion real quedaba enterrada en la consola. Ahora `_motivo_no_disponible`
   guarda el ultimo error human-readable y `diagnostico()` lo expone por HTTP
   via `GET /cursos/estado`, para no depender de leer logs a mano.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import List, Optional

logger = logging.getLogger("athenia.busqueda.almacen")

#: Debe coincidir con el modelo que genero el indice (384 dimensiones).
#: Cambiarlo obliga a reconstruir la base: los vectores dejan de ser comparables.
MODELO_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"

NOMBRE_COLECCION = "athenex_courses"

#: Metrica de la coleccion. Se fija al CREARLA y es inmutable despues:
#: cambiarla exige reconstruir el indice con `scripts/build_embeddings.py`.
METADATOS_COLECCION = {"hnsw:space": "cosine"}

_BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

#: Ruta canonica del indice dentro del contenedor Docker.
RUTA_INDICE = os.path.join(_BASE_DIR, "data", "vector_db")


def _funcion_embeddings() -> tuple[object | None, str | None]:
    """
    Funcion de embeddings de Chroma, o `(None, motivo)` si no se pudo cargar.

    Se importa aqui dentro y no arriba a proposito: importar
    `sentence-transformers` carga PyTorch (~2 GB) y anade segundos al arranque
    de FastAPI y a CADA ejecucion de la suite de pruebas. Con la importacion
    diferida, el resto de la API arranca igual aunque la dependencia no este.

    Devuelve una tupla `(funcion, motivo)` en vez de solo `funcion` porque
    antes el `None` no distinguia entre "falta el paquete", "no hay red para
    bajar el modelo" y "la version instalada no es compatible con la que
    Chroma espera" — los tres casos quedaban indistinguibles en el log. El
    `motivo` es el mensaje que despues viaja en `GET /cursos/estado`.
    """
    try:
        from chromadb.utils import embedding_functions
    except ImportError as exc:
        motivo = f"chromadb no esta instalado ({exc})."
        logger.warning(motivo)
        return None, motivo

    try:
        return (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=MODELO_EMBEDDINGS
            ),
            None,
        )
    except Exception as exc:  # modelo no descargado, sin red, sin torch, version incompatible...
        motivo = (
            f"No se pudo cargar el modelo de embeddings '{MODELO_EMBEDDINGS}': "
            f"{type(exc).__name__}: {exc}"
        )
        logger.warning(motivo)
        return None, motivo


class AlmacenChroma:
    """
    Indice vectorial persistente de cursos.

    Cumple el `Protocol` `AlmacenVectorial` por forma, sin heredar de el.

    La coleccion se abre una sola vez por proceso, protegida por un lock:
    Uvicorn ejecuta las rutas `def` (sincronas) en un threadpool, asi que dos
    peticiones simultaneas podrian abrir el cliente a la vez.
    """

    nombre = "chromadb"

    def __init__(self, ruta: Optional[str] = None, nombre_coleccion: str = NOMBRE_COLECCION):
        self.ruta = ruta or RUTA_INDICE
        self.nombre_coleccion = nombre_coleccion
        self._coleccion = None
        self._intentado = False
        self._lock = threading.Lock()
        # Conteo por categoria, memorizado en la primera llamada: solo cambia
        # al reconstruir el indice.
        self._categorias: Optional[dict] = None
        # Ultimo motivo por el que la coleccion no se pudo abrir. `None`
        # mientras no se haya intentado abrir, o si se abrio con exito.
        self._motivo_no_disponible: Optional[str] = None

    # -- apertura perezosa ---------------------------------------------------

    def _abrir(self):
        """
        Abre la coleccion una unica vez. Devuelve `None` si no es posible.

        Un fallo no se reintenta en cada peticion: si falta la base, reintentar
        significaria pagar la carga del modelo en cada request.
        """
        if self._intentado:
            return self._coleccion

        with self._lock:
            if self._intentado:  # otra hebra gano la carrera mientras esperabamos
                return self._coleccion
            self._intentado = True
            self._coleccion = self._construir_coleccion()

        return self._coleccion

    def _construir_coleccion(self):
        if not os.path.isdir(self.ruta):
            self._motivo_no_disponible = f"No existe el indice vectorial en {self.ruta}."
            logger.warning(self._motivo_no_disponible)
            return None

        try:
            import chromadb
        except ImportError as exc:
            self._motivo_no_disponible = f"chromadb no esta instalado ({exc})."
            logger.warning(self._motivo_no_disponible)
            return None

        funcion, motivo = _funcion_embeddings()
        if funcion is None:
            self._motivo_no_disponible = motivo
            return None

        try:
            cliente = chromadb.PersistentClient(path=self.ruta)
            coleccion = cliente.get_collection(
                name=self.nombre_coleccion,
                embedding_function=funcion,
            )
        except Exception as exc:
            self._motivo_no_disponible = (
                f"No se pudo abrir la coleccion '{self.nombre_coleccion}': "
                f"{type(exc).__name__}: {exc}"
            )
            logger.warning(self._motivo_no_disponible)
            return None

        self._verificar_metrica(coleccion)
        self._motivo_no_disponible = None
        logger.info("Indice vectorial abierto: %d cursos en %s.", coleccion.count(), self.ruta)
        return coleccion

    @staticmethod
    def _verificar_metrica(coleccion) -> None:
        """
        Avisa si el indice no usa distancia coseno.

        Es exactamente el fallo de la base entregada. Como la metrica se fija
        al crear la coleccion, no se puede corregir en caliente: hay que
        reconstruir. Se registra como ERROR para que salte en los logs de OCI
        en lugar de degradar en silencio la calidad de los resultados.
        """
        metricas = getattr(coleccion, "metadata", None) or {}
        espacio = metricas.get("hnsw:space", "l2")
        if espacio != "cosine":
            logger.error(
                "El indice '%s' usa la metrica '%s' en lugar de 'cosine'. Los puntajes "
                "no seran fiables. Reconstruye con: python backend/scripts/build_embeddings.py",
                coleccion.name,
                espacio,
            )

    # -- contrato AlmacenVectorial ------------------------------------------

    def esta_disponible(self) -> bool:
        """True si hay una coleccion abierta y con al menos un curso."""
        return self.total() > 0

    def total(self) -> int:
        coleccion = self._abrir()
        if coleccion is None:
            return 0
        try:
            return coleccion.count()
        except Exception as exc:
            self._motivo_no_disponible = f"No se pudo contar el indice: {exc}"
            logger.warning(self._motivo_no_disponible)
            return 0

    def diagnostico(self) -> dict:
        """
        Snapshot del estado del indice para `GET /cursos/estado`.

        Fuerza la apertura perezosa (si no se intento aun) para que el primer
        diagnostico despues de arrancar ya sea informativo, en vez de
        devolver "no se intento todavia".
        """
        total = self.total()
        return {
            "disponible": total > 0,
            "total_indexado": total,
            "ruta_indice": self.ruta,
            "coleccion": self.nombre_coleccion,
            "modelo_embeddings": MODELO_EMBEDDINGS,
            "motivo": self._motivo_no_disponible,
        }

    def consultar(self, texto: str, limite: int) -> List[dict]:
        """
        Vecinos mas cercanos a `texto`. Ver `AlmacenVectorial.consultar`.

        Nunca lanza: ante cualquier fallo devuelve lista vacia y lo registra.
        Un buscador caido no debe tumbar el Dashboard.
        """
        coleccion = self._abrir()
        if coleccion is None or limite <= 0:
            return []

        try:
            crudo = coleccion.query(
                query_texts=[texto],
                n_results=limite,
                # `distances` faltaba en la version original: sin el no hay
                # forma de calcular `match_score` ni de aplicar un umbral.
                include=["metadatas", "distances", "documents"],
            )
        except Exception as exc:
            logger.warning("Fallo la consulta vectorial: %s", exc)
            return []

        return self._normalizar(crudo)

    def listar(
        self,
        categoria: Optional[str] = None,
        limite: int = 24,
        desplazamiento: int = 0,
    ) -> List[dict]:
        """
        Navega el catalogo sin consulta. Ver `AlmacenVectorial.listar`.

        Usa `collection.get()`, que filtra por metadatos sin calcular ninguna
        distancia: no carga el modelo de embeddings ni recorre el grafo HNSW.
        """
        coleccion = self._abrir()
        if coleccion is None or limite <= 0:
            return []

        try:
            crudo = coleccion.get(
                where={"categoria": categoria} if categoria else None,
                limit=limite,
                offset=max(0, desplazamiento),
                include=["metadatas"],
            )
        except Exception as exc:
            logger.warning("Fallo al listar el catalogo: %s", exc)
            return []

        # `get()` devuelve listas planas, no anidadas por consulta como `query()`.
        ids = crudo.get("ids") or []
        metadatos = crudo.get("metadatas") or []
        return [
            {"id": str(id_), "distancia": None, "metadatos": dict(meta or {}), "documento": ""}
            for id_, meta in zip(ids, metadatos)
        ]

    def categorias(self) -> dict:
        """
        Conteo de cursos por categoria. Ver `AlmacenVectorial.categorias`.

        El resultado se memoriza: recorrer los metadatos de +5.000 cursos en
        cada peticion seria absurdo para un dato que solo cambia al reconstruir
        el indice.
        """
        if self._categorias is not None:
            return self._categorias

        coleccion = self._abrir()
        if coleccion is None:
            return {}

        try:
            crudo = coleccion.get(include=["metadatas"])
        except Exception as exc:
            logger.warning("Fallo al agregar categorias: %s", exc)
            return {}

        conteo: dict = {}
        for meta in crudo.get("metadatas") or []:
            nombre = (meta or {}).get("categoria") or "Otras Areas"
            conteo[nombre] = conteo.get(nombre, 0) + 1

        self._categorias = dict(sorted(conteo.items(), key=lambda kv: -kv[1]))
        return self._categorias

    @staticmethod
    def _normalizar(crudo: dict) -> List[dict]:
        """
        Aplana la respuesta de Chroma a la forma del `Protocol`.

        Chroma devuelve una lista por cada `query_text`; aqui solo se envia
        uno, de ahi el `[0]`. Se recorren los ids con `zip` sobre las tres
        listas para que un desajuste de longitudes trunque en lugar de
        emparejar mal un id con los metadatos de otro curso.
        """
        if not crudo:
            return []

        def primera(clave: str) -> list:
            valor = crudo.get(clave) or []
            return valor[0] if valor and valor[0] is not None else []

        ids = primera("ids")
        distancias = primera("distances")
        metadatos = primera("metadatas")
        documentos = primera("documents")

        # `documents` puede venir vacio; se rellena para que el zip no trunque.
        if len(documentos) < len(ids):
            documentos = list(documentos) + [""] * (len(ids) - len(documentos))

        return [
            {
                "id": str(id_),
                "distancia": float(distancia),
                "metadatos": dict(meta or {}),
                "documento": documento or "",
            }
            for id_, distancia, meta, documento in zip(ids, distancias, metadatos, documentos)
        ]
