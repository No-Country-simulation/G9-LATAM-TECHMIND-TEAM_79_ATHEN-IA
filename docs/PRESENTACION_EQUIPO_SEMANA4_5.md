# 🎤 Presentación de Equipo — Semanas 4 y 5

**AthenIA** · Hackathon ONE Alura + Oracle / No Country · Generación 9
**Demo Day — 5 diapositivas, ~5 minutos**

> Guion completo para presentar al equipo y al jurado. Cada diapositiva trae
> **qué poner en la slide**, **qué decir en voz alta** y **qué responder** si
> preguntan. Todos los datos están verificados contra el repositorio.

---

## ⏱️ Reparto del tiempo

| Diapositiva | Tiempo | Quién |
|---|:---:|---|
| 1 · Portada y propuesta de valor | 45 s | PM / Full Stack |
| 2 · Arquitectura Full Stack + ML | 60 s | Arquitecto / Backend |
| 3 · Motor de recomendaciones | 75 s | Full Stack |
| 4 · Analíticas y calidad | 60 s | QA |
| 5 · Despliegue en OCI | 60 s | DevOps / Backend |
| **Demo en vivo** | **60 s** | quien maneje la pantalla |

> **Antes de empezar:** tener `npm run dev` corriendo, el navegador en
> `localhost:5173` y una terminal libre. Confirmar que el Header muestra el
> badge morado **"Modelo IA"** (no "Reglas").

---

## 🟣 Diapositiva 1 — Portada y Propuesta de Valor

### Contenido de la slide

> # 🏛️ AthenIA
> **Organización Inteligente del Conocimiento Técnico**
>
> - **El problema:** el conocimiento técnico de un equipo vive disperso — cursos,
>   artículos, documentación. Nadie sabe qué hay ni cómo se relaciona.
> - **La solución:** pegas un texto técnico y AthenIA lo **clasifica**, extrae sus
>   **tecnologías** y te dice **qué más de tu biblioteca se relaciona**.
> - **El resultado:** una biblioteca que se organiza sola y explica sus conexiones.
>
> `Hackathon ONE Alura + Oracle · Generación 9`

### Qué decir

> «AthenIA nace de un problema que todos tenemos: el conocimiento técnico está
> disperso y nadie sabe qué hay dentro.
>
> Tú pegas el temario de un curso o un artículo. AthenIA te dice a qué área
> pertenece, con qué nivel de confianza, qué tecnologías menciona, y —lo más
> importante— **qué otro contenido de tu biblioteca se relaciona con ese, y por
> qué**.
>
> No es un buscador. Es una biblioteca que entiende lo que guarda.»

### Preguntas probables

**«¿En qué se diferencia de una simple búsqueda por etiquetas?»**
> Las etiquetas hay que ponerlas a mano y siempre quedan incompletas. AthenIA
> las extrae sola del texto y, además, **calcula relaciones**: no solo te dice
> "esto es DevOps", te dice "esto se parece a aquello porque ambos hablan de
> Docker y Kubernetes". Eso una etiqueta no lo hace.

**«¿Quién es el usuario final?»**
> Un estudiante o un equipo técnico que acumula material de formación. El caso
> de uso directo del Hackathon: alguien de ONE con decenas de cursos de Alura
> que quiere ver su ruta de aprendizaje organizada.

---

## 🟣 Diapositiva 2 — Arquitectura Full Stack e Integración ML

### Contenido de la slide

> ## Arquitectura en capas, con las dependencias apuntando al dominio
>
> ```
>  React 19 + Vite            FastAPI                     Modelo ML
>  ───────────────           ─────────                   ──────────
>  pages/                    routers/     ← HTTP          clasificador_cursos.pkl
>  components/       ──►     services/    ← casos de uso  Pipeline:
>  hooks/                    domain/      ← contratos       TfidfVectorizer
>  services/api.js           ml/ repos/   ← implementación  → MultinomialNB
> ```
>
> | Capa | Tecnología |
> |---|---|
> | Frontend | React 19 · Vite 8 · Tailwind v4 · React Router 7 |
> | Backend | Python 3.13 · FastAPI · Pydantic v2 · Uvicorn |
> | IA | Scikit-Learn 1.6.1 · TF-IDF + MultinomialNB |
>
> **Regla de oro:** las rutas dependen de `Protocol`, nunca de implementaciones.

