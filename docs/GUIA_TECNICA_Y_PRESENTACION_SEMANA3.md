# Guía Técnica y Presentación — Semana 3

**AthenIA** · Hackathon ONE Alura + Oracle / No Country · Generación 9

Documento de estudio y guion para la presentación en vivo. Todo lo que describe
este documento existe **hoy, en el repositorio, verificado**: 75/75 pruebas
automatizadas en verde, servidor probado en caliente, build de frontend limpio.
No hay nada aspiracional aquí — si algo se describe, se puede mostrar en vivo.

> **Estado verificado al momento de escribir esto:**
> `pytest` → 75 passed · `npm run build` → compila sin errores · `GET /salud` →
> `motor: modelo_ml_real` con `clasificador_cursos.pkl` cargado.

---

## Tabla de contenido

1. [Mapa y arquitectura del repositorio](#1-mapa-y-arquitectura-del-repositorio)
2. [Cómo funciona el modelo de IA y la capa de inferencia](#2-cómo-funciona-el-modelo-de-ia-y-la-capa-de-inferencia)
3. [Refactorización SOLID aplicada](#3-refactorización-solid-aplicada)
4. [Guion paso a paso para la presentación en vivo](#4-guion-paso-a-paso-para-la-presentación-en-vivo)

---

## 1. Mapa y arquitectura del repositorio

### 1.1 Estructura de `backend/`

```
backend/
├── app/
│   ├── main.py                 Composicion de la app FastAPI (119 lineas)
│   ├── config.py               Configuracion por variables de entorno
│   ├── schemas.py               Contratos Pydantic (Request/Response)
│   ├── errors.py                Manejo uniforme de errores HTTP
│   ├── dependencies.py          Proveedores de Depends (el punto DIP)
│   ├── services.py              Casos de uso + raiz de composicion (256 lineas)
│   │
│   ├── domain/                  Abstracciones y reglas de negocio puras
│   │   ├── protocols.py         Protocol `Clasificador`, `RepositorioContenidos`
│   │   └── taxonomia.py         Categorias, palabras clave, normalizacion de texto
│   │
│   ├── ml/                      Motores de clasificacion
│   │   ├── registro.py          El "que motor gana" — extension point (OCP)
│   │   ├── reglas.py            Clasificador por palabras clave (fallback)
│   │   ├── modelo.py            Envoltorio del artefacto de Data Science
│   │   ├── adaptador.py         Normaliza las 3 formas de entrega del .pkl
│   │   └── carga.py             Localizar + deserializar + sondear el .pkl
│   │
│   ├── repositories/            Persistencia
│   │   └── memoria.py           Historial en un `list` (Semana 4: Oracle DB)
│   │
│   └── routers/                 Endpoints HTTP, agrupados por area
│       ├── salud.py             GET /, GET /salud, GET /categorias
│       └── contenido.py         POST /contenido, historial, metricas
│
├── models/
│   ├── clasificador_cursos.pkl  Artefacto entrenado por Data Science
│   └── README.md                Contrato del artefacto para Data Science
│
├── tests/
│   ├── conftest.py               Fixtures (incluye pipelines entrenados al vuelo)
│   └── test_api.py               75 casos de prueba
│
├── Dockerfile                    Imagen multi-stage python:3.13-slim
└── requirements.txt
```

**Por que esta forma y no otra.** Cada carpeta responde a una pregunta distinta:

| Carpeta | Pregunta que responde | Ejemplo |
|---|---|---|
| `domain/` | ¿Que es un "clasificador" para AthenIA? ¿Que categorias existen? | `Protocol Clasificador`, `TAXONOMIA` |
| `ml/` | ¿Como clasificamos, en la practica, con que motor? | `ClasificadorML`, `ClasificadorReglas` |
| `repositories/` | ¿Donde vive el historial? | `RepositorioMemoria` |
| `routers/` | ¿Que URL hace que? | `POST /contenido` |
| `services.py` | ¿Como se combinan las piezas de arriba en un caso de uso? | `analizar_y_guardar()` |

Esta separacion es el eje de la Seccion 3 (SOLID). Aqui basta con saber que
**la direccion de las dependencias siempre apunta hacia `domain/`**:
`routers` → `services` → `domain`, y tanto `ml/` como `repositories/`
implementan lo que `domain/` define, sin que `domain/` sepa que existen.

### 1.2 Estructura de `frontend/`

```
frontend/src/
├── pages/              Dashboard, AgregarContenido, BuscarContenidos, Categorias
├── components/         Sidebar, Header, ContentForm, AnalysisResult, CourseCard...
├── hooks/               useContenidos, useMetricas, useCategorias
├── services/api.js      UNICO modulo que conoce la URL del backend
└── data/categorias.js   Colores y formato de presentacion por categoria
```

El frontend no está estructurado con clases ni con el vocabulario SOLID
clásico (React no es orientado a objetos), pero aplica el mismo *principio*
de separación por responsabilidad:

- **`services/api.js`** es el único punto que sabe hacer HTTP. Ninguna
  página ni componente usa `fetch`/`axios` directamente — equivalente
  funcional del DIP: las páginas dependen de funciones (`analizarContenido`,
  `obtenerContenidos`), no de los detalles de axios.
- **`hooks/`** encapsulan el *cómo* se obtienen los datos (debounce,
  cancelación de peticiones obsoletas con `AbortController`); las páginas
  solo consumen `{ items, cargando, error }`.
- **`components/`** son presentacionales: reciben props, no llaman a la API.
- **`data/categorias.js`** centraliza el mapeo categoría→color, para que
  ningún componente tenga colores hardcodeados.

### 1.3 Flujo de datos completo (React → FastAPI → ML → React)

```
┌─────────────┐   1. Usuario escribe    ┌──────────────────────┐
│   React     │   titulo + texto en     │  ContentForm.jsx      │
│  (Browser)  │   "Agregar Contenido"   │  valida en cliente     │
└──────┬──────┘                         └───────────┬───────────┘
       │                                             │
       │ 2. POST /contenido                          │
       │    { titulo, texto, origen?, url? }         ▼
       │                                    services/api.js
       │                                    (unico modulo que conoce
       ▼                                     la URL del backend)
┌─────────────────────────────────────────────────────────────────┐
│  FASTAPI — routers/contenido.py :: analizar_contenido()          │
│                                                                    │
│  3. ContenidoInput valida (schemas.py) -> 422 si esta mal          │
│  4. Depends(get_clasificador) resuelve el motor ACTIVO             │
│     (dependencies.py -> services.clasificador)                     │
│  5. Depends(get_repositorio) resuelve el historial ACTIVO          │
└───────────────────────────┬───────────────────────────────────────┘
                             │
                             │ 6. services.analizar_y_guardar(payload, motor, historial)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAPA ML — el motor activo clasifica                               │
│                                                                    │
│   ¿Hay clasificador_cursos.pkl cargado y verificado?                │
│        │                                                          │
│    SI ─┴─ ml/modelo.py :: ClasificadorML.clasificar()               │
│           - concatena "titulo. texto"                              │
│           - pipeline.predict_proba([texto]) -> categoria + %       │
│           - domain/taxonomia.py extrae palabras clave              │
│           - si predict() lanza -> fallback a reglas EN CALIENTE     │
│                                                                    │
│    NO ─── ml/reglas.py :: ClasificadorReglas.clasificar()           │
│           - coincidencia de palabras clave contra domain/taxonomia │
│           - 100% determinista, sin dependencias externas           │
└───────────────────────────┬───────────────────────────────────────┘
                             │
                             │ 7. resultado = {categoria, probabilidad, ...}
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  repositories/memoria.py :: RepositorioMemoria.agregar()           │
│  8. Guarda el registro con id + creado_en (thread-safe, con lock)  │
└───────────────────────────┬───────────────────────────────────────┘
                             │
                             │ 9. AnalisisOutput(**registro) -> JSON
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  React recibe { categoria, probabilidad, informacion_adicional }   │
│  10. AnalysisResult.jsx renderiza la tarjeta con badge de colores   │
│  11. Dashboard.jsx y BuscarContenidos.jsx reflejan el nuevo item     │
│      en su siguiente fetch a GET /metricas y GET /contenidos        │
└─────────────────────────────────────────────────────────────────┘
```

**El punto que hay que remarcar en la demo:** el paso 6 (`analizar_y_guardar`)
nunca importa `ClasificadorML` ni `RepositorioMemoria` directamente — recibe
`motor` y `historial` ya resueltos desde `Depends`. Si mañana Data Science
entrega un motor de embeddings, este flujo **no cambia ni una línea**; solo
cambia qué construye `ml/registro.py` en el paso 4.

---

## 2. Cómo funciona el modelo de IA y la capa de inferencia

### 2.1 TF-IDF + Naive Bayes, explicado sin jerga

El artefacto real (`backend/models/clasificador_cursos.pkl`) es un
`sklearn.pipeline.Pipeline` con dos pasos encadenados:

```python
Pipeline([
    ("tfidf", TfidfVectorizer(...)),   # paso 1: texto -> numeros
    ("classifier", MultinomialNB()),   # paso 2: numeros -> categoria
])
```

**Paso 1 — `TfidfVectorizer` (¿cómo convertir texto en números?)**

Un modelo no entiende palabras, entiende números. TF-IDF ("Term
Frequency – Inverse Document Frequency") convierte cada texto en un vector
donde cada posición representa una palabra, y el valor mide qué tan
*distintiva* es esa palabra para ese texto en particular:

- **TF (frecuencia del término):** cuántas veces aparece la palabra en
  *este* texto. "Docker" aparece 3 veces → cuenta más que si aparece 1 vez.
- **IDF (frecuencia inversa de documento):** qué tan *rara* es la palabra en
  *todo* el corpus de entrenamiento. Palabras como "el", "de", "curso"
  aparecen en casi todos los textos → aportan poco. Palabras como
  "Kubernetes" o "TensorFlow" aparecen solo en textos de una categoría →
  aportan mucho.

El resultado es que palabras genéricas pesan poco y palabras técnicas
específicas pesan mucho — exactamente lo que se necesita para distinguir
"un curso de Docker" de "un curso de Pandas".

**Paso 2 — `MultinomialNB` (¿cómo decide la categoría?)**

Naive Bayes Multinomial aplica el teorema de Bayes: para cada categoría
posible, calcula "dado que vi estas palabras con estas frecuencias, ¿qué
tan probable es que este texto pertenezca a esta categoría?", basándose en
qué tan seguido aparecieron esas mismas palabras en los textos de
entrenamiento de cada categoría. Se llama "naive" (ingenuo) porque asume que
las palabras son independientes entre sí (una simplificación que en la
práctica funciona sorprendentemente bien para clasificación de texto).

`predict_proba()` devuelve la probabilidad para **cada** categoría, no solo
la ganadora — por eso `ClasificadorML.clasificar()` (`ml/modelo.py:67-76`)
puede reportar tanto la categoría principal como las `categorias_relacionadas`
(las siguientes más probables) con una sola llamada al modelo.

**Por qué es la elección correcta para este problema:** con un dataset de
tamaño moderado (miles de cursos, no millones), TF-IDF + Naive Bayes es
rápido de entrenar, rápido de inferir (sin GPU, sin latencia de red a un
proveedor externo) y fácil de auditar — se puede inspeccionar qué palabras
pesan más para cada categoría. Un LLM sería más caro, más lento y sería
"caja negra" para explicar en la demo.

### 2.2 El cargador dinámico de modelos

`ml/carga.py::cargar_modelo_entrenado()` es la única función del backend que
toca el sistema de archivos para el modelo. Hace 4 cosas en secuencia, y
**cualquiera de ellas puede fallar sin tumbar la API**:

```python
def cargar_modelo_entrenado() -> Optional[Clasificador]:
    ruta = localizar_modelo()          # 1. ¿existe el archivo?
    if ruta is None:
        return None

    artefacto = _deserializar(ruta)     # 2. joblib.load(), si falla -> pickle.load()
    adaptador = AdaptadorModelo(artefacto)  # 3. ¿tiene forma de modelo?
    adaptador.predict([TEXTO_SONDA])    # 4. ¿predice de verdad?

    return ClasificadorML(adaptador, ruta)
```

- **Localizar** (`localizar_modelo()`): busca `ATHENIA_MODELO_PATH` si está
  definido; si no, recorre `ATHENIA_MODELOS_DIR` buscando nombres conocidos
  (`clasificador_cursos.pkl` primero); si tampoco, toma el `.pkl`/`.joblib`
  más reciente que encuentre. Devuelve `None` si no hay nada.
- **Deserializar** (`_deserializar()`): intenta `joblib.load()` primero
  (formato nativo de scikit-learn, maneja bien arrays de NumPy grandes); si
  falla, reintenta con `pickle.load()` estándar. Dos formatos, un solo
  camino de entrada.
- **Adaptar** (`AdaptadorModelo`, en `ml/adaptador.py`): Data Science puede
  entregar un `Pipeline` completo, un `dict` con el modelo y el
  vectorizador por separado, o una tupla. El adaptador detecta la forma por
  **duck typing** (`hasattr(x, "predict")`, `hasattr(x, "transform")`) y
  expone siempre la misma interfaz `predict()`/`predict_proba()`.
- **Sondear**: antes de activar el modelo, se ejecuta **una predicción de
  prueba real** con un texto fijo (`TEXTO_SONDA`). Un modelo que carga en
  memoria pero no puede predecir sobre texto crudo (por ejemplo, si se
  guardó sin su vectorizador) se descarta *aquí*, antes de que el jurado
  mande la primera petición real. Esto está probado explícitamente en
  `test_sonda_de_carga_descarta_modelos_inservibles` (CP-104).

Si **cualquiera** de las 4 etapas falla, la función devuelve `None` en vez
de lanzar una excepción. `ml/registro.py::RegistroProveedores.resolver()`
interpreta ese `None` como "este proveedor no está disponible" y cae al
`ClasificadorReglas` — sin que nadie tenga que capturar nada en las rutas
HTTP.

**Adicionalmente**, incluso con el modelo ya cargado y verificado,
`ClasificadorML.clasificar()` envuelve la llamada real a `predict()` en un
`try/except` (`ml/modelo.py:60-89`): si el modelo falla en una petición
puntual (texto raro, encoding inesperado), esa petición individual cae a
reglas y queda marcada como `"modelo": "reglas-keywords-v1 (fallback en
inferencia)"` — la API responde 200, nunca 500.

### 2.3 Por qué fue crítico alinear scikit-learn a 1.6.1

Al integrar el `.pkl` real por primera vez, cargó — pero scikit-learn emitió:

```
InconsistentVersionWarning: Trying to unpickle estimator TfidfVectorizer
from version 1.6.1 when using version 1.9.0. This might lead to breaking
code or invalid results.
```

**Por qué pasa esto:** un objeto de scikit-learn serializado con `pickle`
guarda su estado interno (pesos, vocabulario, parámetros) tal como estaban
en la versión que lo entrenó. Entre versiones mayores de scikit-learn, la
estructura interna de esos objetos puede cambiar — un atributo que antes se
llamaba de una forma ahora se llama de otra, o cambia de tipo. El objeto
deserializado puede "verse" cargado correctamente y aun así comportarse mal
en la práctica: predicciones ligeramente distintas, o un error oculto que
solo aparece con ciertos inputs.

**Por qué era grave para esta demo específicamente:** un warning no tumba la
API — pero significa que el jurado podría ver números de confianza que no
son exactamente los que Data Science midió al entrenar el modelo, y en el
peor caso, silenciosamente equivocados sin ningún error visible.

**La corrección:** fijar `scikit-learn==1.6.1` en `backend/requirements.txt`
para igualar exactamente la versión de entrenamiento. Se verificó cargando
el artefacto con `-W error::UserWarning` (que convierte cualquier warning en
excepción) y confirmando cero warnings — ver el pin exacto en
`backend/requirements.txt`.

**La lección operativa para el equipo:** la versión de scikit-learn **es
parte del contrato del modelo**, tan importante como el nombre del archivo.
Si Data Science reentrena con otra versión, ese cambio debe venir acompañado
de actualizar el pin en `requirements.txt` en el mismo commit — está
documentado explícitamente en `backend/models/README.md`, sección
"Versiones".

---

## 3. Refactorización SOLID aplicada

### 3.1 El problema real que había (con números)

Antes del refactor de esta semana, dos archivos concentraban toda la lógica:

| Archivo | Líneas | Responsabilidades mezcladas |
|---|---|---|
| `services.py` | 929 | Taxonomía + 2 clasificadores + adaptador + carga de modelo + persistencia + métricas + datos demo |
| `main.py` | 383 | App factory + CORS + middleware + 3 exception handlers + 8 rutas HTTP |

Después:

| Archivo | Líneas | Responsabilidad única |
|---|---|---|
| `services.py` | 256 | Casos de uso + raíz de composición |
| `main.py` | 119 | App factory + registro de routers |
| `domain/` (2 archivos) | 336 | Abstracciones + reglas de negocio |
| `ml/` (5 archivos) | 595 | Motores de clasificación |
| `repositories/` (1 archivo) | 114 | Persistencia |
| `routers/` (2 archivos) | 233 | Endpoints HTTP |

**El total de líneas no bajó** (de hecho subió, por la documentación de cada
límite) — lo que cambió es que ahora cada archivo responde a **una sola
pregunta**, y se puede leer, probar y modificar sin cargar mentalmente el
resto del sistema.

### 3.2 SRP — Single Responsibility Principle

> *"Una clase (o módulo) debe tener una, y solo una, razón para cambiar."*

**Antes:** `services.py` cambiaba por seis razones distintas: si cambiaba la
taxonomía de categorías, si cambiaba el algoritmo de scoring de reglas, si
cambiaba el formato del artefacto `.pkl`, si cambiaba la forma de buscar el
archivo en disco, si cambiaba cómo se guarda el historial, o si cambiaba
cómo se calculan las métricas del Dashboard. Cualquiera de esos seis cambios
tocaba el mismo archivo de 929 líneas.

**Después**, cada razón de cambio vive en su propio archivo:

```
"Cambió qué tecnologías detecta la categoría Backend"
    -> domain/taxonomia.py   (el diccionario TAXONOMIA)

"Cambió cómo se pondera título vs. cuerpo en el fallback"
    -> ml/reglas.py          (ClasificadorReglas.PESO_TITULO)

"Data Science entrega el modelo en un dict en vez de un Pipeline"
    -> ml/adaptador.py       (AdaptadorModelo._descomponer)

"Cambió el nombre del archivo que se busca en backend/models/"
    -> ml/carga.py           (NOMBRES_ARTEFACTO)

"El historial ahora vive en Oracle en vez de en memoria"
    -> repositories/memoria.py  (se reemplaza por repositories/oracle.py)

"Cambió qué endpoints expone la API"
    -> routers/*.py
```

Concretamente en `routers/salud.py` vs. el `main.py` original: antes, el
handler de `GET /salud` estaba en el mismo archivo que el `lifespan`, el
middleware CORS y los 3 exception handlers. Hoy, `routers/salud.py` (75
líneas) solo tiene 3 endpoints relacionados con estado/meta; `errors.py`
(104 líneas) solo tiene los exception handlers; `main.py` (119 líneas) solo
ensambla las piezas.

### 3.3 OCP — Open/Closed Principle

> *"Las entidades de software deben estar abiertas a extensión, pero
> cerradas a modificación."*

**Antes**, `obtener_clasificador()` era una cadena `if/else` cerrada:

```python
# como era antes (services.py, version pre-refactor)
def obtener_clasificador() -> ClasificadorBase:
    ruta = localizar_modelo()
    if ruta is None:
        return ClasificadorReglas()
    ...
    return ClasificadorML(adaptador, ruta)
```

Si en la Semana 4 llega un motor de embeddings o un LLM, la única forma de
integrarlo era **editar esta función** — agregar un tercer `if`, cambiar el
orden de las condiciones, tocar código que ya estaba probado y funcionando.

**Después**, existe un registro (`ml/registro.py`) que resuelve el motor
activo sin conocer ninguno por nombre:

```python
# ml/registro.py — RegistroProveedores.resolver()
def resolver(self) -> Clasificador:
    for proveedor in sorted(self._proveedores, key=lambda p: p.prioridad):
        motor = proveedor.cargar()
        if motor is not None:
            return motor
    return ClasificadorReglas()   # unica garantia incondicional
```

Y el registro se **puebla** por composición, no por lógica condicional:

```python
# ml/__init__.py — el UNICO lugar donde se listan los motores conocidos
registro.registrar("modelo-ml", carga.cargar_modelo_entrenado, prioridad=10)
```

**La prueba de que esto es real, no solo un diseño bonito:**
`test_ocp_nuevo_proveedor_se_integra_sin_tocar_el_registro` (CP-106, en
`backend/tests/test_api.py`) construye un clasificador falso que simula el
motor de la Semana 4, lo registra con prioridad más alta que el modelo ML,
y confirma que `resolver()` lo elige — **sin haber tocado
`RegistroProveedores`, `ClasificadorML` ni ninguna ruta**. Ejecutarla en
vivo es la evidencia más fuerte que se puede mostrar en la presentación.

**Cómo se vería agregar el motor de la Semana 4 en la práctica:**

```python
# 1. archivo NUEVO: ml/embeddings.py
class ClasificadorEmbeddings:
    nombre = "embeddings-openai-v1"
    motor = "modelo_ml_real"
    ...
    def clasificar(self, titulo, texto): ...
    def categorias(self): ...

def cargar() -> Optional[Clasificador]:
    ...

# 2. UNA linea nueva en ml/__init__.py, nada mas:
registro.registrar("embeddings", embeddings.cargar, prioridad=5)
```

Cero líneas modificadas en `ml/registro.py`, `ml/modelo.py`,
`ml/reglas.py`, cualquier router, o `services.py`.

### 3.4 DIP — Dependency Inversion Principle

> *"Los módulos de alto nivel no deben depender de módulos de bajo nivel;
> ambos deben depender de abstracciones."*

**Antes**, las rutas leían un global concreto del módulo `services`:

```python
# main.py, version pre-refactor
@app.get("/salud")
def salud():
    return SaludOutput(
        motor=services.clasificador.motor,      # <- acoplado al modulo
        modelo_cargado=services.clasificador.nombre,
        ...
    )
```

Esto acopla la ruta HTTP directamente al estado mutable de un módulo
concreto. Probar esa ruta con un clasificador distinto significaba
monkey-patchear `services.clasificador` a mano.

**Después**, la abstracción vive en `domain/protocols.py`:

```python
# domain/protocols.py:39
class Clasificador(Protocol):
    nombre: str
    motor: str
    es_mock: bool
    detalle: str
    def clasificar(self, titulo: str, texto: str) -> dict: ...
    def categorias(self) -> List[str]: ...
```

`dependencies.py` expone un *proveedor* que resuelve la instancia activa:

```python
# dependencies.py:40
def get_clasificador() -> Clasificador:
    return services.clasificador
```

Y las rutas dependen del **tipo abstracto**, no de la implementación:

```python
# routers/contenido.py:42-45
def analizar_contenido(
    payload: ContenidoInput,
    clasificador: Clasificador = Depends(get_clasificador),   # <- Protocol, no ClasificadorML
    repositorio: RepositorioContenidos = Depends(get_repositorio),
) -> AnalisisOutput:
    ...
```

La firma de la función dice `Clasificador`. Nunca importa `ClasificadorML`
ni `ClasificadorReglas`. Ese es el DIP: la ruta (módulo de alto nivel)
depende de una abstracción (`domain.protocols.Clasificador`), y las
implementaciones concretas (módulos de bajo nivel: `ml.modelo`, `ml.reglas`)
también dependen de esa misma abstracción — ninguna de las dos depende
directamente de la otra.

**La prueba de que esto es real:**
`test_dip_las_rutas_dependen_del_protocol_no_de_la_implementacion` (CP-107)
usa `app.dependency_overrides[get_clasificador] = lambda: ClasificadorDoble()`
— el mecanismo estándar de FastAPI para sustituir dependencias — y confirma
que `POST /contenido` responde con la categoría del doble de prueba, **sin
tocar el estado global de `services`**. Si la ruta dependiera del módulo
concreto en vez de la abstracción inyectada, este `override` no tendría
ningún efecto.

**El mismo patrón para persistencia:** `RepositorioContenidos` (Protocol) →
`RepositorioMemoria` hoy, `RepositorioOracle` en la Semana 4 — mismo
mecanismo, mismo punto de extensión (`dependencies.py::get_repositorio`).

### 3.5 Lo que se dejó fuera a propósito

Para ser honestos frente a preguntas técnicas: este refactor **no** introduce
un contenedor de inyección de dependencias de terceros (`dependency-injector`,
`punq`), ni convierte `services.py` en un objeto instanciable en vez de un
módulo con globals. Para el tamaño de este proyecto (un hackathon de 5
semanas), un módulo como raíz de composición con `Depends` de FastAPI es
suficiente y es exactamente el patrón que la documentación oficial de
FastAPI recomienda. Un contenedor DI de terceros sería sobre-ingeniería para
este alcance — mencionarlo en la presentación como decisión consciente, no
como limitación.

---

## 4. Guion paso a paso para la presentación en vivo

Duración estimada: **12-15 minutos** + preguntas. Todo lo que sigue se puede
ejecutar en vivo; nada es simulado.

### Pantalla 0 — Antes de empezar (checklist, 2 min antes)

```bash
cd "proyecto mvp hakaton"
npm run dev
```

Esperar a ver en la terminal:
```
[BACKEND]  Motor de clasificacion: modelo_ml_real | artefacto: clasificador_cursos.pkl
[FRONTEND] Local:   http://localhost:5173/
```

Abrir en el navegador: `http://localhost:5173` y `http://localhost:8000/docs`
(Swagger) en pestañas separadas. Tener una terminal libre para correr
`pytest` en vivo más adelante.

---

### Pantalla 1 — Propuesta de valor (1 min)

**Decir:** "AthenIA recibe contenido técnico en texto libre, lo clasifica
con un modelo real de Machine Learning, extrae las tecnologías mencionadas,
y guarda un historial consultable. Todo el flujo que van a ver ahora corre
con el modelo entrenado por Data Science, no con datos simulados."

**Mostrar:** el Dashboard en `localhost:5173` — señalar el badge morado
"Modelo IA" en el header (no "Reglas").

---

### Pantalla 2 — Análisis en vivo (2 min)

**Hacer:** ir a "Agregar Curso", pegar un texto real (ej. sobre Kubernetes o
Machine Learning), pulsar "Analizar con IA".

**Decir mientras carga:** "Esto que están viendo pasa por 4 pasos internos:
localizar el modelo, deserializarlo, adaptarlo a una interfaz común, y
verificarlo con una predicción de prueba — eso ya pasó al arrancar el
servidor. Lo que ven ahora es solo la inferencia."

**Mostrar el resultado:** categoría, % de confianza, palabras clave,
categorías relacionadas. Señalar: "La probabilidad viene directo de
`predict_proba()` del modelo — no es un número inventado."

---

### Pantalla 3 — `GET /salud` en vivo (1.5 min)

**Ejecutar en terminal o en Swagger:**

```bash
curl http://localhost:8000/salud
```

**Mostrar la respuesta y señalar el campo `motor`:**

```json
{
  "motor": "modelo_ml_real",
  "modelo_cargado": "clasificador_cursos.pkl",
  "detalle_modelo": "Pipeline",
  "es_mock": false
}
```

**Decir:** "Este endpoint es la prueba de vida del sistema. Si algo le pasa
al modelo, este campo pasa a `clasificador_reglas` automáticamente y la API
sigue respondiendo — se los voy a demostrar en el siguiente paso."

---

### Pantalla 4 — Demostración de resiliencia (2 min, la más impactante)

**Hacer (en la terminal, con el servidor corriendo):**

```bash
# Renombrar el modelo para simular que "desaparece"
mv backend/models/clasificador_cursos.pkl backend/models/clasificador_cursos.pkl.bak
curl -X POST http://localhost:8000/... # o simplemente recargar /salud tras reiniciar
```

> Nota operativa: como el modelo se resuelve al arrancar el proceso, para
> esta demo es más limpio **reiniciar el backend** después de renombrar el
> archivo (`Ctrl+C` en la terminal de `npm run dev` y volver a correrlo), o
> preparar de antemano una segunda terminal con el backend apuntando a una
> carpeta de modelos vacía (`ATHENIA_MODELOS_DIR`) para alternar sin
> reiniciar. Practicar esta parte antes, una vez, para que salga fluida.

**Mostrar:** `GET /salud` ahora responde `"motor": "clasificador_reglas"`,
`"es_mock": true` — **y la aplicación web sigue funcionando exactamente
igual**, se puede seguir analizando contenido.

**Decir:** "Esto no es un accidente — es una decisión de arquitectura. El
sistema tiene 4 capas de verificación antes de confiar en el modelo, y si
cualquiera falla, cae a un clasificador por reglas 100% determinista. La
demo nunca se cae por un problema del modelo." (Restaurar el archivo antes
de seguir: `mv backend/models/clasificador_cursos.pkl.bak
backend/models/clasificador_cursos.pkl` y reiniciar.)

---

### Pantalla 5 — La suite de pruebas (2 min)

**Ejecutar en vivo:**

```bash
pytest
```

**Mientras corre, decir:** "75 pruebas automatizadas, corren en menos de 10
segundos porque no dependen de un servidor levantado — usan el TestClient
de FastAPI directamente en memoria."

**Mostrar el resultado:** `75 passed`. Señalar en el output (si se corre con
`-v`) los nombres `test_ocp_...` y `test_dip_...`:

```bash
pytest -v -k "ocp or dip"
```

**Decir:** "Estas dos pruebas específicamente no verifican una regla de
negocio — verifican la arquitectura misma. Una prueba que un motor nuevo se
integra sin tocar código existente; la otra, que las rutas dependen de una
abstracción y no de una implementación concreta."

---

### Pantalla 6 — El código de la arquitectura (3 min, para audiencia técnica)

Abrir en el editor, en este orden, y leer en voz alta la línea señalada:

1. **`backend/app/domain/protocols.py:39`** — `class Clasificador(Protocol)`.
   "Este es el contrato. Todo motor de clasificación debe cumplir esta
   forma."

2. **`backend/app/ml/registro.py:38-63`** — `class RegistroProveedores`.
   "Este es el único lugar del backend donde se decide qué motor está
   activo. No hay un segundo `if/else` escondido en ningún otro archivo."

3. **`backend/app/routers/contenido.py:42-45`** — la firma de
   `analizar_contenido`. "Miren el tipo: `Clasificador`, no `ClasificadorML`.
   La ruta no sabe si detrás hay un Pipeline de scikit-learn o un modelo de
   embeddings."

**Cerrar con la tabla de antes/después** (Sección 3.1 de este documento) —
"929 líneas en un archivo bajaron a 256, y las responsabilidades que se
sacaron no desaparecieron: viven en 8 archivos nuevos, cada uno con una
sola razón para cambiar."

---

### Preguntas difíciles y cómo responderlas

#### PM: "¿Cuánto tiempo/riesgo agregó este refactor a la Semana 3?"

**Responder:** "Se hizo *después* de que la integración del modelo ya
estaba funcionando y con 73 pruebas en verde — esa era la base. El refactor
no cambió ningún comportamiento observable: mismas 8 rutas, mismos
contratos JSON, mismos 73 casos de prueba pasando sin modificar su lógica
(solo se agregaron 2 pruebas nuevas). El riesgo se controló verificando la
suite completa después de cada capa movida, no al final."

#### PM: "¿Por qué invertir tiempo en esto en vez de features nuevas?"

**Responder:** "Dos razones concretas, no abstractas: primero, el motor de
Data Science va a cambiar — hoy es TF-IDF+Naive Bayes, la Semana 4 puede
traer embeddings o un LLM. Con la arquitectura anterior, ese cambio
significaba editar una función de 60 líneas con lógica condicional ya
probada. Ahora es agregar un archivo. Segundo, con Oracle Database
reemplazando el historial en memoria, el mismo patrón aplica: se cambia
`repositories/memoria.py` por `repositories/oracle.py` sin tocar rutas."

#### Data Science: "¿Por qué scikit-learn 1.6.1 y no la última versión?"

**Responder:** "Porque es la versión exacta con la que se entrenó
`clasificador_cursos.pkl`. Con una versión más nueva (probamos con 1.9.0),
el modelo carga pero scikit-learn advierte explícitamente de
`InconsistentVersionWarning` — la estructura interna de `TfidfVectorizer` y
`MultinomialNB` puede diferir entre versiones mayores, y eso puede
traducirse en predicciones sutilmente distintas a las que ustedes midieron
al entrenar. Lo verificamos cargando con warnings promovidos a error: cero
warnings con 1.6.1. Si reentrenan con otra versión, avísennos para
actualizar el pin en el mismo commit — está documentado en
`backend/models/README.md`."

#### Data Science: "¿Qué pasa si entregamos el modelo en un formato distinto (por ejemplo, con el vectorizador aparte)?"

**Responder:** "Ya está cubierto y probado. `AdaptadorModelo` en
`ml/adaptador.py` acepta un `Pipeline` completo, un `dict` con claves como
`{"modelo": ..., "vectorizador": ...}` (en español o inglés), o una tupla en
cualquier orden — lo detecta por duck typing, no por convención estricta de
nombres. Hay 4 pruebas parametrizadas (`test_artefacto_con_vectorizador_separado`)
que verifican las 4 variantes."

#### QA: "¿Cómo se prueba algo que depende de un archivo binario externo (el .pkl)?"

**Responder:** "De dos formas complementarias. La mayoría de las pruebas de
integración ML (`CP-90` a `CP-105`) entrenan un `Pipeline` real de
scikit-learn *al vuelo*, en memoria, con un corpus mínimo — así no dependen
de que el `.pkl` de producción exista, y corren en cualquier máquina o CI.
Aparte, hay un segundo grupo (`CP-110` a `CP-113`) que sí carga el
`clasificador_cursos.pkl` real del repositorio — pero usa `pytest.skip()` si
el archivo no está presente, en vez de fallar. La suite nunca es roja por
un archivo ausente, pero si el archivo *está* y no se activa, eso sí falla
la prueba — es un problema real que hay que ver."

#### QA: "¿Qué cobertura de pruebas tiene el mecanismo de fallback específicamente?"

**Responder:** "Seis casos dedicados solo a resiliencia (`CP-100` a
`CP-105`): artefacto corrupto, objeto sin método `predict`, ruta
inexistente, fallo de inferencia en caliente (el modelo carga bien pero
falla en una predicción puntual), y la sonda de carga rechazando un modelo
entrenado sin su vectorizador. Cada una simula un modo de fallo real y
verifica que la API sigue respondiendo 200, nunca 500."

#### Cualquiera: "¿Esto es sobre-ingeniería para un MVP de hackathon?"

**Responder con honestidad, no a la defensiva:** "Es una pregunta justa. La
respuesta corta es: se aplicó donde dolía de verdad — un archivo de 929
líneas con seis razones de cambio distintas — y se dejó fuera donde no
aportaba: no hay un framework de inyección de dependencias de terceros, no
hay capas de abstracción para cosas que no van a cambiar (como el formato
JSON de respuesta). El criterio fue: ¿esto se va a tener que modificar en
las próximas 2 semanas? Si sí (el motor de IA, la base de datos), se
desacopla. Si no, se deja simple."

---

<div align="center">

**Ver también:** [`README.md`](../README.md) · [`docs/QA_TESTING_GUIDE.md`](QA_TESTING_GUIDE.md) · [`backend/models/README.md`](../backend/models/README.md)

</div>
