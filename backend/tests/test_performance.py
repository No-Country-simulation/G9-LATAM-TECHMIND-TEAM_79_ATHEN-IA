import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ===========================================================================
# Propuesta 3: Pruebas de Carga, Latencia y Rendimiento (Performance Testing)
# ===========================================================================

def test_performance_latencia_endpoint_salud():
    """
    Verifica que el endpoint de estado/salud responda en un tiempo
    inferior a 50 milisegundos (SLA estricto para monitoreo en OCI).
    """
    inicio = time.perf_counter()
    respuesta = client.get("/salud")
    fin = time.perf_counter()
    
    tiempo_ejecucion_ms = (fin - inicio) * 1000
    
    assert respuesta.status_code == 200
    # La verificación de salud debe ser casi instantánea
    assert tiempo_ejecucion_ms < 50, f"Latencia alta en /salud: {tiempo_ejecucion_ms:.2f}ms"


def test_performance_tiempo_respuesta_inferencia_clasificacion():
    """
    Mide el tiempo de inferencia del clasificador al procesar un payload completo.
    Garantiza que el procesamiento + clasificación tome menos de 300 ms.
    """
    payload = {
        "titulo": "Curso Avanzado de Arquitectura de Software en la Nube",
        "texto": "Aprende patrones microservicios, SOLID, Docker, Kubernetes y despliegue continuo en Oracle Cloud OCI."
    }
    
    inicio = time.perf_counter()
    respuesta = client.post("/contenido", json=payload)
    fin = time.perf_counter()
    
    latencia_ms = (fin - inicio) * 1000
    
    assert respuesta.status_code == 200
    # Umbral de tiempo para inferencia local / preparación para OCI
    assert latencia_ms < 300, f"Tiempo de respuesta excedido: {latencia_ms:.2f}ms"


def test_performance_carga_simultanea_volumen_medico():
    """
    Simula una ráfaga secuencial/concurrente de 30 solicitudes de clasificación
    para evaluar si el backend degrada memoria o velocidad de procesamiento.
    """
    payload_base = {
        "titulo": "Prueba de Estrés de Clasificación #",
        "texto": "Texto de prueba de carga simulando múltiples peticiones consecutivas al motor de ML."
    }
    
    tiempos = []
    
    for i in range(30):
        payload = payload_base.copy()
        payload["titulo"] = f"{payload_base['titulo']}{i}"
        
        inicio = time.perf_counter()
        res = client.post("/contenido", json=payload)
        fin = time.perf_counter()
        
        assert res.status_code == 200
        tiempos.append((fin - inicio) * 1000)
    
    promedio_ms = sum(tiempos) / len(tiempos)
    maximo_ms = max(tiempos)
    
    # Criterios de aceptación de carga
    assert promedio_ms < 150, f"Promedio de respuesta muy alto en carga: {promedio_ms:.2f}ms"
    assert maximo_ms < 400, f"Pico de latencia inaceptable: {maximo_ms:.2f}ms"