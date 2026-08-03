# Modelos entrenados

Punto de entrega del equipo de **Data Science**.

## Cómo integrar el modelo

1. Dejar el artefacto entrenado en esta carpeta con el nombre acordado:

   ```
   backend/models/clasificador_cursos.pkl
   ```

2. Reiniciar el backend. `app/services.py` lo detecta al arrancar y cambia solo
   del clasificador por reglas al modelo real. **No hay que modificar rutas,
   esquemas, frontend ni pruebas.**

3. Verificar:

   ```bash
   curl http://localhost:8000/salud
   ```

   Debe responder:

   ```json
   {
     "motor": "modelo_ml_real",
     "modelo_cargado": "clasificador_cursos.pkl",
     "detalle_modelo": "Pipeline",
     "es_mock": false
   }
   ```

   Si responde `"motor": "clasificador_reglas"`, el artefacto no se cargó.
   Revisar los logs del servidor: dicen exactamente en qué etapa falló.

---

## Formatos aceptados

El backend acepta las tres formas en que un notebook suele guardar el modelo.
No hay que adaptar nada del lado de Data Science.

### 1. Pipeline completo — **recomendado**

Incluye el vectorizador, así que recibe texto crudo:

```python
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
    ("clf", LogisticRegression(max_iter=1000)),
])
pipeline.fit(X_train, y_train)

joblib.dump(pipeline, "backend/models/clasificador_cursos.pkl")
```

### 2. Diccionario con las piezas por separado

```python
joblib.dump(
    {"modelo": clf, "vectorizador": tfidf},
    "backend/models/clasificador_cursos.pkl",
)
```

Claves reconocidas — el orden no importa:

| Pieza | Claves aceptadas |
|-------|------------------|
| Modelo | `modelo`, `model`, `clf`, `classifier`, `clasificador`, `estimator` |
| Vectorizador | `vectorizador`, `vectorizer`, `tfidf`, `vec`, `transformer` |

### 3. Tupla o lista de dos elementos

```python
joblib.dump((tfidf, clf), "backend/models/clasificador_cursos.pkl")
```

El orden tampoco importa: el backend identifica cada pieza por sus métodos
(`.predict()` vs `.transform()`).

> **Serialización:** sirven tanto `joblib.dump` como `pickle.dump`. El backend
> intenta primero con joblib y, si falla, con pickle.

---

## Cómo se construye la entrada

El backend concatena título y texto así antes de predecir:

```python
entrada = f"{titulo}. {texto}"
```

**Entrenar con esa misma concatenación** mejora la consistencia entre
entrenamiento e inferencia.

---

## Contrato esperado

```python
modelo.predict(["texto del curso"])        # -> array(["Backend"])
modelo.predict_proba(["texto del curso"])  # -> array([[0.02, 0.92, ...]])
modelo.classes_                            # -> array(["Backend", "Cloud", ...])
```

- `classes_` alimenta `GET /categorias`, que el frontend usa para pintar los
  filtros. Si el modelo no lo expone, se usa el catálogo local.
- Si el modelo no expone `predict_proba`, la API reporta una probabilidad
  neutra (`PROBABILIDAD_SIN_PROBA = 0.75`).
- Las **palabras clave** (`informacion_adicional`) se siguen extrayendo por
  taxonomía, no las produce el modelo.

---

## Mecanismo de fallback

`obtener_clasificador()` degrada al clasificador por reglas si falla cualquiera
de estas cuatro etapas:

| # | Etapa | Qué puede fallar |
|---|-------|------------------|
| 1 | **Localizar** | El archivo no está en la carpeta |
| 2 | **Deserializar** | Pickle corrupto, versión de sklearn incompatible, dependencia ausente |
| 3 | **Adaptar** | Estructura desconocida o sin `.predict()` |
| 4 | **Sondear** | Carga bien pero revienta al predecir (p. ej. vectorizador olvidado) |

Además, `ClasificadorML.clasificar()` captura errores de inferencia **en
caliente**: si `predict` lanza durante una petición real, esa petición se
responde con reglas en vez de devolver un 500.

**La demo nunca se cae por un problema del modelo.**

---

## Versiones

`scikit-learn` debe coincidir con la versión usada al entrenar. Un desajuste
mayor hace que `pickle.load` falle o emita `InconsistentVersionWarning`.

Versión fijada actualmente en `backend/requirements.txt`:

```
scikit-learn==1.9.0
joblib==1.5.3
numpy==2.5.1
pandas==3.0.5
```

Si entrenaste con otra versión, avísale al equipo de backend para alinear el
pin antes de la demo.

---

## Ruta configurable

Para apuntar a otra ubicación (por ejemplo un volumen montado en OCI):

```bash
export ATHENIA_MODELO_PATH=/mnt/modelos/clasificador_cursos.pkl
```

O cambiar solo la carpeta de búsqueda:

```bash
export ATHENIA_MODELOS_DIR=/mnt/modelos
```

---

## Notas

- Los `.pkl` y `.joblib` están en `.gitignore`: se distribuyen por OCI Object
  Storage, no por el repositorio.
- Si entregas el archivo con otro nombre, el backend igual lo detecta (usa el
  `.pkl`/`.joblib` más reciente de la carpeta) y lo avisa en los logs — pero es
  preferible respetar `clasificador_cursos.pkl`.
