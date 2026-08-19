# Arquitectura de la Búsqueda Vectorial de AthenIA

> Guía técnica y material de estudio del equipo.
> Escrita a partir de la auditoría del buscador semántico sobre el catálogo de
> 8.710 cursos entregado por el equipo de Data.

---

## Índice

1. [Por qué existe este documento](#1-por-qué-existe-este-documento)
2. [Conceptos clave](#2-conceptos-clave)
   - 2.1 [Distancia L2 vs. Similitud Coseno](#21-distancia-l2-vs-similitud-coseno)
   - 2.2 [Index Drift vs. Metadata Drift](#22-index-drift-vs-metadata-drift)
   - 2.3 [El problema de los valores *truthy* en Python](#23-el-problema-de-los-valores-truthy-en-python)
3. [El pipeline vectorial de AthenIA](#3-el-pipeline-vectorial-de-athenia)
4. [Buenas prácticas aplicadas](#4-buenas-prácticas-aplicadas)
5. [Operación: reconstruir, verificar, diagnosticar](#5-operación-reconstruir-verificar-diagnosticar)
6. [Deuda técnica conocida](#6-deuda-técnica-conocida)

---

## 1. Por qué existe este documento

La primera integración del buscador devolvía resultados incoherentes: cursos sin
relación con la consulta, tarjetas tituladas `4 hours` y el mismo curso repetido
tres veces. El diagnóstico encontró **trece defectos** en cuatro capas distintas
(datos, indexado, servicio, frontend).

Ninguno era un error "de IA". Todos eran errores de ingeniería clásicos:
una métrica mal configurada, un operador `or` que no hacía lo que parecía, y
código duplicado. Este documento explica el porqué de cada uno para que el
equipo pueda razonarlos, no solo copiarlos.

---

## 2. Conceptos clave

### 2.1 Distancia L2 vs. Similitud Coseno

Un *embedding* es un vector de 384 números que representa el significado de un
texto. Para decidir qué curso se parece más a una consulta hay que medir la
distancia entre vectores — y **la métrica que elijas cambia el resultado**.

#### Distancia Euclidiana (L2)

Es la distancia "en línea recta" de toda la vida, extendida a 384 dimensiones:

```
d(A, B) = √( Σᵢ (Aᵢ − Bᵢ)² )
```

ChromaDB usa por defecto su versión **al cuadrado** (se ahorra la raíz, que no
cambia el orden). Mide **cuán lejos** está la punta de un vector de la otra.

#### Similitud Coseno

Mide el **ángulo** entre los dos vectores, ignorando su longitud:

```
              A · B              Σᵢ Aᵢ·Bᵢ
cos(θ) = ───────────────  =  ────────────────────
           ‖A‖ · ‖B‖          √(ΣAᵢ²) · √(ΣBᵢ²)
```

El resultado va de −1 a 1. Chroma lo expone como **distancia coseno**:

```
distancia = 1 − cos(θ)
```

| `cos(θ)` | ángulo | distancia | lectura |
|---|---|---|---|
| 1.0 | 0° | 0.0 | mismo significado |
| 0.7 | 45° | 0.3 | relacionados |
| 0.0 | 90° | 1.0 | sin relación |
| −1.0 | 180° | 2.0 | opuestos |

#### Por qué L2 fallaba con textos de distinta longitud

Ésta es la parte importante. Los modelos de embeddings producen vectores cuya
**magnitud (‖A‖) crece con la cantidad de texto**. Un curso con una descripción
de 400 palabras genera un vector "largo"; uno de 20 palabras, un vector "corto",
aunque hablen exactamente del mismo tema.

Con **L2**, la distancia mezcla dos cosas que no deberían mezclarse:

- la **dirección** del vector → el tema del que trata (lo que nos importa)
- la **magnitud** → cuánto texto tenía (irrelevante)

Visualízalo en 2D. Dos cursos sobre Python, uno con descripción corta (A) y otro
larga (B), apuntan en la misma dirección pero con distinta longitud:

```
        ▲
        │              B  (mismo tema, texto largo)
        │            ╱
        │          ╱
        │        ╱  ← A y B: ángulo 0°, coseno los ve IDÉNTICOS
        │      A       pero L2 los ve LEJOS (por la magnitud)
        │    ╱
        │  ╱                    C  (otro tema, texto corto)
        │╱____________________________▶
```

Resultado práctico en nuestro catálogo: con L2, un curso irrelevante con
descripción **corta** podía quedar más cerca de la consulta que el curso
correcto con descripción **larga**. Eso es exactamente la "inconsistencia
semántica" que reportó el equipo.

Con **coseno** el vector se normaliza a longitud 1 antes de comparar, la
magnitud desaparece de la ecuación y solo queda el tema.

> **Nota sobre normalización L2 manual.** En una implementación con NumPy o
> FAISS harías `v / np.linalg.norm(v)` a mano y luego producto punto. Con
> ChromaDB **no se normaliza a mano**: se declara la métrica al crear la
> colección y el motor se encarga. El error no fue "olvidar normalizar", fue
> "no declarar la métrica".

#### El bug, en una línea

```python
# ANTES — sin `metadata`, Chroma cae a hnsw:space="l2"
collection = client.get_or_create_collection(
    name="athenex_courses",
    embedding_function=embedding_fn,
)

# DESPUÉS
collection = client.create_collection(
    name="athenex_courses",
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"},   # <-- la corrección
)
```

Verificado en la base entregada: la tabla `collection_metadata` estaba **vacía**.

**La métrica es inmutable.** Se fija al crear la colección y no se puede cambiar
en caliente: corregirla obliga a reconstruir el índice completo.

#### Consecuencia colateral: sin coseno no hay `match_score`

La distancia L2 **no tiene cota superior** — puede ser 0.4 o 40. No se puede
convertir a un porcentaje de afinidad. La distancia coseno sí está acotada, y de
ahí sale el puntaje:

```python
def distancia_a_puntaje(distancia: float) -> float:
    return max(0.0, min(1.0, 1.0 - float(distancia)))
```

Eso es lo que permite el umbral `min_score`: sin métrica acotada, no hay umbral
posible, y sin umbral **todos** los cursos entran en la respuesta.

Lo demostramos con una prueba real contra Chroma
(`TestIntegracionChromaReal::test_el_indice_l2_original_arruina_los_puntajes`):
con dos textos ortogonales, coseno da distancia **1.0** y L2 da **2.0**.

---

### 2.2 Index Drift vs. Metadata Drift

Dos fallos que suenan parecidos y se confunden a menudo.

#### Index Drift — el problema clásico de FAISS/NumPy

Ocurre cuando mantienes **dos estructuras paralelas**: una matriz de vectores y
un DataFrame con los datos, unidos solo por la posición.

```python
df = pd.read_json("cursos.json")
df = df.dropna(subset=["descripcion"])     # <-- se eliminan filas...
                                            #     y los índices quedan 0,1,3,7,8...
vectores = modelo.encode(df["texto"].tolist())   # matriz reindexada 0,1,2,3,4...
index = faiss.IndexFlatIP(384)
index.add(vectores)

# Al consultar:
_, posiciones = index.search(consulta, 5)
resultados = df.iloc[posiciones[0]]   # 💥 devuelve el curso EQUIVOCADO
```

La matriz se reindexó de 0 a N−1, pero el DataFrame conservó sus índices
originales con huecos. La posición 2 de la matriz **no** es la fila 2 del
DataFrame. El buscador devuelve el título de un curso con el contenido de otro.

**La solución** es la que planteaba la premisa original:

```python
df = df.dropna(subset=["descripcion"]).reset_index(drop=True)   # 0,1,2,3...
```

#### Metadata Drift — y por qué ChromaDB no lo sufre

ChromaDB **no tiene estructuras paralelas**. Guarda el vector, los metadatos y
el id en la misma fila:

```
┌──────────────┬────────────────────┬──────────────────────────────────┐
│ id           │ embedding (384d)   │ metadata                         │
├──────────────┼────────────────────┼──────────────────────────────────┤
│ curso_0      │ [0.12, -0.44, ...] │ {titulo: "ML Specialization",    │
│              │                    │  categoria: "IA y ML", url: ...} │
├──────────────┼────────────────────┼──────────────────────────────────┤
│ curso_57     │ [0.88,  0.03, ...] │ {titulo: "Ethical Hacking", ...} │
└──────────────┴────────────────────┴──────────────────────────────────┘
```

Al consultar, Chroma devuelve las tres cosas juntas y ya emparejadas. **No hay
dos índices que puedan descuadrarse.** Por eso `reset_index(drop=True)` no
aplica a nuestra arquitectura: no hay un DataFrame vivo en el camino.

#### Dónde SÍ existía el riesgo en nuestro código

En el único punto donde sí construimos listas paralelas: el momento de indexar.

```python
documentos.append(texto)                    # lista 1
metadatas.append(construir_metadatos(item)) # lista 2
ids.append(f"curso_{posicion}")             # lista 3
```

Si una de las tres se saltara un `append` bajo alguna condición, se desalinearían
para siempre. Lo blindamos de dos formas:

1. **Por construcción**: los tres `append` viven en el mismo paso del bucle, sin
   ningún `continue` entre ellos. O se añaden los tres, o ninguno.
2. **Por pruebas**: `TestPreparacionDelLote` verifica la alineación y que los
   ids conserven la **posición original del dataset**, no el contador de
   aceptados:

```python
def test_los_ids_conservan_la_posicion_original_del_dataset(self):
    cursos = [
        {"clean_title": "Uno", "clean_intro": "Primer curso de la lista."},
        {"full_text": "  "},                       # se descarta
        {"clean_title": "Tres", "clean_intro": "Tercer curso de la lista."},
    ]
    _, _, ids, _ = preparar_lote(cursos)
    assert ids == ["curso_0", "curso_2"]           # NO ["curso_0", "curso_1"]
```

Ese detalle es lo que permite rastrear cualquier resultado hasta su fila exacta
en `cursos_dataset.json` para depurar.

---

### 2.3 El problema de los valores *truthy* en Python

El defecto que más contaminó los resultados, y el más fácil de pasar por alto.

#### La regla

`if valor:` no pregunta "¿tiene contenido?". Pregunta "¿es *truthy*?". Python
considera falsos únicamente a:

```python
False, None, 0, 0.0, "", [], {}, set(), ()
```

**Todo lo demás es verdadero.** Incluyendo:

```python
bool(" ")       # True  <- un espacio
bool("   ")     # True  <- tres espacios
bool("nan")     # True  <- el string "nan"
bool("None")    # True  <- el string "None"
bool("0")       # True  <- el string "0"
bool(float("nan"))  # True  <- ¡el NaN de pandas!
```

#### Cómo se manifestó

```python
# El código original
text_to_embed = item.get("full_text") or f"{titulo} {skills} {intro}"
```

La intención era clara: *"usa `full_text`; si está vacío, arma el texto con los
otros campos"*. Pero en 378 registros `full_text` valía `"   "` — que es
**truthy** — así que el `or` devolvía los espacios y **el respaldo nunca se
ejecutaba**.

#### Por qué eso destruye una búsqueda semántica

Un texto vacío o casi vacío no produce "ningún vector": produce un vector
**arbitrario**, dominado por el sesgo interno del modelo. Ese vector cae a una
distancia intermedia de *cualquier* consulta.

```
    consulta: "machine learning"
         │
         ▼
    ┌─────────────────────────────────────────────────┐
    │  0.85  Machine Learning with Python      ✓       │
    │  0.78  Applied ML in Python              ✓       │
    │  0.51  <curso con full_text = "   ">     ✗ ←──── se cuela
    │  0.49  <curso con full_text = "4 hours"> ✗ ←──── se cuela
    │  0.47  Deep Learning Specialization      ✓       │
    └─────────────────────────────────────────────────┘
```

No están arriba del todo, pero desplazan resultados legítimos. Multiplicado por
~580 registros contaminados sobre 8.710, aparecen en casi toda consulta.

#### De dónde vienen esos valores

Del ETL. Cuando pandas exporta a JSON sin `fillna()`, un `NaN` se serializa como
`null` o como el string `"nan"`. Y si una columna se corre durante el `merge`,
acabas con la duración en la columna de texto:

```json
{"Title": "4 hours", "full_text": "   ", "clean_skills": "nan"}
```

#### La corrección

Una función explícita, no un `or`:

```python
MARCADORES_NULOS = frozenset(
    {"", "nan", "none", "null", "n/a", "na", "-", "--", "sin titulo", "sin título"}
)

def es_valor_nulo(valor) -> bool:
    if valor is None:
        return True
    # NaN es el único float que no es igual a sí mismo.
    if isinstance(valor, float) and valor != valor:
        return True
    if not isinstance(valor, str):
        return False
    return valor.strip().lower() in MARCADORES_NULOS
```

Y sobre ella, una cascada que sí funciona:

```python
def primer_valor(item: dict, *claves: str, defecto: str = "") -> str:
    for clave in claves:
        valor = texto_limpio(item.get(clave))
        if valor:              # aquí ya es seguro: texto_limpio devuelve "" si era nulo
            return valor
    return defecto
```

> **Truco a recordar:** `float("nan") != float("nan")` es `True`. NaN es el único
> valor de Python que no es igual a sí mismo, y es la forma canónica de
> detectarlo sin importar pandas ni numpy.

#### La lección general

> Cuando limpies datos de un ETL, **nunca uses `or` ni `if valor:` como filtro de
> nulos**. Escribe un predicado explícito y pruébalo con los casos reales del
> dataset: `""`, `" "`, `"nan"`, `"None"`, `float("nan")`, `None`.

---

## 3. El pipeline vectorial de AthenIA

### Vista completa

```
┌──────────────────────────────────────────────────────────────────────────┐
│  1. ORIGEN — equipo de Data                                              │
│     Data/cursos_dataset.json  ·  8.710 registros  ·  52 columnas         │
│     Campos: Title, URL, Short Intro, Category, Rating, Site,             │
│             clean_title, clean_intro, clean_skills, full_text,           │
│             target_category                                              │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  2. LIMPIEZA — app/busqueda/limpieza.py            (dominio puro, sin I/O)│
│                                                                          │
│     es_valor_nulo()      None · NaN · "" · " " · "nan" · "N/A"           │
│     es_solo_duracion()   "4 hours" · "45 min" · "3 semanas"              │
│     es_texto_indexable() ≥15 caracteres y ≥2 palabras reales             │
│     primer_titulo()      salta títulos que son una duración              │
│     preparar_lote()      deduplica y alinea documentos/metadatos/ids     │
│                                                                          │
│     8.710 entran  →  5.066 indexables  ·  3.644 descartados (41,8%)      │
│                       ├─ 351 sin texto aprovechable                      │
│                       └─ 3.293 duplicados exactos de otra fila           │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  3. EMBEDDING — sentence-transformers                                    │
│     paraphrase-multilingual-MiniLM-L12-v2  ·  384 dimensiones            │
│                                                                          │
│     Multilingüe: vectoriza español e inglés al MISMO espacio, así que    │
│     "seguridad informática" encuentra "Ethical Hacking".                 │
│     Lotes de 500 documentos para no agotar la RAM de la VM de OCI.       │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  4. ÍNDICE — ChromaDB PersistentClient                                   │
│     backend/app/data/vector_db/  ·  colección "athenex_courses"          │
│     metadata={"hnsw:space": "cosine"}   ← INMUTABLE tras crearla         │
│                                                                          │
│     Cada fila: id + vector(384) + metadatos                              │
│     (titulo, descripcion, categoria, url, sitio, habilidades, valoracion)│
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │   hasta aquí: offline (build)       │
              │   de aquí abajo: en cada request    │
              └──────────────────┬──────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  5. ALMACÉN — app/busqueda/almacen.py::AlmacenChroma                     │
│     Único módulo del proyecto que importa `chromadb`.                    │
│                                                                          │
│     · Apertura perezosa con lock (una vez por proceso, no por request)   │
│     · Verifica hnsw:space al abrir → log ERROR si no es cosine           │
│     · query(include=["metadatas", "distances", "documents"])             │
│     · Degrada a [] sin lanzar si falta el índice o la dependencia        │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │  [{id, distancia, metadatos, documento}]
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  6. SERVICIO — app/busqueda/servicio.py::BuscadorCursos                  │
│                                                                          │
│     consulta vacía        → [] sin tocar el índice                       │
│     sobremuestreo ×3      → pide 30 para poder devolver 10 tras filtrar  │
│     match_score = 1 − d   → acotado a [0, 1]                             │
│     min_score (0.35)      → corta en el primero bajo umbral (vienen      │
│                             ordenados, no hace falta recorrer el resto)  │
│     dedup por título      → evita 3 tarjetas del mismo curso             │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  7. API — app/routers/cursos.py                                          │
│     GET /cursos/buscar?q=...&limite=10&min_score=0.35                    │
│                                                                          │
│     response_model=RespuestaBusquedaCursos (Pydantic v2)                 │
│       busqueda · total · min_score · total_indexado · resultados[]       │
│     CursoEncontrado:                                                     │
│       id · title · description · category · url · site · match_score     │
│                                                                          │
│     200 + lista vacía  →  sin coincidencias (estado normal)              │
│     422                →  parámetros inválidos                           │
│     nunca 500 por culpa del índice                                       │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  8. FRONTEND — services/api.js::mapearCurso                              │
│     match_score (0..1)  →  probabilidad  →  aPorcentaje() → "85%"        │
│     id estable como key de React (nunca Math.random())                   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Resultados reales del pipeline corregido

```
>>> "quiero aprender machine learning con python"
   0.846  [Inteligencia Artificial y ML]  Machine Learning with Python
   0.782  [Inteligencia Artificial y ML]  Applied Machine Learning in Python
   0.738  [Inteligencia Artificial y ML]  Machine Learning for Accounting with Python

>>> "seguridad informatica y hacking etico"      (consulta ES → cursos EN)
   0.825  [Ciberseguridad y Redes]  Ethical Hacking: An Introduction
   0.822  [Ciberseguridad y Redes]  Ethical Hacker
   0.788  [Ciberseguridad y Redes]  Cyber Security Foundations: Common Malware Attacks

>>> "recetas de cocina italiana"                 (fuera del dominio técnico)
   0.558  [Otras Áreas]  Introduction to Italian
   0.446  [Otras Áreas]  Mastering the Culinary Art of Plating
```

Obsérvese el tercer caso: una consulta fuera del dominio devuelve puntajes
notablemente más bajos. Ése es el comportamiento que hace útil `min_score`.

### Sobre el umbral `min_score = 0.35`

El modelo es **multilingüe**, y ese tipo de modelo genera similitudes altas
incluso entre textos poco relacionados (el espacio vectorial está más
"comprimido" que en un modelo monolingüe). Por eso 0.35 y no 0.6.

| valor | efecto |
|---|---|
| `0.0` | sin filtro — útil para depurar por qué algo no aparece |
| `0.35` | **por defecto**: corta la cola de ruido sin perder coincidencias ES↔EN |
| `0.50` | estricto; empieza a descartar coincidencias válidas entre idiomas |
| `0.80` | prácticamente solo coincidencias literales |

Es un parámetro de la query, no una constante escondida: `?min_score=0.5`.

---

## 4. Buenas prácticas aplicadas

### 4.1 Dependency Inversion con `Protocol`

La regla del proyecto: **las capas altas dependen de abstracciones**. La ruta
HTTP no sabe que existe ChromaDB.

```python
# app/domain/protocols.py
@runtime_checkable
class AlmacenVectorial(Protocol):
    nombre: str
    def esta_disponible(self) -> bool: ...
    def total(self) -> int: ...
    def consultar(self, texto: str, limite: int) -> List[dict]: ...
```

Python usa **tipado estructural**: una clase cumple el `Protocol` por su forma,
sin heredar ni importar nada. Acoplamiento cero.

```
        ┌─────────────────────┐
        │  routers/cursos.py  │   depende de ↓
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │ busqueda/servicio   │   depende de ↓
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────┐
        │  Protocol               │   ← la abstracción
        │  AlmacenVectorial       │
        └──────────▲──────────────┘
                   │ la implementan (sin heredar)
        ┌──────────┴───────┬──────────────────┐
        │  AlmacenChroma   │   AlmacenFalso   │
        │  (producción)    │   (pruebas)      │
        └──────────────────┴──────────────────┘
```

**El beneficio es medible:** las 93 pruebas que no tocan Chroma corren en
**0,72 s** porque inyectan `AlmacenFalso`. Sin la abstracción, cada una
cargaría un modelo de 470 MB.

### 4.2 Inyección de dependencias con FastAPI

```python
# app/dependencies.py — instancia única, compartida entre peticiones
_buscador_cursos = BuscadorCursos(AlmacenChroma())

def get_buscador_cursos() -> BuscadorCursos:
    return _buscador_cursos
```

```python
# app/routers/cursos.py — la ruta pide la abstracción
def buscar_cursos(
    q: str = Query(...),
    buscador: BuscadorCursos = Depends(get_buscador_cursos),
): ...
```

Y en pruebas, sustituir el índice completo es una línea:

```python
app.dependency_overrides[get_buscador_cursos] = lambda: BuscadorCursos(AlmacenFalso(...))
```

### 4.3 *Lazyness* + lock para el modelo

El problema original: se abría un `PersistentClient` y se instanciaba un
`SentenceTransformer` **en cada petición**.

```python
def _abrir(self):
    if self._intentado:              # 1. memoriza incluso el fallo
        return self._coleccion
    with self._lock:                 # 2. Uvicorn corre rutas `def` en threadpool:
        if self._intentado:          #    dos requests simultáneas podrían
            return self._coleccion   #    abrir el cliente a la vez
        self._intentado = True
        self._coleccion = self._construir_coleccion()
    return self._coleccion
```

Tres decisiones deliberadas:

1. **Importación diferida.** `sentence-transformers` se importa dentro de la
   función, no arriba. Importarlo carga PyTorch y añade segundos al arranque de
   FastAPI y a cada ejecución de pytest.
2. **Doble comprobación con lock.** El patrón *double-checked locking*: la
   comprobación barata primero, el lock solo si hace falta.
3. **Memorizar el fallo.** Si el índice no existe, `_intentado = True` evita
   reintentar (y repagar la carga del modelo) en cada request.

Medido: primera consulta **~30 s** (carga del modelo), siguientes **~0,04 s**.

> **Pendiente conocido:** esos 30 s los paga el primer usuario. Un *warm-up* en
> el `lifespan` de FastAPI lo movería al arranque del contenedor. Ver §6.

### 4.4 Fallo ruidoso en los logs, silencioso para el usuario

`AlmacenChroma` **verifica la métrica al abrir** y registra `ERROR` si no es
coseno — precisamente el fallo original, detectado en caliente:

```python
if espacio != "cosine":
    logger.error(
        "El indice '%s' usa la metrica '%s' en lugar de 'cosine'. Los puntajes "
        "no seran fiables. Reconstruye con: python backend/scripts/build_embeddings.py",
        coleccion.name, espacio,
    )
```

Al mismo tiempo, ningún fallo del índice tumba la API: `consultar()` devuelve
`[]` y la ruta responde 200 con lista vacía. El Dashboard sigue vivo aunque el
buscador no lo esté.

### 4.5 Single Responsibility, en la práctica

El código original tenía la función de búsqueda **pegada tres veces** en
`services.py`, con tres rutas distintas al índice — y la ruta HTTP declarada dos
veces en `routers/contenido.py`. La separación actual:

| módulo | única responsabilidad |
|---|---|
| `busqueda/limpieza.py` | sanear texto (funciones puras, sin I/O) |
| `busqueda/almacen.py` | hablar con ChromaDB |
| `busqueda/servicio.py` | reglas de negocio (umbral, orden, dedup, contrato) |
| `routers/cursos.py` | HTTP: validar entrada, mapear a Pydantic |
| `scripts/build_embeddings.py` | construir el índice (offline) |

Que la conversión distancia→puntaje viva en el **servicio** y no en el
**almacén** es intencional: cambiar de ChromaDB a Oracle AI Vector Search no
debe cambiar las reglas de relevancia.

---

## 5. Operación: reconstruir, verificar, diagnosticar

### Reconstruir el índice

Obligatorio tras cualquier cambio en `limpieza.py`, en el modelo de embeddings o
en el dataset.

```bash
pip install -r backend/requirements.txt && python backend/scripts/build_embeddings.py --forzar
```

Sin `--forzar` el script se niega a tocar una colección existente. Con `--limite N`
indexa solo los primeros N registros (útil para probar en segundos).

### Verificar que el índice quedó bien

```bash
python -c "import sqlite3; c=sqlite3.connect('backend/app/data/vector_db/chroma.sqlite3'); print(c.execute('SELECT key,str_value FROM collection_metadata').fetchall()); print(c.execute('SELECT COUNT(*) FROM embeddings').fetchone())"
```

Debe imprimir `[('hnsw:space', 'cosine')]`. Si sale `[]`, la colección quedó en
L2 y hay que reconstruir.

### Diagnosticar "no encuentra nada"

Por orden de probabilidad:

| síntoma | causa probable | comprobación |
|---|---|---|
| `total_indexado: 0` | falta el índice o `sentence-transformers` | revisar logs al arrancar |
| `total: 0` con `total_indexado > 0` | umbral demasiado alto | repetir con `&min_score=0` |
| puntajes todos ~0.0 | el índice quedó en L2 | consulta SQL de arriba |
| resultados sin relación | el índice no se reconstruyó tras cambiar la limpieza | comparar `total_indexado` con `preparar_lote()` |

El parámetro `min_score=0` es la herramienta de depuración principal: si con
umbral 0 aparecen los cursos correctos pero con puntaje bajo, el problema es de
calibración; si no aparecen ni así, el problema es del índice.

---

## 6. Deuda técnica conocida

Cosas detectadas durante la auditoría que **no** están resueltas. Se documentan
aquí para que el equipo decida, no para que se olviden.

### 6.1 El 72 % del catálogo está etiquetado `Otras Áreas`

```
Otras Áreas                    6.302   (72,4%)
Cloud Computing y DevOps         901
Ciencia de Datos y Analítica     576
Inteligencia Artificial y ML     465
Desarrollo de Software y Web     293
Ciberseguridad y Redes           173
```

Es un problema del `target_category` del dataset, no del buscador. Ningún ajuste
de búsqueda lo compensa: el filtro por categoría del Dashboard es poco útil
mientras 7 de cada 10 cursos caigan en el cajón de sastre. **Acción sugerida:**
que el equipo de Data revise la asignación de categorías.

### 6.2 Los ~30 s de la primera búsqueda

La carga perezosa del modelo se paga en la primera petición. **Acción sugerida:**
un *warm-up* en el `lifespan` de FastAPI que llame a `almacen.total()` al
arrancar, moviendo el coste al despliegue.

### 6.3 El índice vectorial viaja en git

`backend/app/data/vector_db/` ocupa decenas de MB de binarios versionados. Se
mantiene así porque el despliegue en OCI depende de que la imagen lo lleve
horneado (la misma decisión que se tomó con `clasificador_cursos.pkl`).
**Acción sugerida a futuro:** moverlo a OCI Object Storage y descargarlo en el
build.

### 6.4 `docs/.github/workflows/ci.yml`

Copia obsoleta del workflow (Python 3.11, sin caché) en una ruta donde GitHub
**no la ejecuta**. Es inerte, pero confunde a quien la encuentre. **Acción
sugerida:** borrarla.

---

## Referencias

- Código: [`backend/app/busqueda/`](../backend/app/busqueda/)
- Pruebas: [`backend/tests/test_busqueda_vectorial.py`](../backend/tests/test_busqueda_vectorial.py)
- Constructor del índice: [`backend/scripts/build_embeddings.py`](../backend/scripts/build_embeddings.py)
- [ChromaDB — Collections & distance functions](https://docs.trychroma.com/docs/collections/configure)
- [Sentence-Transformers — modelos multilingües](https://www.sbert.net/docs/pretrained_models.html)
