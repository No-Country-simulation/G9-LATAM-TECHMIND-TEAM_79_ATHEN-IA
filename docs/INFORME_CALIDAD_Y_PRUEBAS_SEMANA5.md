# 📋 Informe de Calidad y Pruebas — Semana 5

**AthenIA** · Hackathon ONE Alura + Oracle / No Country · Generación 9
**Entrega final · Demo Day**

> Documento de cierre para el jurado, el equipo y QA. Todos los datos están
> verificados ejecutando la suite y consultando el despliegue real en OCI.

---

## 1. Resumen ejecutivo

| Indicador | Valor |
|---|---|
| **Pruebas automatizadas** | **150** · 100% en verde |
| **Cobertura de código** | **96.65%** (umbral de CI: 85%) |
| **Tiempo de la suite** | ~3 s |
| **Endpoints REST** | 10 |
| **Motor de IA en producción** | `modelo_ml_real` · `clasificador_cursos.pkl` |
| **Despliegue** | http://137.131.171.174:8080 (OCI · Docker Compose + Nginx) |

> ⚠️ **El despliegue en OCI corre la build anterior.** Las correcciones de esta
> Semana 5 (campo `nivel_confianza`, taxonomía de Ciberseguridad, avisos y
> arreglos de UI) están en el repositorio y verificadas en local, pero **aún no
> están publicadas**. Requieren un redespliegue — ver §6.4.

Estado verificado del despliegue al cierre:

```json
{
  "estado": "ok",
  "version": "0.4.0",
  "entorno": "production",
  "motor": "modelo_ml_real",
  "modelo_cargado": "clasificador_cursos.pkl",
  "es_mock": false
}
```

---

## 2. Suite de pruebas automatizadas

### 2.1 Distribución por archivo

| Archivo | Pruebas | Qué cubre |
|---|:---:|---|
| `test_api.py` | 75 | Contrato del Hackathon, validaciones, historial, métricas, modelo ML, arquitectura SOLID |
| `test_confianza.py` | 30 | **Semana 5** — niveles de confianza y robustez ante entradas ambiguas |
| `test_recomendaciones.py` | 22 | Índice de Jaccard, ranking, evidencia, motor sustituible |
| `test_analiticas.py` | 14 | Distribuciones, actividad temporal, regresión de `/metricas` |
| `test_resilience.py` | 4 | Casos borde, payloads masivos, inyección |
| `test_performance.py` | 3 | Latencia y SLA |
| `test_integration.py` | 2 | Flujo E2E |
| **Total** | **150** | |

### 2.2 Cobertura por módulo

```
Name                                   Stmts   Miss  Cover
--------------------------------------------------------------------
backend/app/__init__.py                    1      0   100%
backend/app/config.py                     46      4    91%
backend/app/dependencies.py               11      0   100%
backend/app/domain/confianza.py           17      2    88%
backend/app/domain/protocols.py           43      0   100%
backend/app/domain/similitud.py           33      0   100%
backend/app/domain/taxonomia.py           26      0   100%
backend/app/errors.py                     29      2    93%
backend/app/main.py                       36      1    97%
backend/app/ml/adaptador.py               50      0   100%
backend/app/ml/carga.py                   63      4    94%
backend/app/ml/modelo.py                  44      2    95%
backend/app/ml/registro.py                30      3    90%
backend/app/ml/reglas.py                  38      0   100%
backend/app/recomendador.py               24      0   100%
backend/app/repositories/memoria.py       45      1    98%
backend/app/routers/analiticas.py         10      0   100%
backend/app/routers/contenido.py          39      0   100%
backend/app/routers/salud.py              16      0   100%
backend/app/schemas.py                   111      1    99%
backend/app/services.py                   60      6    90%
--------------------------------------------------------------------
TOTAL                                    776     26    97%

Required test coverage of 85% reached. Total coverage: 96.65%
============================= 150 passed in 2.96s =============================
```

La cobertura **no es opcional**: `pytest.ini` incluye `--cov-fail-under=85`, así
que la suite falla si baja del umbral. Es la misma regla del pipeline de CI
(`.github/workflows/ci.yml`).

### 2.3 Casos añadidos en la Semana 5

Se detectaron probando el despliegue real con entradas que un jurado escribiría
para intentar romper la demo.

| Rango | Casos | Qué garantiza |
|---|:---:|---|
| `CP-300`…`CP-305` | 14 | Bandas de confianza: límites exactos, orden fijo, sin huecos en el rango 0–1 |
| `CP-310`…`CP-316` | 7 | `nivel_confianza` presente y coherente en respuesta, historial y listado |
| `CP-320`…`CP-323` | 7 | Ruido, símbolos, números, texto no técnico, HTML/JS, UTF-8 y textos masivos |
| `CP-330`…`CP-331` | 2 | Extracción de tecnologías en contenido de ciberseguridad |

