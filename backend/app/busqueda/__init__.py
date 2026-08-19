"""
Busqueda vectorial de cursos.
==============================

Capa que indexa y consulta el catalogo de +8.000 cursos entregado por el
equipo de Data.

    limpieza.py   Saneado del texto antes de vectorizar (dominio puro).
    almacen.py    Implementacion sobre ChromaDB del `AlmacenVectorial`.
    servicio.py   Caso de uso: consultar, filtrar por umbral y formatear.

La ruta HTTP depende del `Protocol` `AlmacenVectorial` (ver
`domain/protocols.py`), no de ChromaDB. Eso permite probar la busqueda sin
levantar la base vectorial ni descargar un modelo de embeddings de 500 MB.
"""
