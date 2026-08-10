"""
Adaptador del artefacto entregado por Data Science.
=====================================================

`AdaptadorModelo` normaliza las formas en que Data Science puede entregar el
artefacto. El backend no puede asumir una sola estructura: segun como se haya
guardado el modelo, `pickle.load`/`joblib.load` devuelve cosas distintas.
Este adaptador detecta cual llego y expone siempre la misma interfaz
(`predict`, `predict_proba`, `clases`) — es el patron **Adapter** aplicado a
un artefacto externo cuya forma no controlamos.

Formas soportadas
------------------
1. `Pipeline` de scikit-learn que ya incluye el vectorizador:
       pipeline.predict(["texto crudo"])
2. `dict` con el modelo y el vectorizador por separado:
       {"modelo": clf, "vectorizador": tfidf}
   (se aceptan las claves habituales en ingles y espanol)
3. `tuple` / `list` de dos elementos, en cualquier orden:
       (tfidf, clf)  o  (clf, tfidf)
"""

from __future__ import annotations

from typing import List, Optional


class AdaptadorModelo:
    """Envuelve el artefacto crudo con una interfaz `predict`/`predict_proba` uniforme."""

    # Claves habituales con las que un notebook guarda cada pieza.
    CLAVES_MODELO = ("modelo", "model", "clf", "classifier", "clasificador", "estimator")
    CLAVES_VECTORIZADOR = ("vectorizador", "vectorizer", "tfidf", "vec", "transformer")

    def __init__(self, artefacto) -> None:
        self._modelo, self._vectorizador = self._descomponer(artefacto)

        if not hasattr(self._modelo, "predict"):
            raise TypeError(
                "El artefacto no expone `.predict()`. Revisa como se guardo el modelo."
            )

    # --- Deteccion de la forma del artefacto -------------------------------

    @classmethod
    def _descomponer(cls, artefacto):
        """Devuelve `(modelo, vectorizador_o_None)` segun la forma recibida."""
        if isinstance(artefacto, dict):
            modelo = cls._primero_con(artefacto, cls.CLAVES_MODELO, "predict")
            vectorizador = cls._primero_con(artefacto, cls.CLAVES_VECTORIZADOR, "transform")
            if modelo is None:
                # Ultimo recurso: cualquier valor del dict que sepa predecir.
                modelo = next((v for v in artefacto.values() if hasattr(v, "predict")), None)
            return modelo, vectorizador

        if isinstance(artefacto, (tuple, list)) and len(artefacto) == 2:
            primero, segundo = artefacto
            # El orden no esta garantizado: se identifica por capacidades.
            if hasattr(primero, "predict"):
                return primero, segundo if hasattr(segundo, "transform") else None
            return segundo, primero if hasattr(primero, "transform") else None

        # Caso mas comun y recomendado: un Pipeline que acepta texto crudo.
        return artefacto, None

    @staticmethod
    def _primero_con(diccionario: dict, claves, metodo: str):
        """Primer valor cuya clave este en `claves` y que exponga `metodo`."""
        for clave in claves:
            valor = diccionario.get(clave)
            if valor is not None and hasattr(valor, metodo):
                return valor
        return None

    # --- Interfaz uniforme --------------------------------------------------

    @property
    def requiere_vectorizador(self) -> bool:
        return self._vectorizador is not None

    def _preparar(self, textos: List[str]):
        """Aplica el vectorizador si el modelo no lo trae embebido."""
        if self._vectorizador is None:
            return textos
        return self._vectorizador.transform(textos)

    def predict(self, textos: List[str]):
        return self._modelo.predict(self._preparar(textos))

    def predict_proba(self, textos: List[str]):
        if not hasattr(self._modelo, "predict_proba"):
            return None
        return self._modelo.predict_proba(self._preparar(textos))

    @property
    def clases(self) -> Optional[List[str]]:
        clases = getattr(self._modelo, "classes_", None)
        return None if clases is None else [str(c) for c in clases]

    def describir(self) -> str:
        """Descripcion corta del artefacto, para logs y `GET /salud`."""
        tipo = type(self._modelo).__name__
        return f"{tipo}+vectorizador" if self.requiere_vectorizador else tipo