### Qué decir

> «El backend está en capas, y la regla que las ordena es que **todas las
> dependencias apuntan hacia el dominio**.
>
> El dominio define *contratos*: qué es un clasificador, qué es un repositorio.
> Las implementaciones concretas —el modelo de scikit-learn, el historial en
> memoria— cumplen esos contratos. Y las rutas HTTP dependen del contrato,
> nunca de la implementación.
>
> ¿Por qué importa? Porque el motor de IA **va a cambiar**. Hoy es TF-IDF con
> Naive Bayes. Mañana pueden ser embeddings. Con esta arquitectura, ese cambio
> es una clase nueva y una línea — no tocar las rutas ni los tests.
>
> El modelo en sí es un `Pipeline` de scikit-learn: TF-IDF convierte el texto en
> números pesando las palabras distintivas, y Naive Bayes calcula la
> probabilidad de cada categoría. Corre en milisegundos, sin GPU y sin llamadas
> externas.»

### Preguntas probables

**«¿Por qué no usaron un LLM?»**
> Por coste, latencia y explicabilidad. Un LLM cobra por token, añade segundos
> de latencia y es una caja negra difícil de justificar. TF-IDF + Naive Bayes
> corre en milisegundos, es gratis y podemos inspeccionar exactamente qué
> palabras pesaron. Para clasificar en 5 categorías con un dataset de cursos, es
> la herramienta proporcionada al problema.

**«¿Qué pasa si el modelo falla o no está?»**
> Hay un fallback en 4 etapas —lo detallo en la diapositiva 5— y una prueba que
> lo verifica. La API nunca devuelve 500 por culpa del modelo.

**«¿Esta arquitectura no es sobreingeniería para un MVP?»**
> Se aplicó donde dolía: un archivo de 929 líneas con seis responsabilidades
> distintas. Bajó a 256 y las demás viven en módulos con una sola razón de
> cambio. Lo que **no** hicimos fue meter un framework de inyección de
> dependencias ni abstraer cosas que no van a cambiar. El criterio fue: ¿esto se
> modifica en las próximas dos semanas? Si sí, se desacopla.

---

## 🟣 Diapositiva 3 — Motor de Recomendaciones (Índice de Jaccard)

### Contenido de la slide

> ## ¿Qué contenido se parece a este?
>
> ### Índice de Jaccard: lo que comparten ÷ todo lo que mencionan
>
> $$J(A,B) = \frac{|A \cap B|}{|A \cup B|}$$
>
> $$\text{puntaje} = \mathbf{0.75} \times J(\text{palabras clave}) + \mathbf{0.25} \times \text{misma categoría}$$
>
> **Ejemplo real** — referencia: `{Docker, Kubernetes, Linux}` · *Cloud Computing y DevOps*
>
> | Candidato | ∩ | ∪ | Jaccard | Misma cat. | **Puntaje** |
> |---|:--:|:--:|:--:|:--:|:--:|
> | Kubernetes en Producción | 2 | 4 | 0.50 | ✔ | **0.625** |
> | Nginx y proxies | 1 | 4 | 0.25 | ✔ | **0.4375** |
> | Machine Learning con Python | 0 | 6 | 0.00 | ✘ | **0.000** ❌ descartado |
>
> ### 🔑 La clave: **explicamos la recomendación**
> > *"Comparten: **Docker** · **Kubernetes**"*

### Qué decir

