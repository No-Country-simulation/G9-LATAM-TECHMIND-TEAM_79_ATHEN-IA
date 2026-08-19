# =============================================================================
# AthenIA - Backend (FastAPI)
# Imagen optimizada para despliegue en Oracle Cloud Infrastructure (OCI).
#
# Construir (desde backend/):
#   docker build -t athenia-backend:latest .
#
# Ejecutar:
#   docker run -p 8000:8000 --name athenia-api athenia-backend:latest
#
# Con modelo entrenado montado desde el host:
#   docker run -p 8000:8000 -v "$(pwd)/models:/app/models:ro" athenia-backend:latest
# =============================================================================

# -----------------------------------------------------------------------------
# Etapa 1 — builder: compila las dependencias en un venv aislado.
# Separar la compilacion evita arrastrar toolchains a la imagen final.
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# gcc solo se necesita si alguna rueda no trae binario precompilado.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc \
 && rm -rf /var/lib/apt/lists/*

# Capa cacheable: solo se reconstruye si cambian las dependencias.
COPY requirements.txt .

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 # torch se instala primero desde el indice CPU-only. `sentence-transformers`
 # lo arrastra por defecto en su variante CUDA (~2,5 GB de binarios de GPU),
 # inutil en una VM de OCI sin GPU. Esto deja la imagen ~2 GB mas ligera.
 && /opt/venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && /opt/venv/bin/pip install -r requirements.txt

# Modelo de embeddings horneado en la imagen.
# ------------------------------------------
# `sentence-transformers` descarga el modelo de HuggingFace la PRIMERA vez que
# se usa. Sin este paso, en produccion pasa una de dos:
#   - la primera busqueda tarda ~30 s mientras baja ~470 MB, o
#   - si la VM de OCI no tiene salida a internet, el modelo nunca carga y
#     `/cursos/buscar` responde 200 con lista vacia para siempre.
# Descargarlo en build lo convierte en una capa cacheada e inmutable.
ENV SENTENCE_TRANSFORMERS_HOME=/opt/modelos
RUN /opt/venv/bin/python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# -----------------------------------------------------------------------------
# Etapa 2 — runtime: solo el venv y el codigo de la aplicacion.
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="AthenIA API" \
      org.opencontainers.image.description="Clasificacion inteligente de contenido tecnico" \
      org.opencontainers.image.vendor="Equipo AthenIA - Hackathon ONE Alura + Oracle"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    SENTENCE_TRANSFORMERS_HOME=/opt/modelos \
    ATHENIA_ENV=production \
    ATHENIA_HOST=0.0.0.0 \
    ATHENIA_PORT=8000

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
# Modelo de embeddings pre-descargado en la etapa builder (ver arriba).
COPY --from=builder /opt/modelos /opt/modelos

# Se copia solo lo que la API necesita en runtime (ver .dockerignore).
# Incluye `app/data/vector_db/` — el indice vectorial de cursos viaja horneado,
# igual que el .pkl del clasificador. Si algun dia se excluye en el
# .dockerignore, `/cursos/buscar` respondera 200 con lista vacia sin error
# visible: el mismo modo de fallo silencioso que ya documenta models/.
COPY app ./app
COPY models ./models

# Usuario sin privilegios: requisito de las politicas de seguridad de OCI.
RUN useradd --create-home --shell /usr/sbin/nologin athenia \
 && chown -R athenia:athenia /app
USER athenia

EXPOSE 8000

# El health check usa el mismo endpoint que consume QA.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