---

## 3. Hallazgos de la auditoría y correcciones

### 3.1 🔴 El resultado de confianza baja se presentaba como certeza

**Hallazgo.** Al probar el despliegue con entradas ambiguas, todas devolvían
la misma categoría con probabilidad `0.37`:

| Entrada | Probabilidad | Categoría |
|---|:---:|---|
| `"x"` / `"y"` | 0.37 | Cloud Computing y DevOps |
| `"???"` / `"!!! @@@ ###"` | 0.37 | Cloud Computing y DevOps |
| *"Receta de arepas…"* | 0.37 | Cloud Computing y DevOps |

`0.37` es el **suelo del modelo**: un clasificador siempre elige una clase, no
tiene la opción de responder "no lo sé". El problema no era el modelo, sino que
la interfaz pintaba ese resultado **con la misma autoridad visual** que uno
del 93%: misma barra, mismo color, mismo formato.

**Riesgo para la demo.** Un jurado escribiendo cualquier cosa habría visto a
AthenIA clasificar con aparente seguridad un texto sin ningún sentido técnico.

**Corrección.**
- Nuevo módulo de dominio `app/domain/confianza.py` con las bandas
  Alta (≥75%) / Media (50–74%) / Baja (<50%), **reutilizando los mismos
  umbrales** que ya usaba el panel de analíticas (antes estaban duplicados).
- Campo `nivel_confianza` en la respuesta de `POST /contenido`, propagado al
  historial y al listado.
- La tarjeta de resultado muestra un aviso ámbar cuando el nivel es `baja`.

> **Límite honesto de esta corrección:** reporta la certeza *declarada por el
> modelo*, no detecta "contenido no técnico". Un texto sin señal puede recibir
> probabilidad alta si su vocabulario se parece por casualidad a una clase — de
> hecho *"El clima de hoy"* obtiene 0.66. Lo que se elimina es la **falsa
> apariencia de certeza**, no el error del modelo.

### 3.2 🟡 Contenido de ciberseguridad sin ninguna tecnología detectada

**Hallazgo.** El modelo tiene una clase `Ciberseguridad y Redes`, pero la
taxonomía de palabras clave **no tenía rama equivalente**. Un curso de
firewalls y pentesting se clasificaba, pero la tarjeta salía con
`informacion_adicional: []` — sin nada que mostrar.

**Corrección.** Rama `Ciberseguridad` en `domain/taxonomia.py` con 6 grupos
(Seguridad, Firewall, VPN, Pentesting, Criptografía, Redes). Verificado:

```
"Firewalls, VPN, pentesting y hardening con TLS"
  antes → informacion_adicional: []
  ahora → ["Seguridad", "Firewall", "VPN", "Pentesting", "Criptografia", "Redes"]
```

### 3.3 🟡 Desbordamiento en las tarjetas de métricas

**Hallazgo.** En `StatCard`, el contenedor del texto no tenía `min-w-0` y el
icono no tenía `shrink-0`. Con un valor o etiqueta larga, el icono se sale de
la tarjeta — y como el contenedor tiene `overflow-hidden`, se recorta.

**Corrección.** `min-w-0 flex-1` en el texto, `shrink-0` en el icono y
`truncate` con `title` para ver el valor completo al pasar el ratón.

### 3.4 🟡 Dos endpoints haciendo el mismo trabajo

**Hallazgo.** El Dashboard consumía `/analiticas` pero la vista Categorías
seguía llamando a `/metricas` — dos peticiones para el mismo agregado.

**Corrección.** `Categorias.jsx` unificado a `useAnaliticas()`. `/metricas` se
mantiene operativo por compatibilidad (hay pruebas de regresión que lo
verifican), pero ninguna vista lo consume ya.

### 3.5 ⚠️ Discrepancia de nombres de endpoints

Los endpoints `/clasificar` y `/recomendar` **no existen** — devuelven 404,
comprobado contra el despliegue. Los reales son:

| Se mencionó | Endpoint real |
|---|---|
| `/clasificar` | `POST /contenido` |
| `/recomendar` | `GET /contenidos/{id}/recomendaciones` |
| `/analiticas` | `GET /analiticas` ✅ correcto |
| `/salud` | `GET /salud` ✅ correcto |

**Importante para la demo:** si se indica al jurado probar `/clasificar`,
recibirá un 404. Usar siempre los nombres reales.

