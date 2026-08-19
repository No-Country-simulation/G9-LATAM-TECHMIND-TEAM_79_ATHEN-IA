"""
Saneado del texto antes de vectorizar (dominio puro, sin I/O).
================================================================

Aqui esta la causa raiz de los resultados incoherentes que reportaba el
equipo. Auditando `Data/cursos_dataset.json` (8.710 registros) aparecio esto:

    full_text solo con espacios ........  378 registros (4.3%)
    full_text que es una duracion ......  ~200 registros ('4 hours', '5 hours')
    clean_title solo con espacios ......  381 registros
    clean_skills vacio ................. 6.657 registros (76.4%)
    Title con el string 'None' .........  cientos

Un texto vacio o de dos palabras sin contenido tematico produce un vector
practicamente aleatorio dentro del espacio de embeddings. Al consultar
cualquier cosa, esos vectores caen a distancias intermedias y **se cuelan
entre los resultados**: son los "cursos extranos" que aparecian.

El `build_embeddings.py` original intentaba protegerse asi:

    text_to_embed = item.get("full_text") or f"{titulo} {skills} {intro}"

pero `" "` y `"nan"` son **truthy** en Python, de modo que el `or` nunca
saltaba al respaldo. Este modulo corrige justamente eso.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

# Valores que las exportaciones de pandas dejan como texto y que NO son
# contenido: hay que tratarlos como ausentes.
MARCADORES_NULOS = frozenset(
    {"", "nan", "none", "null", "n/a", "na", "-", "--", "sin titulo", "sin título"}
)

# Un texto util para vectorizar necesita un minimo de senal semantica.
# Por debajo de este umbral el embedding es ruido.
MINIMO_CARACTERES_UTILES = 15

# Campos que son solo una duracion, no contenido ("4 hours", "3 semanas").
_SOLO_DURACION = re.compile(
    r"^\s*\d+([.,]\d+)?\s*(h|hr|hrs|hour|hours|min|mins|minute|minutes|"
    r"d|day|days|dia|dias|w|week|weeks|semana|semanas|month|months|mes|meses|"
    r"year|years|ano|anos)\b\.?\s*$",
    re.IGNORECASE,
)


def es_valor_nulo(valor: Any) -> bool:
    """
    True si el valor debe tratarse como ausente.

    Cubre `None`, los `float('nan')` de pandas, cadenas vacias o de solo
    espacios, y los marcadores textuales que deja una exportacion a JSON
    (`"nan"`, `"None"`, `"N/A"`...).
    """
    if valor is None:
        return True

    # NaN es el unico float que no es igual a si mismo.
    if isinstance(valor, float) and valor != valor:
        return True

    if not isinstance(valor, str):
        return False

    return valor.strip().lower() in MARCADORES_NULOS


def texto_limpio(valor: Any, defecto: str = "") -> str:
    """Devuelve el texto sin espacios sobrantes, o `defecto` si es nulo."""
    if es_valor_nulo(valor):
        return defecto
    return re.sub(r"\s+", " ", str(valor)).strip()


def es_solo_duracion(texto: str) -> bool:
    """
    True si el texto es unicamente una duracion.

    En el dataset hay ~200 registros cuyo `full_text` es literalmente
    "4 hours": un campo de duracion que se colo en la columna de texto durante
    el ETL. Vectorizarlo genera un embedding sin relacion con ningun tema.
    """
    return bool(_SOLO_DURACION.match(texto))


def es_texto_indexable(texto: str) -> bool:
    """
    True si el texto tiene senal suficiente para producir un embedding util.

    Filtra vacios, duraciones sueltas y cadenas demasiado cortas. Un curso
    que no lo supera NO se indexa: es preferible tener 8.100 cursos
    encontrables que 8.710 con 600 comodines que ensucian toda consulta.
    """
    if not texto or len(texto) < MINIMO_CARACTERES_UTILES:
        return False
    if es_solo_duracion(texto):
        return False
    # Al menos dos palabras de tres letras o mas: descarta "MBA", "PMP 2024".
    return len(re.findall(r"[^\W\d_]{3,}", texto, flags=re.UNICODE)) >= 2


def primer_valor(item: dict, *claves: str, defecto: str = "") -> str:
    """
    Primer campo no nulo de `claves`, ya limpio.

    Sustituye al patron `item.get("a") or item.get("b")`, que fallaba porque
    `" "` y `"nan"` son truthy y ganaban al respaldo.
    """
    for clave in claves:
        valor = texto_limpio(item.get(clave))
        if valor:
            return valor
    return defecto


def primer_titulo(item: dict, *claves: str, defecto: str = "Sin titulo") -> str:
    """
    Como `primer_valor`, pero descarta ademas los titulos que son una duracion.

    En el dataset hay ~200 registros cuyo `Title` es literalmente "4 hours" (la
    duracion se corrio de columna en el ETL). Sin este filtro el Dashboard
    muestra tarjetas tituladas "4 hours", que es justo el tipo de resultado
    extrano que se reporto.
    """
    for clave in claves:
        valor = texto_limpio(item.get(clave))
        if valor and not es_solo_duracion(valor):
            return valor
    return defecto


def construir_texto_indexable(item: dict) -> Optional[str]:
    """
    Texto que se vectoriza para un curso, o `None` si no debe indexarse.

    Combina titulo + categoria + habilidades + introduccion. Se descartan las
    partes nulas antes de unir, para que el embedding no reciba "nan" ni
    espacios sueltos.
    """
    titulo = primer_valor(item, "clean_title", "Title", "Course Title")
    categoria = primer_valor(item, "target_category", "clean_category", "Category")
    habilidades = primer_valor(item, "clean_skills", "Skills")
    intro = primer_valor(item, "clean_intro", "Short Intro", "Course Short Intro")

    # `full_text` viene precalculado por Data, pero solo se usa si es valido:
    # en 378 registros es una cadena de espacios.
    precalculado = texto_limpio(item.get("full_text"))
    if es_texto_indexable(precalculado):
        candidato = precalculado
    else:
        candidato = " ".join(p for p in (titulo, categoria, habilidades, intro) if p)

    candidato = re.sub(r"\s+", " ", candidato).strip()
    return candidato if es_texto_indexable(candidato) else None


def construir_metadatos(item: dict) -> dict:
    """
    Metadatos que viajan junto al vector.

    ChromaDB los guarda en la misma fila que el embedding, asi que no existe
    el riesgo de desalineacion indice/metadatos propio de un array paralelo a
    un DataFrame: no hay dos estructuras que puedan descuadrarse.

    Chroma no admite `None` en metadatos, de ahi los valores por defecto.
    """
    return {
        "titulo": primer_titulo(item, "clean_title", "Title", "Course Title"),
        "descripcion": primer_valor(
            item, "clean_intro", "Short Intro", "Course Short Intro", defecto=""
        )[:500],
        "categoria": primer_valor(
            item, "target_category", "clean_category", "Category", defecto="Otras Areas"
        ),
        "url": primer_valor(item, "URL", "Course URL", "url"),
        "sitio": primer_valor(item, "clean_site", "Site", defecto="Desconocido"),
        "habilidades": primer_valor(item, "clean_skills", "Skills")[:300],
        # Se conserva como texto: Chroma tipa los metadatos y un None romperia.
        "valoracion": primer_valor(item, "Rating", defecto=""),
    }


def preparar_lote(cursos: Iterable[dict]) -> tuple[list[str], list[dict], list[str], int]:
    """
    Prepara el catalogo completo para indexar.

    Devuelve `(documentos, metadatos, ids, descartados)`. Los tres primeros
    quedan alineados por construccion: se anaden en el mismo paso del bucle,
    de modo que `documentos[i]`, `metadatos[i]` e `ids[i]` son siempre el
    mismo curso.

    El `id` se deriva de la posicion ORIGINAL en el dataset, no del contador
    de aceptados. Asi un `curso_57` sigue apuntando al registro 57 del JSON
    aunque se hayan descartado registros anteriores — es lo que permite
    rastrear un resultado hasta su fila de origen.
    """
    documentos: list[str] = []
    metadatos: list[dict] = []
    ids: list[str] = []
    descartados = 0
    vistos: set[str] = set()

    for posicion, item in enumerate(cursos):
        texto = construir_texto_indexable(item)
        if texto is None:
            descartados += 1
            continue

        # El dataset trae 3.293 filas con texto identico a otra anterior (el
        # mismo curso repetido). Indexarlas produce vectores identicos, y una
        # busqueda gasta sus 10 huecos mostrando el mismo curso varias veces:
        # con "hacking etico" salian 3 copias de "Ethical Hacking".
        # Se conserva la primera aparicion, que es la de menor posicion.
        huella = texto.lower()
        if huella in vistos:
            descartados += 1
            continue
        vistos.add(huella)

        documentos.append(texto)
        metadatos.append(construir_metadatos(item))
        ids.append(f"curso_{posicion}")

    return documentos, metadatos, ids, descartados
