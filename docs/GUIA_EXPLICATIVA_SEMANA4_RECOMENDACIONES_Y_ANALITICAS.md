# 🎓 Guía Explicativa — Semana 4: Recomendaciones y Analíticas

**AthenIA** · Hackathon ONE Alura + Oracle / No Country · Generación 9

> Clase máster para el equipo Full Stack. Todo lo que aquí se explica **está en
> el código y verificado**: 120 pruebas en verde, 96.72% de cobertura. Los
> números de los ejemplos no son inventados — salen de ejecutar las funciones
> reales del repositorio.

---

## Índice

1. [El algoritmo de recomendación: Jaccard paso a paso](#1-el-algoritmo-de-recomendación-jaccard-paso-a-paso)
2. [Las analíticas: de FastAPI a React sin librerías pesadas](#2-las-analíticas-de-fastapi-a-react-sin-librerías-pesadas)
3. [El historial: localStorage + debounce de 1.2 s](#3-el-historial-localstorage--debounce-de-12-s)
4. [Guion rápido para la reunión y el pitch](#4-guion-rápido-para-la-reunión-y-el-pitch)

---

## 1. El algoritmo de recomendación: Jaccard paso a paso

### 1.1 El problema

Un usuario abre "Docker para Principiantes". ¿Qué otro contenido de su
biblioteca le mostramos como relacionado?

Podríamos usar embeddings o un LLM, pero para un catálogo de cientos de cursos
sería usar un cañón para matar una mosca: caro, lento y difícil de explicar
ante un jurado. Ya tenemos algo mejor y gratis: **el modelo de IA ya extrajo
las palabras clave de cada contenido**. Solo hay que comparar esos conjuntos.

### 1.2 La intuición

Dos cursos se parecen si **hablan de las mismas tecnologías**.

```
Curso A: {Docker, Kubernetes, Linux}
Curso B: {Docker, Kubernetes, Monitoreo}
                ↑         ↑
           comparten 2 tecnologías → se parecen bastante
```

Pero "cuántas comparten" a secas engaña. Mira este caso:

```
Curso A: {Docker, Linux}                          → comparte 1 con C
Curso C: {Docker, Java, SQL, React, AWS, Python}  → comparte 1 con A
```

Ambos comparten exactamente 1 tecnología. Pero el Curso C habla de **seis
cosas distintas**: que mencione Docker de pasada no lo hace un curso de Docker.
Si contáramos coincidencias brutas, los cursos con muchas palabras clave
parecerían relacionados con todo el catálogo.

**La solución: normalizar por el tamaño de la unión.** Eso es Jaccard.

### 1.3 La matemática

$$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

En castellano: **lo que comparten, dividido entre todo lo que mencionan entre
los dos.**

| | Fórmula | Resultado |
|---|---|---|
| Conjuntos idénticos | `2/2` | `1.0` — máxima similitud |
| Sin nada en común | `0/5` | `0.0` — nada que ver |
| Comparten 1 de 2 | `1/3` | `0.33` |
| Comparten 1 de 6 | `1/7` | `0.14` ← penalizado por ser más disperso |

El denominador es la **unión**, no la suma: si A tiene 3 y B tiene 3 y
comparten 2, la unión es 4 (no 6), porque los 2 compartidos se cuentan una vez.

### 1.4 Por qué no basta con las palabras clave

Imagina dos cursos de Ciberseguridad donde el modelo extrajo pocas palabras
clave y ninguna coincide. Jaccard daría `0.0` y no se recomendarían entre sí,
aunque el modelo de IA los clasificó en **la misma categoría**.

Por eso el puntaje combina dos señales:

$$\text{puntaje} = 0.75 \times J(\text{palabras}) + 0.25 \times \text{misma categoría}$$

**Por qué 75/25 y no 50/50:**

- Las palabras clave son **específicas**: compartir "Kubernetes" dice mucho.
- La categoría es **amplia**: "Cloud Computing y DevOps" agrupa decenas de
  cursos. Si pesara demasiado, toda la categoría se recomendaría entre sí y
  las sugerencias serían inútiles.

Los pesos viven en `backend/app/domain/similitud.py` como constantes con
nombre, no como números mágicos dentro de una fórmula:

```python
PESO_PALABRAS_CLAVE = 0.75
PESO_CATEGORIA = 0.25
UMBRAL_MINIMO_RELEVANCIA = 0.10   # por debajo, es ruido: no se muestra
```

### 1.5 Ejemplo trabajado con números reales

Referencia: **`{Docker, Kubernetes, Linux}`** en *Cloud Computing y DevOps*.

Esta tabla es la salida literal de ejecutar las funciones del repositorio:

| Candidato | ∩ | ∪ | Jaccard | Misma cat. | **Puntaje** | ¿Se muestra? |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Kubernetes en Producción | 2 | 4 | 0.5000 | 1 | **0.6250** | ✅ |
| Nginx y proxies | 1 | 4 | 0.2500 | 1 | **0.4375** | ✅ |
| Machine Learning con Python | 0 | 6 | 0.0000 | 0 | **0.0000** | ❌ |

Verificación del primero, a mano:

```
Jaccard  = 2 / 4               = 0.5
puntaje  = 0.75 × 0.5  +  0.25 × 1
         = 0.375       +  0.25
         = 0.625                          ✔ coincide
```

Y el segundo, que **solo comparte "Linux"** pero está en la misma categoría:

```
puntaje  = 0.75 × 0.25 +  0.25 × 1  =  0.1875 + 0.25  =  0.4375
```

Fíjate en el tercero: `0.0` queda por debajo del umbral `0.10`, así que **ni
siquiera aparece** en la respuesta. Un curso de Machine Learning no se cuela
entre las recomendaciones de un curso de Docker.

### 1.6 Del concepto al código

**`domain/similitud.py`** — matemática pura, sin base de datos ni HTTP:

```python
def jaccard(primero, segundo) -> float:
    conjunto_a = _conjunto_normalizado(primero)
    conjunto_b = _conjunto_normalizado(segundo)

    if not conjunto_a or not conjunto_b:
        return 0.0                                  # sin keywords → 0, no crash

    return len(conjunto_a & conjunto_b) / len(conjunto_a | conjunto_b)
```

> **Detalle que evita un bug silencioso:** `_conjunto_normalizado` pasa todo
> por `normalizar()` (minúsculas, sin acentos). Sin eso, `"Spring Boot"` y
> `"spring boot"` contarían como tecnologías distintas y dos cursos idénticos
> puntuarían `0.0`. Lo cubre la prueba **CP-202**.

**`recomendador.py`** — recorre los candidatos y ordena:

```python
recomendaciones.sort(key=lambda r: (-r["puntaje"], -r["id"]))
```

> **Por qué el `-id` como segundo criterio:** si dos contenidos empatan en
> puntaje, sin un desempate estable el orden podría cambiar entre llamadas y
> las aserciones de QA fallarían de forma intermitente. Con `-id`, a igualdad
> gana el más reciente, siempre igual.

### 1.7 La pieza que hace la diferencia en la demo: la evidencia

Cualquiera puede devolver `{"puntaje": 0.625}`. Nosotros devolvemos también
**por qué**:

```json
{
  "titulo": "Kubernetes en Produccion",
  "puntaje": 0.625,
  "palabras_compartidas": ["Docker", "Kubernetes"]
}
```

La UI lo pinta como *"Comparten: Docker · Kubernetes"*. El usuario entiende la
recomendación sin saber qué es Jaccard, y el jurado ve un sistema explicable en
vez de una caja negra.

### 1.8 Arquitectura: cómo se cambia el motor sin tocar nada más

El endpoint no conoce `RecomendadorPorKeywords`. Depende del `Protocol`
`MotorRecomendaciones`:

```python
def recomendaciones_de_contenido(
    contenido_id: int,
    recomendador: MotorRecomendaciones = Depends(get_recomendador),  # ← abstracción
):
```

Migrar a embeddings en la Semana 5 = escribir una clase con el mismo método
`recomendar()` y cambiar **una línea** en `dependencies.get_recomendador()`.
Lo demuestra la prueba **CP-221**, que sustituye el motor en caliente con
`dependency_overrides` y verifica que el endpoint responde con la nueva
estrategia.

---

## 2. Las analíticas: de FastAPI a React sin librerías pesadas

### 2.1 El recorrido completo

```
┌───────────────────────────────────────────────────────────────────────┐
│ 1. REPOSITORIO — repositories/memoria.py                              │
│    repositorio.listar() → [ {categoria, probabilidad, origen, ...} ]  │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 2. AGREGACIÓN — services.calcular_analiticas(items, motor)            │
│    Counter() sobre categorías, orígenes, franjas de confianza y días  │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 3. CONTRATO — schemas.AnaliticasOutput (Pydantic)                     │
│    Valida rangos: porcentaje 0-100, confianza 0-1, cantidades >= 0    │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼  GET /analiticas  (JSON)
┌───────────────────────────────────────────────────────────────────────┐
│ 4. HOOK — useAnaliticas()                                             │
│    AbortController + estados {analiticas, cargando, error}            │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 5. VISTA — AnalyticsPanel.jsx                                         │
│    Barras con CSS width % · Línea con <svg><polyline>                 │
└───────────────────────────────────────────────────────────────────────┘
```

### 2.2 El truco: el backend entrega datos "listos para pintar"

La decisión clave es **dónde se calcula el porcentaje**. Lo hace Python, no
React:

```python
def _segmentos(conteo: Counter, total: int) -> List[dict]:
    return [
        {
            "etiqueta": etiqueta,
            "cantidad": cantidad,
            "porcentaje": round(cantidad / total * 100, 1),
        }
        for etiqueta, cantidad in conteo.most_common()
    ]
```

`.most_common()` ya devuelve ordenado de mayor a menor. Así el frontend
**no ordena, no calcula, no transforma** — solo pinta. Menos JavaScript, menos
sitios donde equivocarse, y la misma respuesta sirve para cualquier cliente
futuro (una app móvil, un informe en PDF).

### 2.3 Un detalle de UX que parece trivial y no lo es

Las franjas de confianza se devuelven **siempre en el mismo orden**, aunque
alguna esté en cero:

```python
FRANJAS_CONFIANZA = (
    ("Alta (≥75%)",    0.75),
    ("Media (50-74%)", 0.50),
    ("Baja (<50%)",    0.0),
)
```

Si las ordenáramos por cantidad como las categorías, la leyenda cambiaría de
posición cada vez que llegan datos nuevos. El usuario que mira el dashboard dos
veces vería las barras saltando de sitio. Lo fija la prueba **CP-243**.

> **Por qué esta métrica importa para el negocio:** es la única del panel que
> responde *"¿confío en lo que dice la IA?"*. Si el 60% del contenido cae en
> "Baja", el equipo de Data Science sabe que toca reentrenar. No es un gráfico
> decorativo.

### 2.4 Gráficos sin Chart.js: barras

Una barra es un `div` con `width` en porcentaje. No hace falta nada más:

```jsx
<div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-800">
  <div
    className="h-full rounded-full transition-[width] duration-700"
    style={{
      width: `${(segmento.cantidad / maximo) * 100}%`,
      backgroundColor: colorDe(segmento.etiqueta),
    }}
  />
</div>
```

Se normaliza contra `maximo` (el segmento más grande), no contra el total: así
la barra mayor siempre llena el ancho y las diferencias se aprecian aunque
todos los valores sean pequeños.

### 2.5 Gráficos sin Chart.js: la línea de actividad

Un `<polyline>` de SVG recibe pares `x,y`. Solo hay que convertir los datos:

```jsx
const coordenadas = puntos.map((punto, indice) => {
  const x = (indice / (puntos.length - 1)) * ANCHO      // reparte horizontal
  const y = ALTO - (punto.cantidad / maximo) * ALTO     // invierte vertical
  return `${x},${y}`
})
```

> **El `ALTO -` es obligatorio:** en SVG el eje Y crece **hacia abajo**
> (`y=0` es el borde superior). Sin restar, el gráfico saldría boca abajo.

Dos casos borde que el componente cubre:

| Situación | Problema | Solución en el código |
|---|---|---|
| `puntos.length === 1` | `(indice / 0)` → `NaN` | Se muestra el dato como texto, sin gráfico |
| `puntos.length === 0` | No hay nada que dibujar | Mensaje "Aún no hay actividad registrada" |

**Accesibilidad:** un SVG es invisible para un lector de pantalla, así que se
describe la serie completa en texto:

```jsx
role="img"
aria-label={`Actividad diaria: ${puntos.map(p => `${p.fecha}, ${p.cantidad} análisis`).join('; ')}`}
```

### 2.6 El coste real de la decisión

| Enfoque | Peso añadido al bundle |
|---|---|
| Chart.js | ~200 KB |
| Recharts | ~500 KB (arrastra D3) |
| **SVG + CSS (lo nuestro)** | **0 KB** |

El bundle total quedó en **340 KB (108 KB gzip)**. Con Recharts habría más que
duplicado — y en la demo sobre OCI, cada KB es tiempo de carga ante el jurado.

---

## 3. El historial: localStorage + debounce de 1.2 s

### 3.1 El problema del debounce

La búsqueda filtra **mientras escribes**. Si guardáramos cada pulsación:

```
Usuario teclea "docker"
  → "d", "do", "doc", "dock", "docke", "docker"
  → 6 entradas en el historial, 5 de ellas basura
```

Con solo 8 huecos disponibles, tres búsquedas dejarían el historial inservible.

### 3.2 La solución: esperar a que la escritura "repose"

```jsx
const MS_ANTES_DE_REGISTRAR = 1200

useEffect(() => {
  const termino = consulta.trim()
  if (!termino || cargando || total === 0) return undefined

  const temporizador = setTimeout(() => registrar(termino), MS_ANTES_DE_REGISTRAR)
  return () => clearTimeout(temporizador)     // ← la clave
}, [consulta, cargando, total, registrar])
```

**Cómo funciona el `return () => clearTimeout(...)`:** cada vez que `consulta`
cambia, React ejecuta primero la función de limpieza del efecto anterior. Eso
**cancela el temporizador pendiente** antes de programar uno nuevo. El registro
solo ocurre si pasan 1.2 s completos sin teclear.

```
t=0.0s  "d"       → programa timer A
t=0.2s  "do"      → cancela A, programa B
t=0.4s  "doc"     → cancela B, programa C
...
t=1.0s  "docker"  → cancela E, programa F
t=2.2s            → F dispara ✅  guarda "docker"   (1 sola entrada)
```

### 3.3 Las dos condiciones extra

Fíjate en `if (!termino || cargando || total === 0)`:

- **`cargando`**: no registrar mientras la petición está en vuelo — `total`
  todavía tiene el valor de la búsqueda anterior.
- **`total === 0`**: **solo se guardan búsquedas que encontraron algo.** Un
  historial lleno de términos que no dieron resultados no le sirve a nadie.

Esa segunda condición es una decisión de producto, no técnica, y es la que
convierte la función en algo útil.

### 3.4 Persistencia defensiva

`localStorage` puede fallar de formas que rompen la página si no se prevén:

```js
function leerDeStorage() {
  try {
    const crudo = window.localStorage.getItem(CLAVE)
    if (!crudo) return []

    const datos = JSON.parse(crudo)
    if (!Array.isArray(datos)) return []          // guardado con otro formato

    return datos
      .filter((e) => e && typeof e.termino === 'string' && e.termino.trim())
      .slice(0, MAXIMO)
  } catch {
    return []        // JSON corrupto, o Safari en modo privado (lanza al leer)
  }
}
```

Tres defensas, tres fallos reales cubiertos:

| Defensa | Escenario que evita |
|---|---|
| `try/catch` | Safari privado lanza al tocar `localStorage`; JSON corrupto |
| `Array.isArray` | Una versión anterior guardó un objeto en vez de un array |
| `.filter(...)` | Alguien editó el storage a mano desde DevTools |

Sin ellas, un `localStorage` manipulado tumbaría toda la vista de búsqueda.
**Degradar a "sin historial" siempre es mejor que una pantalla en blanco.**

### 3.5 Detalle: mover al frente en vez de duplicar

```js
const sinDuplicado = previas.filter(
  (e) => e.termino.toLowerCase() !== limpio.toLowerCase(),
)
return [{ termino: limpio, momento: Date.now() }, ...sinDuplicado].slice(0, MAXIMO)
```

Si buscas "docker" por tercera vez, no aparece tres veces: **sube al primer
puesto**. El historial refleja uso reciente, que es lo que el usuario espera.

### 3.6 Un detalle de HTML que sí importa

Cada chip tiene dos acciones: *reejecutar la búsqueda* y *eliminarla*. La
tentación es anidar el botón de borrar dentro del chip clicable — pero
**`<button>` dentro de `<button>` es HTML inválido** y los navegadores lo
"reparan" de formas impredecibles. Por eso son hermanos dentro de un `<span>`:

```jsx
<span className="inline-flex items-center overflow-hidden rounded-lg border ...">
  <button onClick={() => onSeleccionar(entrada.termino)}>{entrada.termino}</button>
  <button onClick={() => onEliminar(entrada.termino)} aria-label={`Quitar "${entrada.termino}"`}>
    <X size={12} />
  </button>
</span>
```

---

## 4. Guion rápido para la reunión y el pitch

### 4.1 Versión 60 segundos (pitch)

> «En la Semana 4 AthenIA dejó de ser un clasificador para convertirse en un
> **asistente de conocimiento**.
>
> Antes te decía *"esto es DevOps, 76% de confianza"*. Ahora además te dice
> **"y esto otro te interesa, porque ambos hablan de Docker y Kubernetes"**.
>
> Lo hace con similitud de Jaccard sobre las palabras clave que el propio
> modelo extrajo — sin llamadas externas, sin coste por token, en
> milisegundos. Y siempre muestra **por qué** recomienda algo: nada de caja
> negra.
>
> Añadimos también un panel de analíticas que responde la pregunta que importa:
> *¿cuánto puedo fiarme de esta IA?* Clasifica cada resultado en confianza
> Alta, Media o Baja, y eso le dice a Data Science cuándo toca reentrenar.
>
> Todo con **120 pruebas automatizadas y 96% de cobertura**, y sin sumar ni un
> KB de librerías de gráficos al frontend.»

### 4.2 Demo en vivo — 3 minutos, 4 pasos

| # | Acción | Qué decir |
|---|---|---|
| 1 | Dashboard → señalar "Confianza del modelo" | *"Esta métrica no la teníamos: nos dice cuánto contenido clasificó la IA con poca certeza. Es el termómetro del modelo."* |
| 2 | Buscar → escribir `docker` → esperar 2 s | *"Fíjense abajo: la búsqueda se guardó sola en el historial. Con debounce, para no guardar cada letra."* |
| 3 | Clic en "Ver detalle" → panel lateral | *"Aquí está lo nuevo: contenido relacionado. Y miren la línea de abajo — **Comparten: Docker** — el sistema explica por qué."* |
| 4 | Clic en una recomendación | *"Y se puede navegar entre contenidos relacionados sin salir del panel."* |

> **Ensaya el paso 2 una vez.** Hay que esperar 1.2 s tras dejar de teclear
> para que el chip aparezca; si sigues hablando y no esperas, no se ve.

### 4.3 Las tres preguntas que van a hacer

**«¿Por qué Jaccard y no embeddings o un LLM?»**

> Por coste, latencia y explicabilidad. Los embeddings requieren un servicio
> externo o un modelo grande en memoria; un LLM cobra por token y añade
> segundos. Jaccard corre en microsegundos sobre datos que ya teníamos, y
> podemos mostrarle al usuario exactamente qué palabras dispararon la
> recomendación. Dicho eso, **la arquitectura ya está lista para cambiar**: el
> endpoint depende de un `Protocol`, así que migrar a embeddings en la Semana 5
> es una clase nueva y una línea. Tenemos una prueba que lo demuestra.

**«¿Por qué 75/25 y no otra proporción?»**

> Las palabras clave son específicas; la categoría es amplia. Si la categoría
> pesara más, todos los cursos de una misma área se recomendarían entre sí y
> las sugerencias perderían valor. Con 25% aporta lo justo para relacionar
> contenido cuando el modelo extrajo pocas palabras clave, sin dominar el
> resultado. Los pesos son constantes con nombre en `domain/similitud.py`:
> ajustarlos es cambiar un número, no reescribir el algoritmo.

**«¿Esto escala?»**

> Hoy es O(n) sobre el historial, con un tope de 500 items en memoria —
> trivial. Con decenas de miles habría que indexar, pero eso llega junto con la
> migración a Oracle Database, y el `Protocol` `RepositorioContenidos` ya
> aísla ese cambio. Está documentado como decisión consciente en el propio
> código, no es un descuido.

### 4.4 Chuleta de números

| Dato | Valor |
|---|---|
| Pruebas totales | **120** (84 → 120 en la Semana 4) |
| Cobertura | **96.72%** (umbral CI: 85%) |
| Pruebas nuevas | 36 (CP-200…CP-222 y CP-230…CP-252) |
| Pesos del recomendador | 75% palabras clave · 25% categoría |
| Umbral de relevancia | 0.10 |
| Debounce del historial | 1200 ms · máximo 8 entradas |
| Peso de librerías de gráficos | **0 KB** |
| Bundle final | 340 KB (108 KB gzip) |

---

<div align="center">

**Ver también:**
[`README.md`](../README.md) ·
[`QA_TESTING_GUIDE.md`](QA_TESTING_GUIDE.md) ·
[`GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md`](GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md)

</div>
