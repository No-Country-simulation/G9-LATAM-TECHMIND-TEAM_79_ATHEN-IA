"""
Motores de clasificacion de AthenIA.
=====================================

Cada motor "conectable" (que puede o no estar disponible) vive en su propio
modulo y se anuncia aqui registrando un proveedor en `ml.registro`. El
clasificador por reglas NO se registra como proveedor: es la unica pieza que
`registro.resolver()` garantiza construir siempre, sin condiciones, como piso
de la cascada de fallback (ver `ml/registro.py::resolver()`).

Agregar un motor nuevo en la Semana 4 (embeddings, LLM, ensemble)
-------------------------------------------------------------------
1. Crear `ml/mi_motor_nuevo.py` con una clase que cumpla `domain.protocols.Clasificador`
   y una funcion `cargar() -> Optional[Clasificador]` que la instancie, o
   devuelva `None` si el motor no esta disponible (sin artefacto, dependencia
   ausente, etc.).
2. Registrarlo aqui abajo con `registro.registrar(...)` y una prioridad.
3. Nada mas cambia: ni `ml/modelo.py`, ni las rutas, ni `services.py`.

Eso es el Open/Closed Principle en la practica: el paquete esta **cerrado** a
modificacion (ninguna clase existente se toca) y **abierto** a extension (un
archivo y una linea de registro nuevos).
"""

from . import carga
from .registro import registro

# Unico proveedor "conectable" hoy: el artefacto entrenado por Data Science.
# Prioridad baja = se intenta primero. Cuando llegue el motor de la Semana 4,
# se suma una segunda linea aqui con su propia prioridad; esta no se toca.
registro.registrar("modelo-ml", carga.cargar_modelo_entrenado, prioridad=10)

__all__ = ["registro"]