### 3.6 ✅ Falsa alarma descartada

Una prueba inicial contra el despliegue devolvió `400` con emojis. Se verificó
que era **un artefacto del shell** (comillas mal escapadas), no un fallo de la
API: enviando el mismo payload desde archivo, con y sin `charset=utf-8`, la
respuesta es `200`. El caso quedó cubierto por CP-322.

---

## 4. Verificación funcional del despliegue

Comprobado contra `http://137.131.171.174:8080`:

| Verificación | Resultado |
|---|:---:|
| Frontend responde (`GET /`) | ✅ 200 (0.28 s) |
| `GET /api/salud` — motor real activo | ✅ `modelo_ml_real` |
| `GET /api/analiticas` | ✅ 200 |
| `GET /api/categorias` | ✅ 200 |
| `GET /api/contenidos` | ✅ 200 |
| `GET /api/metricas` | ✅ 200 |
| Proxy Nginx `/api` → backend | ✅ funcionando |
| Precarga de demo (`ATHENIA_SEED_DEMO=true`) | ✅ historial poblado |
| Validación 422 (texto vacío, solo espacios, campo faltante) | ✅ |
| Sin CORS en el navegador (mismo origen vía Nginx) | ✅ |
| `nivel_confianza` en la respuesta | ⏳ pendiente de redespliegue |
| Taxonomía de Ciberseguridad | ⏳ pendiente de redespliegue |

> **Nota sobre CORS.** No hay peticiones cross-origin: Nginx sirve el frontend
> y proxea `/api` por la red interna de Docker, así que el navegador siempre ve
> el mismo origen. Esto elimina de raíz los problemas de CORS y de contenido
> mixto (HTTPS → HTTP) que habrían aparecido llamando al backend por su IP.

---

## 5. Checklist de Criterios de Aceptación

### 5.1 Contrato del Hackathon

- [x] `POST /contenido` acepta `{"titulo": "...", "texto": "..."}`
- [x] Devuelve `categoria` (string)
- [x] Devuelve `probabilidad` (float entre 0.0 y 1.0)
- [x] Devuelve `informacion_adicional` (lista de strings)
- [x] Los campos extra no rompen el contrato *(regresión CP-316)*
- [x] Payload inválido devuelve `422` con detalle del campo

### 5.2 Modelo de IA

- [x] Modelo real entrenado activo en producción (`clasificador_cursos.pkl`)
- [x] `Pipeline(TfidfVectorizer → MultinomialNB)`, 5 clases
- [x] `scikit-learn` fijado en 1.6.1, igual que en el entrenamiento
- [x] Fallback en 4 etapas verificado *(CP-100…CP-104)*
- [x] Error de inferencia en caliente no produce 500 *(CP-103)*
- [x] `GET /salud` reporta qué motor responde

### 5.3 Funcionalidades de valor

- [x] Recomendaciones por similitud con evidencia (`palabras_compartidas`)
- [x] Panel de analíticas con 4 dimensiones
- [x] Historial de búsquedas persistido en `localStorage`
- [x] Vista de detalle con contenido relacionado
- [x] Aviso de confianza baja *(nuevo en Semana 5)*

### 5.4 Interfaz

- [x] 4 vistas operativas: Inicio, Agregar, Buscar, Categorías
- [x] Estados de carga (skeletons y spinners) en todas las vistas
- [x] Errores de API visibles con `role="alert"`
- [x] Modal "Cerrar sesión" funcional, con limpieza real de datos locales
- [x] Badge del Header refleja la salud de la API en vivo
- [x] Diálogos accesibles (foco, `Escape`, focus trap)
- [x] Sin textos obsoletos ni desbordamientos en tarjetas
- [x] Responsive verificado en el build

### 5.5 Calidad y despliegue

- [x] 150 pruebas en verde
- [x] Cobertura 96.65% (> 85% exigido)
- [x] CI con umbral de cobertura en GitHub Actions
- [x] `docker compose up --build` levanta el stack completo
- [x] Desplegado y accesible en OCI
- [x] Contenedor con usuario sin privilegios y `HEALTHCHECK`

### 5.6 Conocido y no resuelto

Se declara explícitamente para que no se descubra en la demo:

- [ ] **Persistencia**: el historial vive en memoria y se pierde al reiniciar
      el contenedor. Siguiente paso: `RepositorioOracle` contra Autonomous
      Database, cumpliendo el `Protocol` que ya existe.
- [ ] **Autenticación**: no hay login. "Cerrar sesión" solo limpia datos
      locales del navegador.
- [ ] **Tests de frontend**: no hay pruebas automatizadas de UI; se valida con
      checklist manual y con el build en cada cambio.

