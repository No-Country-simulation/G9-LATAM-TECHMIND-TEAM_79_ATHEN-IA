"""
Suite de pruebas de QA - Deteccion y versionado del artefacto de IA
====================================================================

Semana 5. Fija el comportamiento de `ml/carga.py` cuando Data Science entrega
una version nueva del modelo.

    CP-400 .. CP-406   Seleccion del artefacto (que gana y por que)
    CP-410 .. CP-412   Integracion: el motor activo refleja el artefacto nuevo

Contexto del cambio
-------------------
Hasta la Semana 5, `localizar_modelo()` recorria una lista de nombres conocidos
y tomaba el primero que existiera. Si Data Science dejaba
`clasificador_v2.pkl` junto al anterior, el nuevo **quedaba ignorado en
silencio**: la API seguia sirviendo el viejo sin ningun aviso. Ahora gana el
mas reciente por fecha de modificacion, y los nombres conocidos solo desempatan.

Ejecutar solo esta suite:

    pytest backend/tests/test_versionado_modelo.py -v
"""

import os
import time

import pytest

from app.config import settings
from app.ml import carga


@pytest.fixture
def carpeta_modelos(tmp_path, monkeypatch):
    """
    Carpeta de modelos aislada, apuntada por la configuracion.

    `MODELO_PATH` se anula para forzar la autodeteccion, que es justamente lo
    que estas pruebas ejercitan.
    """
    directorio = tmp_path / "models"
    directorio.mkdir()

    monkeypatch.setattr(settings, "MODELOS_DIR", directorio)
    monkeypatch.setattr(settings, "MODELO_PATH", None)
    return directorio


def crear_artefacto(directorio, nombre, antiguedad_segundos=0.0):
    """
    Crea un archivo de artefacto con una marca temporal controlada.

    `antiguedad_segundos` retrasa el mtime hacia el pasado, para poder ordenar
    los artefactos sin depender de la resolucion del reloj del sistema de
    archivos (en Windows puede ser de ~15 ms).
    """
    ruta = directorio / nombre
    ruta.write_bytes(b"artefacto de prueba")

    if antiguedad_segundos:
        momento = time.time() - antiguedad_segundos
        os.utime(ruta, (momento, momento))

    return ruta


# ===========================================================================
# CP-400 .. CP-406  |  Seleccion del artefacto
# ===========================================================================


def test_sin_artefactos_no_hay_modelo(carpeta_modelos):
    """CP-400: carpeta vacia -> `None`, que activa el fallback por reglas."""
    assert carga.localizar_modelo() is None
    assert carga.artefactos_disponibles() == []


def test_un_solo_artefacto_se_elige(carpeta_modelos):
    """CP-401: con un unico modelo se carga ese, sin ambiguedad."""
    crear_artefacto(carpeta_modelos, "clasificador_cursos.pkl")

    elegido = carga.localizar_modelo()

    assert elegido is not None
    assert elegido.name == "clasificador_cursos.pkl"


def test_gana_el_artefacto_mas_reciente(carpeta_modelos):
    """
    CP-402: el escenario que motivo el cambio.

    Data Science deja `clasificador_v2.pkl` junto al anterior. Antes ganaba el
    nombre conocido y la actualizacion pasaba desapercibida; ahora gana la
    version nueva.
    """
    crear_artefacto(carpeta_modelos, "clasificador_cursos.pkl", antiguedad_segundos=60)
    crear_artefacto(carpeta_modelos, "clasificador_v2.pkl")

    assert carga.localizar_modelo().name == "clasificador_v2.pkl"


def test_un_artefacto_viejo_no_desplaza_al_actual(carpeta_modelos):
    """
    CP-403: la simetria del caso anterior.

    Dejar un modelo antiguo en la carpeta (por ejemplo, un respaldo) no debe
    hacer que la API retroceda de version.
    """
    crear_artefacto(carpeta_modelos, "modelo_viejo_2024.pkl", antiguedad_segundos=3600)
    crear_artefacto(carpeta_modelos, "clasificador_cursos.pkl")

    assert carga.localizar_modelo().name == "clasificador_cursos.pkl"


def test_empate_de_fecha_se_resuelve_por_nombre_conocido(carpeta_modelos):
    """
    CP-404: con la misma marca temporal gana el nombre acordado.

    Es el caso real tras un `git clone` o un `docker build`, donde todos los
    archivos quedan con un mtime practicamente identico. Sin desempate, la
    eleccion dependeria del orden del sistema de archivos.
    """
    momento = time.time() - 10

    for nombre in ("zzz_experimento.pkl", "clasificador_cursos.pkl", "aaa_borrador.pkl"):
        ruta = crear_artefacto(carpeta_modelos, nombre)
        os.utime(ruta, (momento, momento))

    assert carga.localizar_modelo().name == "clasificador_cursos.pkl"