> «Para recomendar no llamamos a ningún servicio externo: **reutilizamos las
> palabras clave que el propio modelo ya extrajo**.
>
> Usamos el índice de Jaccard: lo que dos contenidos comparten, dividido entre
> todo lo que mencionan entre los dos. ¿Por qué dividir? Porque si solo
> contáramos coincidencias, un curso que menciona diez tecnologías parecería
> relacionado con todo el catálogo. Jaccard normaliza por tamaño.
>
> A eso le sumamos un 25% por coincidir de categoría. Poco peso, a propósito: si
> pesara más, toda una categoría se recomendaría entre sí y las sugerencias
> perderían valor.
>
> Miren el ejemplo: el curso de Kubernetes saca 0.625 porque comparte dos
> tecnologías. El de Nginx saca 0.4375 aunque solo comparte "Linux", porque está
> en la misma categoría. Y el de Machine Learning saca cero, así que **ni
> aparece** — hay un umbral por debajo del cual es ruido.
>
> Pero lo que de verdad lo diferencia es esto: **no mostramos un número
> opaco**. Decimos *"Comparten: Docker, Kubernetes"*. El usuario entiende la
> recomendación sin saber qué es Jaccard.»

### Preguntas probables

**«¿Por qué 75/25 y no otra proporción?»**
> Las palabras clave son específicas —compartir "Kubernetes" dice mucho—; la
> categoría es amplia y agrupa decenas de cursos. El 25% aporta lo justo para
> relacionar contenido cuando el modelo extrajo pocas palabras clave, sin
> dominar el resultado. Son constantes con nombre en `domain/similitud.py`:
> ajustarlas es cambiar un número, no reescribir el algoritmo.

**«¿Escala esto con miles de contenidos?»**
> Hoy es O(n) sobre un historial con tope de 500 ítems: trivial. Con decenas de
> miles habría que indexar, y eso llega junto con la migración a Oracle
> Database. Está documentado como decisión consciente en el código, no es un
> descuido.

**«¿Y si dos contenidos empatan en puntaje?»**
> Hay un desempate estable por ID descendente: a igualdad gana el más reciente.
> Sin eso el orden podría cambiar entre llamadas y las pruebas de QA fallarían
> de forma intermitente.

**«¿Podrían cambiar a embeddings?»**
> Sí, y está preparado. El endpoint depende del `Protocol`
> `MotorRecomendaciones`, no de la implementación. Cambiarlo es una clase nueva
> y una línea en `dependencies.py`. Tenemos una prueba (CP-221) que sustituye el
> motor en caliente y verifica que el endpoint responde con la nueva estrategia.

---

## 🟣 Diapositiva 4 — Dashboard de Analíticas y Calidad

### Contenido de la slide

> ## Analíticas que responden preguntas de negocio
>
> | Panel | La pregunta que responde |
> |---|---|
> | Distribución por categoría | ¿Qué áreas domina mi biblioteca? |
> | **Confianza del modelo** | **¿Cuánto puedo fiarme de esta IA?** |
> | Distribución por origen | ¿De dónde viene mi contenido? |
> | Actividad por día | ¿Cuánto estoy catalogando? |
>
> ### Calidad verificada
>
> | Métrica | Valor |
> |---|---|
> | Pruebas automatizadas | **120** ✅ |
> | Cobertura | **96.72%** (umbral CI: 85%) |
> | Tiempo de la suite | 2.8 s |
> | Librerías de gráficos | **0 KB** |
>
> `CI: GitHub Actions · pytest + cobertura en cada push`

### Qué decir

> «El dashboard no son gráficos decorativos. Cada panel responde una pregunta.
>
> El más importante es **Confianza del modelo**: agrupa el contenido en certeza
> Alta, Media o Baja. Si el 60% cae en Baja, Data Science sabe que toca
> reentrenar. Es la única métrica que responde *"¿me puedo fiar de esta IA?"*.
>
> Sobre calidad: 120 pruebas, 96.72% de cobertura, y el CI **falla el build** si
> baja del 85%. No es un número que miramos de vez en cuando, es una puerta.
>
> Y un detalle del que estamos orgullosos: **cero kilobytes de librerías de
> gráficos**. Las barras son divs con `width` en porcentaje y la línea es un
> `polyline` de SVG. Chart.js habría sumado 200 KB; Recharts, 500. En una demo
> sobre OCI, cada KB es tiempo de carga.»