---

## 6. Verificación rápida para el jurado

Tres comprobaciones que no requieren instalar nada. **Tiempo total: 2 minutos.**

### ✅ 1. La aplicación está viva y usa IA real

```bash
curl http://137.131.171.174:8080/api/salud
```

Buscar `"motor": "modelo_ml_real"` y `"es_mock": false`. Si dijera
`"clasificador_reglas"`, estaría respondiendo el fallback y no el modelo
entrenado.

### ✅ 2. El contrato del Hackathon se cumple

```bash
curl -X POST http://137.131.171.174:8080/api/contenido -H "Content-Type: application/json" -d "{\"titulo\":\"Machine Learning con Python\",\"texto\":\"Modelos con Scikit-Learn, Pandas y NLP usando TF-IDF.\"}"
```

Debe devolver `categoria`, `probabilidad` e `informacion_adicional`.
Resultado esperado: `Inteligencia Artificial y ML` con ~0.93 de confianza.

### ✅ 3. El sistema es honesto cuando no sabe

```bash
curl -X POST http://137.131.171.174:8080/api/contenido -H "Content-Type: application/json" -d "{\"titulo\":\"Receta de arepas\",\"texto\":\"Mezclar harina, agua y sal.\"}"
```

Un texto sin ninguna señal técnica devuelve `"probabilidad": 0.37` — el suelo
del modelo — e `"informacion_adicional": []`. El clasificador siempre elige una
clase, así que la baja probabilidad y la ausencia de tecnologías son la señal
de que **no encontró nada reconocible**.

> ⚠️ **Tras el redespliegue** esta respuesta incluirá además
> `"nivel_confianza": "baja"`, y la interfaz mostrará un aviso ámbar explícito.
> El campo existe en el repositorio y está cubierto por 30 pruebas, pero la
> instancia publicada todavía corre la build anterior.

> **En macOS/Linux** usar comillas simples alrededor del JSON:
> `-d '{"titulo":"..."}'`.

### 🖥️ Recorrido por la interfaz — 90 segundos

| # | Dónde | Qué observar |
|---|---|---|
| 1 | http://137.131.171.174:8080 | Badge morado **"Modelo IA"** en la esquina superior derecha |
| 2 | **Inicio** | Panel de analíticas: distribución de confianza del modelo |
| 3 | **Agregar Curso** | Pegar un texto técnico → categoría, confianza y tecnologías |
| 4 | **Buscar** → escribir `docker`, esperar 2 s | La búsqueda se guarda sola en el historial |
| 5 | **Ver detalle** | Contenido relacionado con la explicación *"Comparten: Docker"* |

### 🔄 6.4 Redespliegue pendiente

Las correcciones de la Semana 5 están commiteadas y verificadas en local, pero
la instancia de OCI sigue sirviendo la build anterior. Para publicarlas:

```bash
docker compose up --build -d
```

Comprobación posterior — debe aparecer el campo nuevo:

```bash
curl -s http://137.131.171.174:8080/api/contenido -X POST -H "Content-Type: application/json" -d "{\"titulo\":\"t\",\"texto\":\"Docker\"}" | grep nivel_confianza
```

Sin este paso, lo que ve el jurado en la URL pública **no incluye** el aviso de
confianza baja ni las palabras clave de ciberseguridad.

---

### 🧪 Reproducir la suite de pruebas

```bash
pytest
```

Salida esperada: `150 passed` y `Total coverage: 96.65%`.

---

## 7. Trazabilidad

| Documento | Contenido |
|---|---|
| [`README.md`](../README.md) | Guía definitiva: arquitectura, ejecución, endpoints |
| [`QA_TESTING_GUIDE.md`](QA_TESTING_GUIDE.md) | Catálogo completo de casos y fixtures |
| [`GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md`](GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md) | Arquitectura SOLID e integración ML |
| [`GUIA_EXPLICATIVA_SEMANA4_RECOMENDACIONES_Y_ANALITICAS.md`](GUIA_EXPLICATIVA_SEMANA4_RECOMENDACIONES_Y_ANALITICAS.md) | Jaccard y analíticas paso a paso |
| [`PRESENTACION_EQUIPO_SEMANA4_5.md`](PRESENTACION_EQUIPO_SEMANA4_5.md) | Guion del Demo Day |
| [`backend/models/README.md`](../backend/models/README.md) | Contrato del artefacto para Data Science |

---

<div align="center">

**AthenIA** · Semana 5 · Entrega final
*150 pruebas · 96.65% de cobertura · desplegado en Oracle Cloud Infrastructure*

</div>
