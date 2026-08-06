"""
Capa de dominio de AthenIA.
===========================

Contiene las **abstracciones** y las reglas de negocio puras. No conoce
FastAPI, ni scikit-learn, ni la base de datos.

La direccion de las dependencias siempre apunta hacia aqui:

    routers  ->  services  ->  domain  <-  ml
                     |                  <-  repositories
                     +------------------>

Ninguna clase de este paquete importa de `ml/`, `repositories/` o `routers/`.
"""
