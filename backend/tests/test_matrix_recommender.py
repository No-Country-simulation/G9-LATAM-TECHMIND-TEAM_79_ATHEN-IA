"""
Pruebas del recomendador por matriz de similitud (Modelo Relacional).
========================================================================

`app/ml/matrix_recommender.py` llegó sin ninguna cobertura (0%, 68
sentencias) — es lo que hizo caer la cobertura total de la suite por debajo
del umbral del 85% que exige `.github/workflows/ci.yml`. Estas pruebas
ejercitan las tres cosas que realmente importan de ese módulo:

  1. `_es_puntero_lfs` — la detección de un puntero de Git LFS sin resolver
     (el fallo real que encontramos: `Data/matriz_similitud_cursos.pkl` viaja
     por Git LFS y, sin `git lfs pull`, el archivo en disco es apenas el
     puntero de texto, no la matriz).
  2. `MatrixRecommender._cargar_recursos` — sus tres desenlaces: archivos
     ausentes, puntero de LFS sin resolver, y carga exitosa.
  3. `MatrixRecommender.recomendar` — orden por similitud, exclusión del
     propio curso, y los casos sin datos (matriz no cargada, índice fuera de
     rango).

Usa archivos temporales (`tmp_path` + `monkeypatch`) en vez de la matriz real
de 190 MB: son las mismas rutas (`MODEL_PATH`/`MAPEO_PATH`) que
`matrix_recommender.py` resuelve como constantes de módulo, así que
monkeypatchearlas alcanza sin tocar el archivo real ni pagar su costo de
carga en cada test.
"""

from __future__ import annotations

import json

import joblib
import numpy as np
import pytest

from app.ml import matrix_recommender as mr


# ===========================================================================
# 1. Deteccion de puntero de Git LFS
# ===========================================================================


class TestEsPunteroLfs:
    def test_detecta_puntero_de_lfs(self, tmp_path):
        ruta = tmp_path / "puntero.pkl"
        ruta.write_bytes(
            b"version https://git-lfs.github.com/spec/v1\n"
            b"oid sha256:fdbf436ac2019e475a5ea38cd34a16f932eb1e2fb99a512e1baeeec991e91047\n"
            b"size 199280889\n"
        )
        assert mr._es_puntero_lfs(str(ruta)) is True

    def test_no_confunde_un_pickle_real_con_un_puntero(self, tmp_path):
        ruta = tmp_path / "real.pkl"
        joblib.dump(np.eye(3), str(ruta))
        assert mr._es_puntero_lfs(str(ruta)) is False

    def test_archivo_inexistente_no_es_puntero(self, tmp_path):
        assert mr._es_puntero_lfs(str(tmp_path / "no_existe.pkl")) is False


# ===========================================================================
# 2. Carga de recursos (los tres desenlaces de _cargar_recursos)
# ===========================================================================


