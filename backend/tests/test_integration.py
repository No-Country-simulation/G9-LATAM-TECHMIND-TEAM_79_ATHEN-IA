import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ===========================================================================
# Propuesta 2: Pruebas de Integración y Flujo E2E (End-to-End)
# ===========================================================================

def test_e2e_flujo_clasificacion_y_persistencia_en_historial():
    """
    Prueba E2E: Verifica el flujo completo desde que se publica un contenido,
    se procesa la respuesta JSON y se confirma su guardado en el historial (/contenidos).
    """
    payload = {
        "titulo": "Curso Intensivo de FastApi y Python",
        "texto": "Desarrollo de APIs RESTful asincrónicas con validaciones Pydantic y pruebas unitarias."
    }
    
    # 1. Enviar el contenido a clasificar
    respuesta_post = client.post("/contenido", json=payload)
    assert respuesta_post.status_code == 200
    
    data_post = respuesta_post.json()
    assert "categoria" in data_post
    assert "probabilidad" in data_post
    
    # 2. Consultar el historial para confirmar persistencia de la operación E2E
    respuesta_get = client.get("/contenidos")
    assert respuesta_get.status_code == 200
    
    data_get = respuesta_get.json()
    assert data_get["total"] >= 1
    
    # Validar que el último elemento coincida con el título enviado
    titulos = [item["titulo"] for item in data_get["items"]]
    assert payload["titulo"] in titulos


def test_e2e_validacion_payload_invalido_devuelve_422():
    """
    Prueba de Integración: Verifica que ante una estructura incompleta
    la API responda con el esquema estandarizado de error de validación (422).
    """
    payload_invalido = {
        "titulo": "Solo un título sin el campo texto obligatorio"
    }
    
    respuesta = client.post("/contenido", json=payload_invalido)
    
    assert respuesta.status_code == 422
    data = respuesta.json()
    assert "detail" in data or "error" in data