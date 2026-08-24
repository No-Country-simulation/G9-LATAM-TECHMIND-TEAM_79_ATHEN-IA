"""
Enriquece `Data/mapeo_cursos.json` con `url` y `descripcion` (Modelo Relacional).
=================================================================================

Problema que resuelve
----------------------
El "Contenido relacionado" que arma `MatrixRecommender` (Modelo Relacional,
`Data/matriz_similitud_cursos.pkl`) lee sus metadatos de `Data/mapeo_cursos.json`,
que solo trae `indice`, `titulo` y `categoria`. Por eso esas tarjetas nunca
muestran un enlace a la plataforma ni una descripcion, a diferencia del
buscador semantico — que si tiene ambos campos porque los lee directo de
`Data/cursos_dataset.json` (ver `busqueda/limpieza.py::construir_metadatos`).

Por que un cruce por titulo y no por indice
---------------------------------------------
`mapeo_cursos.json` tiene 4.991 entradas; `cursos_dataset.json` tiene 8.710
(el dataset crudo, sin deduplicar). El `indice` de `mapeo_cursos.json` NO es
la misma posicion que `Unnamed: 0` en el dataset crudo — la matriz de
similitud se entreno sobre un dataset ya deduplicado/reindexado, así que
cruzar por posicion da coincidencias falsas mas alla de las primeras filas.
Cruzando por titulo normalizado (minusculas, espacios colapsados) el match
es del 99.3% (4.957 de 4.991) — mas que suficiente para una solucion rapida
sin tocar la matriz de similitud ni pedirle nada nuevo a Data Science.

Que hace este script
----------------------
1. Lee `Data/cursos_dataset.json` y arma un indice titulo-normalizado -> registro.
2. Lee `Data/mapeo_cursos.json`.
3. Para cada entrada, busca su titulo en el indice y copia `url` y
   `descripcion` (misma logica de extraccion de columnas que usa el
   buscador: `URL`/`Course URL` y `Short Intro`/`Course Short Intro`).
4. Escribe un respaldo (`mapeo_cursos.json.bak`) y sobreescribe
   `mapeo_cursos.json` con los campos nuevos agregados.

Es un script de una sola corrida — no hace falta re-ejecutarlo salvo que
`cursos_dataset.json` o `mapeo_cursos.json` cambien.

Uso (desde la raiz del repo):

    python backend/scripts/enriquecer_mapeo_cursos.py
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = ROOT_DIR / "Data" / "cursos_dataset.json"
MAPEO_PATH = ROOT_DIR / "Data" / "mapeo_cursos.json"

#: Igual que `busqueda/limpieza.py::primer_valor` pero acotado a lo que este
#: script necesita, para no importar el modulo del backend (evita arrastrar
#: la carga de FastAPI/config solo para correr un script de datos).
_MARCADORES_NULOS = frozenset({"", "nan", "none", "null", "n/a", "na", "-", "--"})


def _normalizar_texto(valor) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() in _MARCADORES_NULOS else texto


def _primer_valor(item: dict, *columnas: str) -> str:
    for columna in columnas:
        valor = _normalizar_texto(item.get(columna))
        if valor:
            return valor
    return ""


def _normalizar_titulo(titulo: str) -> str:
    return re.sub(r"\s+", " ", str(titulo).strip().lower())


def construir_indice_por_titulo(dataset: list[dict]) -> dict[str, dict]:
    """Primer registro visto por titulo normalizado (hay ~3.700 duplicados)."""
    indice: dict[str, dict] = {}
    for registro in dataset:
        titulo = _primer_valor(registro, "Title", "clean_title", "Course Title")
        if not titulo:
            continue
        clave = _normalizar_titulo(titulo)
        indice.setdefault(clave, registro)
    return indice


def enriquecer(mapeo: dict, indice_por_titulo: dict[str, dict]) -> tuple[dict, int, int]:
    coincidencias = 0
    sin_coincidencia = 0
    enriquecido = {}

    for clave, entrada in mapeo.items():
        registro = indice_por_titulo.get(_normalizar_titulo(entrada.get("titulo", "")))
        nueva_entrada = dict(entrada)

        if registro:
            coincidencias += 1
            nueva_entrada["url"] = _primer_valor(registro, "URL", "Course URL", "url")
            nueva_entrada["descripcion"] = _primer_valor(
                registro, "Short Intro", "Course Short Intro", "clean_intro"
            )[:500]
        else:
            sin_coincidencia += 1
            nueva_entrada.setdefault("url", "")
            nueva_entrada.setdefault("descripcion", "")

        enriquecido[clave] = nueva_entrada

    return enriquecido, coincidencias, sin_coincidencia


def main() -> None:
    if not DATASET_PATH.exists():
        raise SystemExit(f"No se encontro {DATASET_PATH}")
    if not MAPEO_PATH.exists():
        raise SystemExit(f"No se encontro {MAPEO_PATH}")

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    with open(MAPEO_PATH, "r", encoding="utf-8") as f:
        mapeo = json.load(f)

    indice_por_titulo = construir_indice_por_titulo(dataset)
    enriquecido, coincidencias, sin_coincidencia = enriquecer(mapeo, indice_por_titulo)

    respaldo = MAPEO_PATH.with_suffix(".json.bak")
    shutil.copyfile(MAPEO_PATH, respaldo)

    with open(MAPEO_PATH, "w", encoding="utf-8") as f:
        json.dump(enriquecido, f, ensure_ascii=False, indent=2)

    total = len(mapeo)
    print(f"Total de cursos en mapeo_cursos.json: {total}")
    print(f"Con url/descripcion agregadas:        {coincidencias} ({coincidencias / total * 100:.1f}%)")
    print(f"Sin coincidencia (quedan en \"\"):      {sin_coincidencia} ({sin_coincidencia / total * 100:.1f}%)")
    print(f"Respaldo del archivo original:         {respaldo}")
    print(f"Archivo actualizado:                   {MAPEO_PATH}")


if __name__ == "__main__":
    main()
