# G9-LATAM-TECHMIND-TEAM_79_ATHEN-IA
## Herramienta inteligente para clasificar, organizar y consultar contenidos técnicos. MVP desarrollado con Data Science, API REST y servicios de nube; para el Hackathon ONE - G9 (Alura + Oracle).
## Descripción del Proyecto
Utilizando técnicas avanzadas de **Ciencia de Datos** y procesamiento de lenguaje, la plataforma procesa textos técnicos para catalogarlos de forma automática. De esta manera, reducimos drásticamente el esfuerzo manual de estructuración y facilitamos la búsqueda temática del conocimiento.
Toda la solución está expuesta mediante una **API REST** que se integra con servicios en la nube de **Oracle Cloud Infrastructure (OCI)**.
---
## Tecnologías y Arquitectura Sugeridas
*   **Ciencia de Datos**: Python, Jupyter Notebook / Google Colab, Pandas, Scikit-Learn, TF-IDF, Modelos de Clasificación.
*   **Back-End**: API REST utilizando Python para un consumo directo y fluido del modelo entrenado.
*   **Cloud & Infraestructura (OCI)**. 
---

## Cuerpo del proyecto

En la búsqueda de un estándar de desarrollo limpio, escalable y facilitar la colaboración, el repositorio se estructura como sigue:

```text
G9-LATAM-TECHMIND-TEAM_79_ATHEN-IA/
├── backend/                  # Código fuente de la API REST y lógica de negocio:
				#es donde recibe ese texto, se lo pasa al modelo de Inteligencia Artificial para que lo analice y le devuelve la respuesta a la pantalla en formato JSON (un 				formato de texto liviano y organizado).
│   ├── app/                  # Núcleo de la aplicación FastAPI
				#El "Núcleo de la aplicación FastAPI" es la carpeta donde juntamos la entrada de datos (main.py), la validación (schemas.py) y el procesamiento inteligente 				(services.py) para convertir solicitudes web en respuestas JSON estructuradas.
│   │   ├── __init__.py       # Inicializador del paquete Python
│   │   ├── config.py         # Variables de entorno y configuración (OCI, rutas)
│   │   ├── main.py           # Punto de entrada de la API REST (Endpoints)
│   │   ├── schemas.py        # Modelos de Pydantic (Validación de entrada y salida JSON) Pydantic es una librería de Python que se encarga de validar que los datos que entran o salen de 				la API tengan la estructura y el tipo correcto.
│   │   └── services.py       # Lógica del modelo ML, extracción semántica y fallback (Si el código detecta que el modelo de IA no cargó o falló, se activa el servicio de reserva, 						continuidad de la herramienta)
│   ├── models/               # Artefactos del modelo entrenado (el equipo de Data entrega el modelo para conectar al Back End y así hacer las predicciones y clasificaciones respectivas).
│   │   └── .gitkeep          # Carpeta destinada al archivo classifier.joblib
│   ├── tests/                # Suite de QA y Pruebas Automatizadas
│   │   ├── __init__.py
│   │   └── test_api.py       # Pruebas unitarias e integración con Pytest (escribimos un script en Python que prueba nuestro código automáticamente en cuestión de segundos cada vez que 					hacemos un cambio.QA TESTER)
│   ├── Dockerfile            # Configuración para contenedorización y despliegue en OCI
│   └── requirements.txt      # Dependencias y librerías del backend
├── notebooks/                # Espacio de trabajo para el equipo de Data Science
│   └── EDA_Model_Training.ipynb # Cuaderno de análisis (EDA, entrenamiento y exportación .joblib)
└── README.md                 # Documentación general del proyecto.