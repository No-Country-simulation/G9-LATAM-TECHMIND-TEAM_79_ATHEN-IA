# Modelos entrenados

Punto de entrega del equipo de **Data Science**.

## Como integrar el modelo real

1. Guardar el artefacto entrenado aqui con el nombre exacto:

   ```
   backend/models/classifier.joblib
   ```

2. Reiniciar el backend. `app/services.py` detecta el archivo al arrancar y
   cambia solo del clasificador por reglas al modelo real. No hay que
   modificar rutas, esquemas, frontend ni pruebas.

3. Verificar:

   ```bash
   curl http://localhost:8000/salud
   ```

   Debe responder `"es_mock": false` y el nombre del artefacto en
   `modelo_cargado`.

## Contrato esperado del artefacto

Un objeto con la API de scikit-learn — idealmente un `Pipeline` que ya incluya
el vectorizador, para que reciba texto crudo:

```python
modelo.predict(["texto del curso"])        # -> array(["Backend"])
modelo.predict_proba(["texto del curso"])  # -> array([[0.02, 0.92, ...]])
modelo.classes_                            # -> array(["Backend", "Cloud", ...])
```

Ejemplo de guardado desde el notebook:

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

joblib.dump(pipeline, "backend/models/classifier.joblib")
```

## Notas

- El backend concatena el texto como `f"{titulo}. {texto}"`. Entrenar con esa
  misma forma mejora la consistencia entre entrenamiento e inferencia.
- Si el modelo no expone `predict_proba`, la API reporta una probabilidad
  neutra (`PROBABILIDAD_SIN_PROBA = 0.75`).
- `joblib` **no** esta en `requirements.txt`: el import es diferido y solo se
  ejecuta si existe el artefacto. Al entregar el modelo, agregar `joblib` y
  `scikit-learn` (con la version usada al entrenar) a `requirements.txt`.
- Los `.joblib` estan en `.gitignore`: se distribuyen por OCI Object Storage,
  no por el repositorio.
- Si la carga o la inferencia falla, el backend registra el error y sigue con
  el clasificador por reglas — la demo nunca se cae por un modelo corrupto.

## Ruta configurable

Para apuntar a otra ubicacion (por ejemplo un volumen montado en OCI):

```bash
export ATHENIA_MODELO_PATH=/mnt/modelos/classifier.joblib
```