class TestCargaDeRecursos:
    def test_archivos_ausentes_deja_matriz_en_none_con_motivo(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mr, "MODEL_PATH", str(tmp_path / "no_existe.pkl"))
        monkeypatch.setattr(mr, "MAPEO_PATH", str(tmp_path / "no_existe.json"))

        recomendador = mr.MatrixRecommender()

        assert recomendador.matriz_similitud is None
        assert recomendador.ultimo_error is not None
        assert "no encontrados" in recomendador.ultimo_error.lower()

        diagnostico = recomendador.diagnostico()
        assert diagnostico["disponible"] is False
        assert diagnostico["total_cursos"] is None
        assert diagnostico["motivo"] == recomendador.ultimo_error

    def test_puntero_de_lfs_sin_resolver_da_motivo_accionable(self, tmp_path, monkeypatch):
        modelo = tmp_path / "matriz_similitud_cursos.pkl"
        modelo.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:x\nsize 1\n")
        mapeo = tmp_path / "mapeo_cursos.json"
        mapeo.write_text("{}", encoding="utf-8")

        monkeypatch.setattr(mr, "MODEL_PATH", str(modelo))
        monkeypatch.setattr(mr, "MAPEO_PATH", str(mapeo))

        recomendador = mr.MatrixRecommender()

        assert recomendador.matriz_similitud is None
        assert "git lfs pull" in recomendador.ultimo_error
        assert recomendador.diagnostico()["disponible"] is False

    def test_pickle_corrupto_no_lanza_y_registra_el_motivo(self, tmp_path, monkeypatch):
        # Ni vacio ni puntero de LFS, pero tampoco un pickle valido: el
        # `except Exception` de `_cargar_recursos` debe atraparlo sin tumbar
        # el proceso, igual que si faltara el archivo.
        modelo = tmp_path / "matriz_similitud_cursos.pkl"
        modelo.write_bytes(b"esto no es un pickle valido")
        mapeo = tmp_path / "mapeo_cursos.json"
        mapeo.write_text("{}", encoding="utf-8")

        monkeypatch.setattr(mr, "MODEL_PATH", str(modelo))
        monkeypatch.setattr(mr, "MAPEO_PATH", str(mapeo))

        recomendador = mr.MatrixRecommender()

        assert recomendador.matriz_similitud is None
        assert recomendador.ultimo_error is not None
        assert recomendador.recomendar(curso_idx=0) == []

    def test_carga_exitosa_deja_todo_listo(self, tmp_path, monkeypatch):
        matriz = np.array([[1.0, 0.9, 0.1], [0.9, 1.0, 0.2], [0.1, 0.2, 1.0]])
        modelo = tmp_path / "matriz_similitud_cursos.pkl"
        joblib.dump(matriz, str(modelo))
        mapeo = tmp_path / "mapeo_cursos.json"
        mapeo.write_text(
            json.dumps(
                {
                    "0": {"titulo": "Curso A", "categoria": "IA", "proveedor": "Coursera", "tags": ["python"]},
                    "1": {"titulo": "Curso B", "categoria": "IA", "proveedor": "Coursera", "tags": []},
                    "2": {"titulo": "Curso C", "categoria": "Cloud", "proveedor": "Udemy", "tags": []},
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(mr, "MODEL_PATH", str(modelo))
        monkeypatch.setattr(mr, "MAPEO_PATH", str(mapeo))

        recomendador = mr.MatrixRecommender()

        assert recomendador.ultimo_error is None
        diagnostico = recomendador.diagnostico()
        assert diagnostico["disponible"] is True
        assert diagnostico["total_cursos"] == 3


# ===========================================================================
# 3. Recomendaciones: orden, exclusion propia, y casos sin datos
# ===========================================================================


@pytest.fixture
def recomendador_con_datos(tmp_path, monkeypatch):
    """Un `MatrixRecommender` con una matriz y mapeo de prueba conocidos."""
    matriz = np.array(
        [
            [1.0, 0.9, 0.1, 0.05],
            [0.9, 1.0, 0.2, 0.10],
            [0.1, 0.2, 1.0, 0.80],
            [0.05, 0.10, 0.80, 1.0],
        ]
    )
    modelo = tmp_path / "matriz_similitud_cursos.pkl"
    joblib.dump(matriz, str(modelo))
    mapeo = tmp_path / "mapeo_cursos.json"
    mapeo.write_text(
        json.dumps(
            {
                "0": {"titulo": "Curso A", "categoria": "IA", "proveedor": "Coursera", "tags": ["python"]},
                "1": {"titulo": "Curso B", "categoria": "IA", "proveedor": "Coursera", "tags": []},
                "2": {"titulo": "Curso C", "categoria": "Cloud", "proveedor": "Udemy", "tags": []},
                # A proposito sin "3": ejercita el respaldo `mapeo_cursos.get(idx, {})`.
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(mr, "MODEL_PATH", str(modelo))
    monkeypatch.setattr(mr, "MAPEO_PATH", str(mapeo))
    return mr.MatrixRecommender()


class TestRecomendar:
    def test_ordena_por_similitud_de_mas_a_menos_afin(self, recomendador_con_datos):
        resultados = recomendador_con_datos.recomendar(curso_idx=0, top_n=3)

        assert [r["id"] for r in resultados] == [1, 2, 3]
        assert resultados[0]["titulo"] == "Curso B"
        assert resultados[0]["match_score"] == 90
        assert resultados[0]["categoria"] == "IA"
        assert resultados[0]["tags"] == []

    def test_nunca_recomienda_el_propio_curso(self, recomendador_con_datos):
        resultados = recomendador_con_datos.recomendar(curso_idx=0, top_n=10)
        assert 0 not in [r["id"] for r in resultados]

    def test_respeta_el_top_n(self, recomendador_con_datos):
        resultados = recomendador_con_datos.recomendar(curso_idx=0, top_n=1)
        assert len(resultados) == 1
        assert resultados[0]["id"] == 1

    def test_curso_sin_entrada_en_el_mapeo_usa_valores_por_defecto(self, recomendador_con_datos):
        # El curso 3 (mas afin al 2) no tiene entrada en el mapeo de prueba.
        resultados = recomendador_con_datos.recomendar(curso_idx=2, top_n=1)
        assert resultados[0]["id"] == 3
        assert resultados[0]["titulo"] == "Curso 3"
        assert resultados[0]["categoria"] == "Desarrollo y Tecnología"
        assert resultados[0]["proveedor"] == "Plataforma"

    def test_curso_idx_fuera_de_rango_devuelve_vacio(self, recomendador_con_datos):
        assert recomendador_con_datos.recomendar(curso_idx=999, top_n=3) == []

    def test_sin_matriz_cargada_devuelve_vacio_sin_lanzar(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mr, "MODEL_PATH", str(tmp_path / "no_existe.pkl"))
        monkeypatch.setattr(mr, "MAPEO_PATH", str(tmp_path / "no_existe.json"))

        recomendador = mr.MatrixRecommender()
        assert recomendador.recomendar(curso_idx=0, top_n=3) == []


# ===========================================================================
# 4. El singleton del modulo (evita el bug de instanciar por peticion)
# ===========================================================================


def test_el_modulo_expone_un_singleton_reutilizable():
    """
    `recomendador_matriz` debe ser LA instancia que usan las rutas
    (`routers/cursos.py`, `main.py`) — no algo que cada una reconstruya. La
    version original instanciaba `MatrixRecommender()` en cada peticion, lo
    que deserializaba los ~190 MB de la matriz real con `joblib.load()` en
    cada request.
    """
    assert isinstance(mr.recomendador_matriz, mr.MatrixRecommender)