### Preguntas probables

**«96% de cobertura, ¿pero prueban lo que importa?»**
> La cobertura sola no dice nada, de acuerdo. Por eso las pruebas están
> catalogadas por caso: contrato del Hackathon, validaciones, integración con el
> modelo real, resiliencia del fallback... Hay incluso **dos pruebas que
> verifican la arquitectura**: una comprueba que se puede añadir un motor nuevo
> sin tocar código existente, y otra que las rutas dependen de abstracciones.
> Están en `docs/QA_TESTING_GUIDE.md` con su identificador.

**«¿Cómo prueban algo que depende de un archivo binario (.pkl)?»**
> De dos formas. La mayoría de pruebas ML **entrena un Pipeline real al vuelo**,
> en memoria: no dependen del artefacto de producción y corren en cualquier
> máquina. Aparte hay un grupo que carga el `.pkl` real, pero hace `skip` si no
> está presente. La suite nunca es roja por un archivo ausente — pero si el
> archivo está y no carga, eso sí falla.

**«¿Qué pasa con el frontend, tiene tests?»**
> No automatizados: priorizamos la cobertura del backend, donde está la lógica
> de negocio. El frontend se valida con un checklist manual de 16 casos
> documentado en la guía de QA, y el build de producción corre en cada cambio.
> Es una deuda consciente, no un olvido.

---

## 🟣 Diapositiva 5 — Estrategia de Despliegue en OCI

### Contenido de la slide

> ## Docker Compose · Nginx · Resiliencia
>
> ```
>   Navegador
>       │  HTTPS
>       ▼
>  ┌─────────────────────┐         ┌──────────────────────┐
>  │  athenia-frontend   │  /api/  │   athenia-backend    │
>  │  Nginx :80          │ ──────► │   FastAPI :8000      │
>  │  · SPA routing      │  red    │   · modelo .pkl      │
>  │  · gzip + cache     │ interna │   · usuario no-root  │
>  └─────────────────────┘         └──────────────────────┘
>              docker compose up --build
> ```
>
> ### Fallback en 4 etapas — la demo no se cae
>
> | # | Etapa | Si falla |
> |---|---|---|
> | 1 | Localizar el `.pkl` | → reglas |
> | 2 | Deserializar (joblib → pickle) | → reglas |
> | 3 | Adaptar la estructura | → reglas |
> | 4 | **Sonda: predicción de prueba** | → reglas |
>
> **+ captura de errores en caliente** · `GET /salud` reporta qué motor responde

### Qué decir

> «El despliegue son dos contenedores orquestados con Docker Compose.
>
> Nginx sirve el frontend y **proxea `/api` al backend por la red interna**. Eso
> resuelve dos problemas de golpe: el navegador nunca hace peticiones
> cross-origin —así que no hay CORS que pelear— y no hay contenido mixto, que
> es lo que rompe cuando sirves HTTPS y llamas a un backend por HTTP.
>
> Y lo que más nos importa para hoy: **la demo no se puede caer por el modelo**.
> Hay cuatro etapas de verificación antes de confiar en él. La cuarta es la
> clave: ejecutamos una **predicción de prueba** antes de exponerlo. Un modelo
> que carga en memoria pero revienta al predecir se descarta ahí, no delante de
> ustedes.
>
> Si cualquier etapa falla, cae a un clasificador por reglas determinista y la
> API sigue respondiendo. `GET /salud` dice en todo momento qué motor está
> contestando, y el badge del header lo muestra en pantalla.»

### Demostración opcional (si sobra tiempo — 30 s)

> Renombrar `backend/models/clasificador_cursos.pkl`, reiniciar el backend y
> mostrar que `/salud` pasa a `clasificador_reglas` **y la app sigue
> funcionando**. Restaurar después.
>
> ⚠️ Ensayarlo antes una vez: requiere reiniciar el backend.

### Preguntas probables