def test_la_seleccion_es_determinista(carpeta_modelos):
    """CP-405: repetir la busqueda devuelve siempre el mismo artefacto."""
    momento = time.time() - 10
    for nombre in ("a.pkl", "b.pkl", "c.joblib"):
        os.utime(crear_artefacto(carpeta_modelos, nombre), (momento, momento))

    elegidos = {carga.localizar_modelo().name for _ in range(5)}

    assert len(elegidos) == 1


def test_detecta_joblib_ademas_de_pkl(carpeta_modelos):
    """CP-406: ambas extensiones cuentan como artefacto."""
    crear_artefacto(carpeta_modelos, "clasificador_cursos.pkl", antiguedad_segundos=60)
    crear_artefacto(carpeta_modelos, "modelo_nuevo.joblib")

    disponibles = carga.artefactos_disponibles()

    assert len(disponibles) == 2
    assert disponibles[0].name == "modelo_nuevo.joblib"


def test_ruta_explicita_tiene_prioridad_sobre_la_fecha(carpeta_modelos, monkeypatch):
    """
    CP-407: `ATHENIA_MODELO_PATH` manda por encima de la autodeteccion.

    Permite fijar una version concreta en produccion aunque haya otras mas
    recientes en la carpeta.
    """
    antiguo = crear_artefacto(carpeta_modelos, "clasificador_cursos.pkl", antiguedad_segundos=60)
    crear_artefacto(carpeta_modelos, "clasificador_v2.pkl")

    monkeypatch.setattr(settings, "MODELO_PATH", antiguo)

    assert carga.localizar_modelo().name == "clasificador_cursos.pkl"


# ===========================================================================
# CP-410 .. CP-412  |  Integracion con el motor activo
# ===========================================================================


def test_version_nueva_se_activa_al_recargar(
    client, activar_artefacto, constructor_pipeline, tmp_path
):
    """
    CP-410: dejar un artefacto mas reciente y recargar cambia el motor activo.

    Es el flujo completo que seguira Data Science: copiar el `.pkl` nuevo y
    reiniciar (o llamar a `recargar_clasificador`).
    """
    carpeta = tmp_path / "models"

    # Version inicial.
    ruta_v1 = carpeta / "clasificador_cursos.pkl"
    activar_artefacto(constructor_pipeline(), ruta_v1, autodetectar=True)
    assert client.get("/salud").json()["modelo_cargado"] == "clasificador_cursos.pkl"

    # Envejece la v1 para que la v2 sea inequivocamente mas nueva.
    momento = time.time() - 120
    os.utime(ruta_v1, (momento, momento))

    # Data Science entrega la v2.
    activar_artefacto(constructor_pipeline(), carpeta / "clasificador_v2.pkl", autodetectar=True)

    cuerpo = client.get("/salud").json()
    assert cuerpo["modelo_cargado"] == "clasificador_v2.pkl"
    assert cuerpo["motor"] == "modelo_ml_real"


def test_el_contrato_no_cambia_al_actualizar_el_modelo(
    client, activar_artefacto, constructor_pipeline, tmp_path
):
    """
    CP-411: cambiar de version no altera el esquema de respuesta.

    Incluye `nivel_confianza`, que es el campo mas reciente y el que mas
    facilmente se rompe al tocar la capa de carga.
    """
    activar_artefacto(
        constructor_pipeline(), tmp_path / "models" / "clasificador_v2.pkl", autodetectar=True
    )

    cuerpo = client.post(
        "/contenido",
        json={"titulo": "Curso de Docker", "texto": "Contenedores, Kubernetes y CI/CD."},
    ).json()

    for campo in ("categoria", "probabilidad", "informacion_adicional", "nivel_confianza"):
        assert campo in cuerpo, f"falta {campo} tras actualizar el modelo"

    assert cuerpo["modelo"] == "clasificador_v2.pkl"
    assert cuerpo["nivel_confianza"] in {"alta", "media", "baja"}


def test_artefacto_nuevo_corrupto_no_tumba_la_api(client, carpeta_modelos):
    """
    CP-412: una entrega defectuosa degrada a reglas, no rompe la demo.

    Si Data Science sube un `.pkl` corrupto mas reciente que el bueno, la API
    debe seguir respondiendo — con el fallback, pero respondiendo.
    """
    from app import services

    crear_artefacto(carpeta_modelos, "clasificador_v3_corrupto.pkl")
    services.recargar_clasificador()

    cuerpo = client.get("/salud").json()
    assert cuerpo["motor"] == "clasificador_reglas"

    respuesta = client.post(
        "/contenido",
        json={"titulo": "Curso de Docker", "texto": "Contenedores y Dockerfile."},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nivel_confianza"] in {"alta", "media", "baja"}
