"""
Precarga el modelo de embeddings para desarrollo local.
=========================================================

    .venv/bin/python backend/scripts/precargar_modelo.py     # macOS/Linux
    .venv\\Scripts\\python backend\\scripts\\precargar_modelo.py  # Windows

Por que existe este script
---------------------------

`GET /cursos` y `GET /cursos/buscar` necesitan instanciar
`SentenceTransformerEmbeddingFunction('paraphrase-multilingual-MiniLM-L12-v2')`
para poder abrir la coleccion de Chroma — incluso solo para LISTAR el
catalogo, sin vectorizar ninguna consulta (ver `busqueda/almacen.py`). La
primera vez que eso pasa, `sentence-transformers` intenta bajar el modelo
(~470 MB) desde Hugging Face.

En el `Dockerfile` de OCI ese paso corre en tiempo de BUILD
(`SENTENCE_TRANSFORMERS_HOME=/opt/modelos`), asi que en produccion nunca
depende de la red. En desarrollo local (`npm run dev` -> `uvicorn` directo,
sin Docker) nadie hace ese paso por vos: si la descarga falla o nunca corre,
`/cursos` y `/cursos/buscar` responden 200 con 0 resultados, en silencio,
aunque el indice de Chroma tenga los cursos completos.

Corre este script UNA VEZ despues de instalar `backend/requirements.txt`, y
de nuevo cada vez que reconstruyas el `.venv` desde cero. Deja el modelo en
el cache por defecto de Hugging Face (`~/.cache/huggingface`, o
`%USERPROFILE%\\.cache\\huggingface` en Windows), asi que las siguientes
ejecuciones de `npm run dev` no vuelven a tocar la red.

Si esto falla por falta de red, es la misma situacion que describe el
Dockerfile para una VM de OCI sin salida a internet: copia la carpeta que el
build de Docker deja en `/opt/modelos` a tu cache local y fijá
`SENTENCE_TRANSFORMERS_HOME` a esa ruta en tu `.env`, para no depender de la
descarga en absoluto.
"""

from __future__ import annotations

import os
import sys

MODELO = "paraphrase-multilingual-MiniLM-L12-v2"


def main() -> int:
    # `scripts/dev-backend.mjs` fija HF_HUB_OFFLINE=1 / TRANSFORMERS_OFFLINE=1
    # para los arranques normales del backend (ver ese archivo). Si alguien
    # exporto esas variables en su shell antes de correr ESTE script, hay que
    # anularlas aca: precargar en modo offline no descarga nada, solo falla
    # con un error confuso.
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)

    print(f"Descargando/verificando el modelo de embeddings '{MODELO}'...")
    print("(~470 MB la primera vez; las siguientes corridas usan el cache local)")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        print(
            f"ERROR: no se pudo importar sentence-transformers ({exc}).\n"
            "Corre primero: pip install -r backend/requirements.txt",
            file=sys.stderr,
        )
        return 1

    try:
        modelo = SentenceTransformer(MODELO)
        vector = modelo.encode("prueba de precarga del modelo de embeddings")
    except Exception as exc:  # sin red, proxy corporativo, version incompatible...
        print(
            f"ERROR: no se pudo descargar/cargar el modelo: {type(exc).__name__}: {exc}\n\n"
            "Si tu red no tiene salida a Hugging Face, copia la carpeta que el build de\n"
            "Docker deja en /opt/modelos (ver backend/Dockerfile) a tu cache local y\n"
            "fija SENTENCE_TRANSFORMERS_HOME a esa ruta antes de arrancar el backend.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: modelo cargado, vector de {len(vector)} dimensiones. Listo para 'npm run dev'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
