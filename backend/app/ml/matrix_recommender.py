import os
import joblib
import json
import numpy as np
from typing import List, Dict, Any

# Calcula la ruta absoluta apuntando a la carpeta 'Data' en la raíz del proyecto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # .../app/ml
BACKEND_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR)) # .../backend
ROOT_DIR = os.path.dirname(BACKEND_DIR) # Raíz del proyecto

MODEL_PATH = os.path.join(ROOT_DIR, 'Data', 'matriz_similitud_cursos.pkl')
MAPEO_PATH = os.path.join(ROOT_DIR, 'Data', 'mapeo_cursos.json')

class MatrixRecommender:
    def __init__(self):
        self.matriz_similitud = None
        self.mapeo_cursos = {}
        self._cargar_recursos()

    def _cargar_recursos(self):
        try:
            if os.path.exists(MODEL_PATH) and os.path.exists(MAPEO_PATH):
                self.matriz_similitud = joblib.load(MODEL_PATH)
                with open(MAPEO_PATH, 'r', encoding='utf-8') as f:
                    self.mapeo_cursos = json.load(f)
                print("✅ Modelo relacional .pkl y mapeo cargados exitosamente.")
            else:
                print(f"⚠️ Archivos no encontrados en: {MODEL_PATH} o {MAPEO_PATH}")
        except Exception as e:
            print(f"❌ Error al cargar el modelo relacional: {e}")

    def recomendar(self, curso_idx: int, top_n: int = 4) -> List[Dict[str, Any]]:
        if self.matriz_similitud is None or curso_idx >= len(self.matriz_similitud):
            return []

        # Extraer similitudes de la matriz NumPy
        similitudes = self.matriz_similitud[curso_idx]
        indices_ordenados = np.argsort(similitudes)[::-1]
        
        # Filtrar para no recomendar el mismo curso
        indices_filtrados = [int(i) for i in indices_ordenados if i != curso_idx][:top_n]

        resultados = []
        for idx in indices_filtrados:
            score = int(round(similitudes[idx] * 100))
            info = self.mapeo_cursos.get(str(idx), self.mapeo_cursos.get(idx, {}))

            if isinstance(info, dict):
                titulo = info.get("titulo", f"Curso {idx}")
                categoria = info.get("categoria", "Desarrollo y Tecnología")
                proveedor = info.get("proveedor", "Plataforma")
                tags = info.get("tags", [])
            else:
                titulo = str(info)
                categoria = "Desarrollo y Tecnología"
                proveedor = "Plataforma"
                tags = []

            resultados.append({
                "id": idx,
                "titulo": titulo,
                "categoria": categoria,
                "proveedor": proveedor,
                "match_score": score,
                "tags": tags
            })

        return resultados

# Instancia global accesible desde los routers
recomendador_matriz = MatrixRecommender()