**«¿Está desplegado en OCI ahora mismo?»**
> El stack está listo y parametrizado —Dockerfiles, Compose, Nginx y variables
> de entorno documentadas—. El despliegue en la instancia lo está ejecutando el
> equipo de infraestructura. Lo que ven hoy corre con exactamente la misma
> configuración que se sube.

**«¿Los datos persisten?»**
> No todavía, y es nuestra deuda principal: el historial vive en memoria y se
> pierde al reiniciar el contenedor. Está documentado en el README con su
> siguiente paso: implementar un repositorio contra Oracle Autonomous Database
> cumpliendo el `Protocol` que ya existe. La arquitectura ya lo aísla; falta la
> implementación.

**«¿Seguridad?»**
> Lo que hay: contenedor con usuario sin privilegios, cabeceras de seguridad en
> Nginx, validación estricta con Pydantic y errores que nunca filtran
> stacktraces. Lo que falta: autenticación. Es la siguiente pieza y no la
> presentamos como hecha.

**«¿Cuánto tarda en arrancar?»**
> El backend carga el modelo al arrancar —por eso el healthcheck tiene 15
> segundos de gracia— y a partir de ahí cada clasificación es de milisegundos.
> El header `X-Process-Time` viene en todas las respuestas si quieren medirlo.

---

## 🎬 Demo en vivo — 4 pasos, 60 segundos

| # | Acción | Qué decir |
|---|---|---|
| 1 | **Dashboard** → señalar "Confianza del modelo" | *"Esto nos dice cuánto contenido clasificó la IA con poca certeza."* |
| 2 | **Agregar Curso** → pegar un texto → *Analizar con IA* | *"Categoría, confianza y tecnologías, del modelo real."* |
| 3 | **Buscar** → escribir `docker` → **esperar 2 s** | *"La búsqueda se guardó sola en el historial, con debounce."* |
| 4 | **Ver detalle** → panel lateral | *"Contenido relacionado — y abajo, **por qué**: comparten Docker."* |

> **Los dos ensayos obligatorios:** el paso 3 necesita 1.2 s de pausa sin
> teclear para que aparezca el chip. Y ten un texto técnico ya copiado al
> portapapeles para el paso 2 — escribirlo en vivo quema 20 segundos.

---

## 📌 Chuleta de números

| Dato | Valor |
|---|---|
| Pruebas · cobertura | **120** · **96.72%** (umbral CI 85%) |
| Modelo | `Pipeline(TfidfVectorizer → MultinomialNB)` · scikit-learn 1.6.1 |
| Clases del modelo | 5 |
| Recomendador | 75% palabras clave · 25% categoría · umbral 0.10 |
| Etapas de fallback | 4 + captura en caliente |
| Bundle frontend | 343 kB (109 kB gzip) · **0 KB** de librerías de gráficos |
| Endpoints REST | 10 |
| Latencia típica | milisegundos (`X-Process-Time` en cada respuesta) |

---

## ✅ Checklist antes de presentar

- [ ] `npm run dev` corriendo, sin errores en la terminal
- [ ] Header muestra el badge morado **"Modelo IA"** (no "Reglas")
- [ ] Dashboard con datos (si está vacío: `ATHENIA_SEED_DEMO=true`)
- [ ] Texto técnico copiado al portapapeles para el paso 2
- [ ] Paso 3 de la demo ensayado una vez (la pausa de 1.2 s)
- [ ] Terminal libre por si piden ver `pytest` en vivo
- [ ] Zoom del navegador al 100% y ventana maximizada

---

<div align="center">

**Ver también:**
[`README.md`](../README.md) ·
[`GUIA_EXPLICATIVA_SEMANA4_RECOMENDACIONES_Y_ANALITICAS.md`](GUIA_EXPLICATIVA_SEMANA4_RECOMENDACIONES_Y_ANALITICAS.md) ·
[`GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md`](GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md) ·
[`QA_TESTING_GUIDE.md`](QA_TESTING_GUIDE.md)

</div>
