"""
Asistente conversacional de AthenIA.
=====================================

Responde preguntas en lenguaje natural sobre el catalogo de cursos
combinando dos piezas que ya existian por separado:

    busqueda/servicio.py   Recupera cursos REALES por afinidad semantica
                           (el mismo motor de `GET /cursos/buscar`).
    asistente/servicio.py  Le pasa esos cursos como contexto a un
                           `ModeloLenguaje` (`domain.protocols.ModeloLenguaje`)
                           para que redacte la respuesta, citando solo lo
                           que el buscador confirmo que existe.

Es el patron RAG (Retrieval-Augmented Generation): el modelo de lenguaje
nunca inventa un curso, porque el contexto que recibe ya viene filtrado
contra el catalogo real. `asistente/motor_openai.py` es la unica pieza que
sabe que el proveedor es OpenAI; todo lo demas depende del `Protocol`.
"""
