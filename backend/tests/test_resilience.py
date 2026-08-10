"""
Suite de pruebas automatizadas de QA - Propuesta 4: Resiliencia y Casos Borde
=============================================================================

Garantiza la estabilidad del sistema frente a entradas extremas, caracteres
especiales, payloads masivos y degradación controlada de servicios.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ===========================================================================
# Propuesta 4: Pruebas de Resiliencia, Robustez y Casos Borde
# ===========================================================================


def test_resiliencia_texto_extremadamente_largo():
    """
    Verifica que la API procese o valide correctamente un payload con un texto
    masivo (ej. un libro o artículo de 100,000+ caracteres) sin colapsar por memoria.
    """
    texto_gigante = "Desarrollo de software con Python, FastApi y Docker. " * 3000  # ~150k caracteres
    
    payload = {
        "titulo": "Prueba de Carga de Texto Gigante",
        "texto": texto_gigante
    }
    
    respuesta = client.post("/contenido", json=payload)
    
    # La API debe procesarlo con éxito o rechazarlo de forma controlada, pero NUNCA lanzar 500
    assert respuesta.status_code in {200, 413, 422}
    if respuesta.status_code == 200:
        assert "categoria" in respuesta.json()


def test_resiliencia_caracteres_especiales_y_emojis():
    """
    Garantiza que la inclusión de Emojis, caracteres Unicode complejos y
    símbolos no rompa el tokenizador o la serialización JSON.
    """
    payload = {
        "titulo": "🚀 Aprendiendo Python & ML 🤖 con @ñandúes y #Cöde!!!",
        "texto": "¡Hola mundo! 🐍🔥 Probando símbolos: <script>alert('xss')</script> ¥€$ %^*()_+"
    }
    
    respuesta = client.post("/contenido", json=payload)
    
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "categoria" in cuerpo
    assert isinstance(cuerpo["categoria"], str)


def test_resiliencia_busqueda_historial_con_inyeccion_o_caracteres_raros():
    """
    Somete los parámetros de búsqueda del historial a caracteres de sanitización
    (SQLi / Scripting simulación) para verificar que la app los maneje de forma segura.
    """
    parametros_extremos = [
        {"buscar": "' OR '1'='1"},
        {"buscar": "<script>"},
        {"buscar": "%; DROP TABLE contenidos;--"},
        {"buscar": "ñÁéÍóÚü#@!"}
    ]
    
    for params in parametros_extremos:
        respuesta = client.get("/contenidos", params=params)
        assert respuesta.status_code == 200
        assert "total" in respuesta.json()


def test_resiliencia_id_inexistente_extremadamente_grande():
    """
    Consulta un ID numérico fuera del rango de enteros común (ej. Overflow ID)
    para asegurar que responda 404 de manera limpia.
    """
    respuesta = client.get("/contenidos/999999999999999999999")
    
    # Debe ser capturado por la validación de Pydantic/FastAPI (422) o no encontrado (404)
    assert respuesta.status_code in {404, 422}