# 🧪 Guía de Pruebas — QA AthenIA

> Documento dirigido al **QA Tester** del equipo.
> Explica qué se está probando, por qué, cómo ejecutarlo y qué hacer cuando algo falla.

**Estado actual: 73 pruebas automatizadas, todas en verde.**

---

## 📑 Contenido

1. [Puesta en marcha](#1-puesta-en-marcha)
2. [Cómo ejecutar las pruebas](#2-cómo-ejecutar-las-pruebas)
3. [Cómo está organizada la suite](#3-cómo-está-organizada-la-suite)
4. [Catálogo de casos de prueba](#4-catálogo-de-casos-de-prueba)
5. [Fixtures disponibles](#5-fixtures-disponibles)
6. [Pruebas manuales de UI](#6-pruebas-manuales-de-ui)
7. [Pruebas exploratorias con Swagger y Postman](#7-pruebas-exploratorias-con-swagger-y-postman)
8. [Cómo agregar un caso nuevo](#8-cómo-agregar-un-caso-nuevo)
9. [Solución de problemas](#9-solución-de-problemas)
10. [Criterios de aceptación](#10-criterios-de-aceptación)

---

## 1. Puesta en marcha

Desde la raíz del repositorio:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\python -m pip install -r backend/requirements.txt
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

> **No hace falta levantar el servidor.** Las pruebas usan `TestClient` de FastAPI,
> que ejecuta la aplicación en memoria. Son rápidas (< 1 segundo) y no dependen
> de puertos ni de red.

---

## 2. Cómo ejecutar las pruebas

### Suite completa

```bash
npm test
```

o directamente:

```bash
pytest
```

### Salida esperada

```
collected 48 items
backend/tests/test_api.py::test_salud_responde_200 PASSED               [  2%]
...
============================= 48 passed in 0.26s ==============================
```

### Comandos útiles

| Objetivo | Comando |
|----------|---------|
| Solo un archivo | `pytest backend/tests/test_api.py` |
| Solo un caso | `pytest -k test_salud_responde_200` |
| Solo validaciones | `pytest -k "422 or vacias or espacios"` |
| Solo historial | `pytest -k "historial or contenidos"` |
| Solo métricas | `pytest -k metricas` |
| Detener en el primer fallo | `pytest -x` |
| Ver `print` y logs | `pytest -s` |
| Traza completa del error | `pytest --tb=long` |
| Los 5 casos más lentos | `pytest --durations=5` |

### Reporte de cobertura (opcional)

```bash
pip install pytest-cov
```

```bash
pytest --cov=backend/app --cov-report=term-missing
```

---

## 3. Cómo está organizada la suite

```
backend/tests/
├── conftest.py     # Configuración y fixtures compartidas
└── test_api.py     # Los 48 casos de prueba
```

### Qué hace `conftest.py`

1. **Desactiva la semilla de demo** (`ATHENIA_SEED_DEMO=false`) *antes* de importar la
   aplicación, para que cada prueba parta de un historial vacío y predecible.
2. **Agrega `backend/` al `sys.path`**, para que `from app.main import app` funcione
   sin instalar el backend como paquete.
3. **Limpia el historial antes y después de cada prueba** (fixture `autouse`), de modo
   que ninguna prueba dependa del orden de ejecución.

### Convención de nombres

Cada caso lleva un identificador `CP-xx` en su docstring, que corresponde al
[catálogo de la sección 4](#4-catálogo-de-casos-de-prueba):

```python
def test_salud_responde_200(client):
    """CP-01: el health check responde 200 mientras el servicio este vivo."""
    assert client.get("/salud").status_code == 200
```

| Rango | Grupo |
|-------|-------|
| `CP-01` … `CP-03` | Meta y uptime |
| `CP-10` … `CP-16` | `POST /contenido` — caso feliz |
| `CP-20` … `CP-27` | `POST /contenido` — validaciones (422) |
| `CP-30` … `CP-33` | Métodos, rutas y catálogo |
| `CP-40` | CORS (integración Frontend ↔ Backend) |
| `CP-50` … `CP-58` | `GET /contenidos` — historial |
| `CP-60` … `CP-63` | Detalle y borrado del historial |
| `CP-70` … `CP-73` | `GET /metricas` — Dashboard |
| `CP-80` … `CP-81` | Metadatos y estado por defecto |
| `CP-90` … `CP-99` | Integración del modelo ML (pipeline entrenado al vuelo) |
| `CP-100` … `CP-105` | Resiliencia del mecanismo de fallback |
| `CP-110` … `CP-113` | Artefacto **real** de Data Science |

---

## 4. Catálogo de casos de prueba

### 4.1 Meta y uptime — `GET /salud`, `GET /`

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-01 | Health check responde | HTTP 200 |
| CP-02 | Health check informa estado | `estado="ok"`, `version`, `modelo_cargado` y `contenidos_en_historial` presentes |
| CP-03 | La raíz lista los endpoints | Incluye `POST /contenido` |

### 4.2 `POST /contenido` — caso feliz

| ID | Caso | Entrada | Resultado esperado |
|----|------|---------|--------------------|
| CP-10 | Payload válido | Curso de Spring Boot | HTTP 200 |
| CP-11 | Contrato del Hackathon | Ídem | Respuesta con `categoria` (str), `probabilidad` (float), `informacion_adicional` (list[str]) |
| CP-12 | Probabilidad normalizada | Ídem | `0.0 <= probabilidad <= 1.0` |
| CP-13 | Clasificación correcta | Ídem | `categoria == "Backend"` y `"Spring Boot"` entre las palabras clave |
| CP-14 | Multicategoría *(4 variantes)* | Textos de Data Science, DevOps, Frontend y Cloud | Cada uno cae en su categoría |
| CP-15 | Contenido no técnico | *"Receta de arepas"* | `categoria == "Otros"` — no se fuerza una categoría técnica |
| CP-16 | Determinismo | Dos llamadas idénticas | Misma clasificación (se excluye el `id`, que cambia por diseño) |

### 4.3 `POST /contenido` — validaciones (422)

| ID | Caso | Entrada | Resultado esperado |
|----|------|---------|--------------------|
| CP-20 | Falta `texto` | `{"titulo": "Solo titulo"}` | HTTP 422 |
| CP-21 | Falta `titulo` | `{"texto": "Solo texto"}` | HTTP 422 |
| CP-22 | Body vacío | `{}` | HTTP 422 |
| CP-23 | Cadenas vacías *(3 variantes)* | `titulo=""`, `texto=""`, ambos | HTTP 422 |
| CP-24 | Solo espacios *(2 variantes)* | `"   "`, `"\n\t "` | HTTP 422 |
| CP-25 | Tipos incorrectos | `{"titulo": 123, "texto": ["lista"]}` | HTTP 422 |
| CP-26 | Detalle del campo | `{"titulo": "Solo titulo"}` | `detail` identifica el campo `texto` |
| CP-27 | Formato `ErrorResponse` | `{}` | Respuesta con `error="validacion"` y `mensaje` legible |

> **Por qué importa CP-23 y CP-24:** `min_length=1` de Pydantic no rechaza `"   "`.
> Un validador propio en `ContenidoInput` cubre ese hueco.

### 4.4 Métodos, rutas y catálogo

| ID | Caso | Petición | Resultado esperado |
|----|------|----------|--------------------|
| CP-30 | Método no permitido | `GET /contenido` | HTTP 405 |
| CP-31 | Ruta inexistente | `GET /ruta-que-no-existe` | HTTP 404 |
| CP-32 | Catálogo de categorías | `GET /categorias` | Lista que incluye `"Backend"` |
| CP-33 | Tiempo de proceso | Cualquier petición | Header `X-Process-Time` presente, en `ms` |

### 4.5 CORS — integración Frontend ↔ Backend

| ID | Caso | Petición | Resultado esperado |
|----|------|----------|--------------------|
| CP-40 | CORS habilitado | `POST /contenido` con `Origin: http://localhost:5173` | HTTP 200 y `access-control-allow-origin: *` |

### 4.6 `GET /contenidos` — historial

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-50 | Historial vacío al inicio | `total == 0`, `items == []` |
| CP-51 | Analizar guarda en el historial | `total == 1` con el título enviado |
| CP-52 | Se conserva el original | El ítem incluye `texto`, `creado_en` y `categoria` |
| CP-53 | Orden descendente | El último análisis aparece primero |
| CP-54 | Filtro por categoría | `?categoria=DevOps` devuelve solo esa categoría |
| CP-55 | Búsqueda libre | `?buscar=docker` encuentra por título, texto o palabra clave |
| CP-56 | Insensible a mayúsculas y acentos | `?buscar=PYTHON` encuentra el contenido |
| CP-57 | Límite | `?limite=2` devuelve 2 ítems |
| CP-58 | Sin coincidencias | `total == 0` — no es un error |

### 4.7 Detalle y borrado

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-60 | Detalle por id | HTTP 200 con el `id` y el `titulo` correctos |
| CP-61 | Id inexistente | HTTP 404 con `error == "http_404"` |
| CP-62 | Id no numérico | HTTP 422 |
| CP-63 | Vaciar historial | `DELETE /contenidos` responde el número de eliminados y deja el historial en 0 |

### 4.8 `GET /metricas` — Dashboard

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-70 | Historial vacío | Todo en cero, sin errores |
| CP-71 | Conteos correctos | `total_cursos`, `total_categorias` y `total_palabras_clave` reflejan el historial |
| CP-72 | Distribución consistente | La suma de `cantidad` iguala `total_cursos`; cada `porcentaje` entre 0 y 100 |
| CP-73 | Confianza promedio | Valor entre 0 y 1 |

### 4.9 Estado por defecto y metadatos

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-80 | Sin artefacto en `backend/models/` | `motor == "clasificador_reglas"`, `es_mock == true` |
| CP-81 | Metadatos opcionales | `origen` y `url` se guardan y se recuperan en el detalle |

### 4.10 Integración del modelo ML — `CP-90` … `CP-99`

Estas pruebas **entrenan un `Pipeline` real de scikit-learn al vuelo** (TF-IDF +
regresión logística sobre un corpus mínimo) y lo serializan igual que lo hace
Data Science. No dependen de que el `.pkl` de producción esté presente, pero
ejercitan exactamente el mismo camino de carga, adaptación e inferencia.

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-90 | Artefacto presente | `motor == "modelo_ml_real"`, `detalle_modelo == "Pipeline"` |
| CP-91 | La predicción viene del modelo | Categoría del modelo y `modelo == "clasificador_cursos.pkl"` |
| CP-92 | Contrato intacto | Las tres claves del Hackathon no cambian con el motor ML |
| CP-93 | Clases del modelo | `GET /categorias` devuelve `classes_` del artefacto |
| CP-94 | Validación con ML activo | Payloads inválidos siguen dando 422 |
| CP-95 | Texto mínimo | Una sola palabra no rompe la inferencia |
| CP-96 | joblib y pickle *(2 variantes)* | Carga con cualquiera de los dos formatos |
| CP-97 | Vectorizador separado *(4 variantes)* | `dict` es/en, `tuple` y `list` se recomponen |
| CP-98 | Autodetección por nombre | Sin `ATHENIA_MODELO_PATH` encuentra el archivo en la carpeta |
| CP-99 | Probabilidad coherente | Coincide con el máximo de `predict_proba` |

### 4.11 Resiliencia del fallback — `CP-100` … `CP-105`

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-100 | `.pkl` corrupto | Degrada a reglas; la API sigue clasificando |
| CP-101 | Objeto sin `.predict()` | Se rechaza el artefacto y se usa el fallback |
| CP-102 | Ruta inexistente | `ATHENIA_MODELO_PATH` inválido no rompe el arranque |
| CP-103 | Fallo de inferencia en caliente | Responde con reglas; `modelo` incluye `"fallback"` |
| CP-104 | Sonda de carga | Un modelo sin su vectorizador se descarta antes de exponerse |
| CP-105 | Categorías relacionadas | Salen de `predict_proba`, no se mezclan con la taxonomía de reglas |

### 4.12 Artefacto real de Data Science — `CP-110` … `CP-113`

Cargan el `clasificador_cursos.pkl` **real** del repositorio.

> Se **saltan solas** si el archivo no está presente (los `.pkl` están en
> `.gitignore` y se distribuyen por OCI Object Storage). Si el archivo existe
> pero no se activa, la prueba **falla** — eso sí es un problema real.

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CP-110 | Carga y activa el motor ML | `motor == "modelo_ml_real"` con el artefacto real |
| CP-111 | Contrato del Hackathon | Se mantiene con el modelo de producción |
| CP-112 | Predicciones dentro del catálogo | Toda categoría pertenece a `classes_` |
| CP-113 | Texto con acentos y ñ | UTF-8 correcto de extremo a extremo |

---

## 5. Fixtures disponibles

Definidas en `backend/tests/conftest.py`. Se piden declarándolas como parámetro
de la función de prueba.

| Fixture | Alcance | Qué entrega |
|---------|---------|-------------|
| `client` | sesión | `TestClient` de FastAPI. No requiere servidor levantado. |
| `motor_por_reglas` | sesión (**autouse**) | Apunta la búsqueda de modelos a una carpeta vacía. Ver nota abajo. |
| `historial_limpio` | función (**autouse**) | Vacía el historial antes y después de cada prueba. Se aplica sola. |
| `payload_valido` | función | Payload de referencia — curso de Spring Boot. |
| `historial_poblado` | función | Crea tres análisis de categorías distintas y devuelve sus respuestas. |
| `modelo_ml_real` | función | Entrena un `Pipeline` de scikit-learn al vuelo y lo activa como `clasificador_cursos.pkl`. |
| `activar_artefacto` | función | Fábrica: serializa cualquier objeto, lo activa y restaura el estado al final. |
| `artefacto_real` | función | Activa el `.pkl` real del repositorio. Hace `skip` si no está presente. |

> **Por qué existe `motor_por_reglas`:** sin él, las pruebas de clasificación
> (CP-13 a CP-15) pasarían a evaluar la precisión del modelo de Data Science en
> cuanto apareciera el `.pkl`, y romperían sin que nadie hubiera tocado el
> backend. Forzando el motor por reglas, la suite mide **el backend**, no el
> modelo. Las pruebas que sí necesitan el modelo lo montan explícitamente.

Ejemplo:

```python
def test_mi_caso(client, payload_valido):
    respuesta = client.post("/contenido", json=payload_valido)
    assert respuesta.status_code == 200
```

---

## 6. Pruebas manuales de UI

Checklist a ejecutar antes de cada entrega. Requiere ambos servicios arriba
(`npm run dev`).

| ID | Caso | Pasos | Resultado esperado |
|----|------|-------|--------------------|
| UI-01 | Análisis exitoso | **Agregar Curso** → llenar título y descripción → *Analizar con IA* | Aparece la tarjeta con categoría, % de confianza y badges de palabras clave |
| UI-02 | Estado de carga | Enviar el formulario y observar el panel derecho | Se ve el spinner con los pasos del análisis |
| UI-03 | Validación en cliente | Enviar el formulario vacío | Mensajes bajo cada campo; **no** se llama al backend |
| UI-04 | Texto demasiado corto | Escribir menos de 20 caracteres en la descripción | Mensaje pidiendo más contenido |
| UI-05 | Backend caído | Apagar el backend → analizar | Mensaje *"No se pudo conectar…"*; el indicador del Header pasa a rojo |
| UI-06 | Indicador de API | Backend arriba → recargar | Indicador verde *"API conectada"* en el Header |
| UI-07 | Dashboard dinámico | Analizar un contenido → ir a **Inicio** | Los contadores y el gráfico de dona incluyen el nuevo contenido |
| UI-08 | Dashboard vacío | `DELETE /contenidos` → recargar Inicio | Estado vacío con invitación a analizar contenido |
| UI-09 | Búsqueda en tiempo real | En **Buscar**, escribir `docker` letra por letra | Los resultados se filtran sin pulsar ningún botón |
| UI-10 | Filtro por categoría | Pulsar el badge `Backend` | Solo se muestran contenidos de Backend; el badge queda resaltado |
| UI-11 | Búsqueda sin resultados | Buscar `zzzzz` | Estado vacío *"Sin resultados"* |
| UI-12 | Buscador del Header | Escribir un término y pulsar Enter | Navega a `/buscar?q=<término>` con el filtro aplicado |
| UI-13 | Esqueletos de carga | Recargar **Buscar** con la red lenta (DevTools → Slow 3G) | Se ven tarjetas esqueleto antes de los datos |
| UI-14 | Responsive | Reducir la ventana a ancho móvil | El Sidebar se convierte en drawer y se abre con el botón de menú |
| UI-15 | Ruta inválida | Ir a `/no-existe` | Pantalla 404 con enlace de retorno |
| UI-16 | Accesibilidad básica | Navegar solo con `Tab` | Todos los controles reciben foco visible |

---

## 7. Pruebas exploratorias con Swagger y Postman

### Swagger UI (sin instalar nada)

Con el backend arriba, abrir:

```
http://localhost:8000/docs
```

Permite ejecutar cualquier endpoint desde el navegador con *Try it out*, ver los
esquemas de request/response y los códigos de error documentados.

### Postman / Thunder Client

Configurar una colección con estas peticiones:

| Nombre | Método | URL | Body |
|--------|--------|-----|------|
| Salud | GET | `http://localhost:8000/salud` | — |
| Analizar (feliz) | POST | `http://localhost:8000/contenido` | `{"titulo":"Introduccion a Spring Boot","texto":"APIs REST con Spring Boot, JWT y JPA."}` |
| Analizar (422) | POST | `http://localhost:8000/contenido` | `{"titulo":"Solo titulo"}` |
| Historial | GET | `http://localhost:8000/contenidos` | — |
| Buscar | GET | `http://localhost:8000/contenidos?buscar=docker` | — |
| Detalle | GET | `http://localhost:8000/contenidos/1` | — |
| Métricas | GET | `http://localhost:8000/metricas` | — |
| Limpiar | DELETE | `http://localhost:8000/contenidos` | — |

Recordar el header `Content-Type: application/json` en los `POST`.

Los ejemplos equivalentes con `curl` están en el
[README](../README.md#-ejemplos-con-curl).

---

## 8. Cómo agregar un caso nuevo

1. Abrir `backend/tests/test_api.py`.
2. Ubicar la sección correspondiente (están separadas por comentarios `====`).
3. Escribir la función siguiendo la convención:

```python
def test_descripcion_clara_de_lo_que_valida(client, payload_valido):
    """CP-XX: una frase explicando qué garantiza este caso."""
    respuesta = client.post("/contenido", json=payload_valido)

    assert respuesta.status_code == 200
    assert respuesta.json()["categoria"] == "Backend"
```

4. Agregar la fila correspondiente en la [sección 4](#4-catálogo-de-casos-de-prueba)
   de este documento.
5. Ejecutar `pytest` y confirmar que pasa.

### Probar varias entradas con un solo caso

```python
@pytest.mark.parametrize(
    "titulo,texto,esperado",
    [
        ("Curso de Kubernetes", "Orquestacion de contenedores.", "DevOps"),
        ("Curso de Pandas", "Analisis de datos con Pandas.", "Data Science"),
    ],
)
def test_clasificacion(client, titulo, texto, esperado):
    """CP-XX: el clasificador distingue estas categorías."""
    respuesta = client.post("/contenido", json={"titulo": titulo, "texto": texto})
    assert respuesta.json()["categoria"] == esperado
```

### Buenas prácticas del equipo

- **Un `assert` conceptual por caso.** Si la prueba falla, debe quedar claro qué se rompió.
- **Nombres descriptivos en español**, coherentes con el resto de la suite.
- **Nunca depender del orden de ejecución** — el fixture `historial_limpio` ya lo garantiza.
- **Documentar el `CP-xx`** en el docstring para poder rastrear el caso hasta esta guía.

---

## 9. Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `ModuleNotFoundError: No module named 'app'` | Se ejecutó `pytest` desde otra carpeta | Ejecutar desde la **raíz** del repositorio; `pytest.ini` define `pythonpath = backend` |
| `ModuleNotFoundError: No module named 'fastapi'` | Entorno virtual sin dependencias o sin activar | `.venv\Scripts\python -m pip install -r backend/requirements.txt` |
| `command not found: pytest` | Pytest fuera del PATH | Usar `npm test`, o `.venv\Scripts\python -m pytest` |
| Fallan las pruebas de historial | Semilla de demo activa | Verificar que `conftest.py` fija `ATHENIA_SEED_DEMO=false` |
| CP-80 falla | Ya existe `backend/models/classifier.joblib` | Es lo esperado tras integrar el modelo: actualizar el caso a `es_mock == false` |
| `Address already in use` al levantar el backend | Puerto 8000 ocupado | Cerrar el proceso anterior o usar `ATHENIA_PORT=8001` |
| El frontend no conecta | Backend apagado | `npm run dev:backend` y revisar `GET /salud` |

---

## 10. Criterios de aceptación

Para dar por buena la entrega de las Semanas 1–2:

- [x] `pytest` en verde — **48/48 pruebas**.
- [x] `POST /contenido` cumple el contrato exigido por el Hackathon.
- [x] Payload inválido responde `422` con detalle del campo.
- [x] `GET /salud` disponible para monitoreo de uptime.
- [x] Historial (`GET /contenidos`) y métricas (`GET /metricas`) operativos.
- [x] CORS habilitado para el dev server de Vite.
- [x] Mecanismo de fallback verificado: la API responde sin modelo entrenado.
- [x] `npm run build` del frontend compila sin errores.
- [ ] Checklist manual **UI-01 … UI-16** ejecutado antes de la demo.

---

<div align="center">

📖 Documentación general: [`README.md`](../README.md)
🤖 Integración del modelo: [`backend/models/README.md`](../backend/models/README.md)

</div>
