"""
Construye el indice vectorial de cursos.
=========================================

    python backend/scripts/build_embeddings.py [--limite N] [--forzar]

Lee `Data/cursos_dataset.json`, sanea cada registro y lo indexa en ChromaDB
con distancia **coseno**.

Por que hay que reconstruir el indice
--------------------------------------

La metrica de una coleccion de Chroma se fija al crearla y es inmutable. El
indice entregado se creo sin `metadata`, asi que quedo con `hnsw:space="l2"`
(euclidiana al cuadrado). Verificado: su tabla `collection_metadata` esta
vacia. No hay forma de convertirlo a coseno en caliente — hay que volver a
generarlo, y por eso este script existe.

Que cambio respecto a la version original
------------------------------------------

1. `metadata={"hnsw:space": "cosine"}` al crear la coleccion.
2. Se descartan los registros sin texto util. El original hacia:

       text_to_embed = item.get("full_text") or f"{titulo} {skills} {intro}"

   pero `" "` es **truthy** en Python, asi que el respaldo nunca se activaba y
   378 cursos se indexaron con una cadena de espacios. Sus vectores casaban
   con cualquier consulta: son los "cursos extranos" del reporte.
3. Los metadatos incluyen `descripcion`, que el original omitia — el frontend
   la necesita para el cuerpo de la tarjeta.
4. Se indexa por lotes: 8.710 documentos en un solo `add()` agota la memoria
   en la instancia de OCI.
5. Si la coleccion ya existe se elimina antes de reconstruir, en lugar de
   `get_or_create` + `add`, que duplicaba documentos al re-ejecutar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Permite ejecutar el script directamente (`python backend/scripts/...`)
# reutilizando la logica de limpieza de la app en vez de duplicarla.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.busqueda.almacen import (  # noqa: E402
    METADATOS_COLECCION,
    MODELO_EMBEDDINGS,
    NOMBRE_COLECCION,
    RUTA_INDICE,
)
from app.busqueda.limpieza import preparar_lote  # noqa: E402

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
RUTA_DATASET = os.path.join(BASE_DIR, "Data", "cursos_dataset.json")

#: Documentos por lote. Equilibra memoria y velocidad en la instancia de OCI.
TAMANO_LOTE = 500


def cargar_dataset(ruta: str) -> list:
    """Lee el catalogo de cursos. Acepta una lista o un dict con `data`/`cursos`."""
    with open(ruta, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    if isinstance(datos, dict):
        for clave in ("data", "cursos", "courses", "items"):
            if isinstance(datos.get(clave), list):
                return datos[clave]
        raise ValueError(f"No encontre una lista de cursos en {ruta}.")

    if not isinstance(datos, list):
        raise ValueError(f"Formato inesperado en {ruta}: {type(datos).__name__}.")

    return datos


def construir(limite: int | None = None, forzar: bool = False) -> int:
    """Genera el indice y devuelve la cantidad de cursos indexados."""
    import chromadb
    from chromadb.utils import embedding_functions

    print(f"Leyendo {RUTA_DATASET} ...")
    cursos = cargar_dataset(RUTA_DATASET)
    if limite:
        cursos = cursos[:limite]
    print(f"  {len(cursos)} registros en el dataset.")

    documentos, metadatos, ids, descartados = preparar_lote(cursos)
    print(f"  {len(documentos)} indexables, {descartados} descartados por texto insuficiente.")

    if not documentos:
        print("Nada que indexar. Abortando.")
        return 0

    os.makedirs(RUTA_INDICE, exist_ok=True)
    cliente = chromadb.PersistentClient(path=RUTA_INDICE)

    existentes = [c.name for c in cliente.list_collections()]
    if NOMBRE_COLECCION in existentes:
        if not forzar:
            print(
                f"\nLa coleccion '{NOMBRE_COLECCION}' ya existe en {RUTA_INDICE}.\n"
                "Re-ejecuta con --forzar para reconstruirla desde cero."
            )
            return 0
        print(f"  Eliminando la coleccion previa '{NOMBRE_COLECCION}' ...")
        cliente.delete_collection(NOMBRE_COLECCION)

    print(f"  Cargando el modelo '{MODELO_EMBEDDINGS}' (puede tardar la primera vez) ...")
    funcion = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODELO_EMBEDDINGS
    )

    coleccion = cliente.create_collection(
        name=NOMBRE_COLECCION,
        embedding_function=funcion,
        # LA CORRECCION CLAVE: sin esto Chroma usa L2 y los puntajes de
        # similitud dejan de ser interpretables.
        metadata=METADATOS_COLECCION,
    )

    for inicio in range(0, len(documentos), TAMANO_LOTE):
        fin = inicio + TAMANO_LOTE
        coleccion.add(
            documents=documentos[inicio:fin],
            metadatas=metadatos[inicio:fin],
            ids=ids[inicio:fin],
        )
        print(f"  Indexados {min(fin, len(documentos))}/{len(documentos)} ...")

    total = coleccion.count()
    print(f"\nListo: {total} cursos indexados con metrica coseno en {RUTA_INDICE}.")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el indice vectorial de cursos.")
    parser.add_argument("--limite", type=int, default=None, help="Indexa solo los primeros N cursos.")
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Elimina la coleccion existente y la reconstruye.",
    )
    args = parser.parse_args()

    try:
        construir(limite=args.limite, forzar=args.forzar)
    except FileNotFoundError:
        print(f"ERROR: no encontre el dataset en {RUTA_DATASET}.")
        return 1
    except ImportError as exc:
        print(f"ERROR: falta una dependencia ({exc}).")
        print("Instala con: pip install -r backend/requirements.txt")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
