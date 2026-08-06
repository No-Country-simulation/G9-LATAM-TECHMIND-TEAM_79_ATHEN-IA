"""
AthenIA - Backend API
=====================
Organizacion Inteligente del Conocimiento Tecnico.

Paquete de la aplicacion FastAPI. Capas:

    config.py    Configuracion por variables de entorno (CORS, OCI, modelo).
    schemas.py   Contratos de datos Pydantic (Request / Response).
    services.py  Logica de negocio: clasificacion, keywords y persistencia.
    main.py      Rutas HTTP y middleware.
"""

__version__ = "0.4.0"
