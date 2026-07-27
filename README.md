<div align="center">

# 🏛️ AthenIA

**Organización Inteligente del Conocimiento Técnico**

Plataforma que recibe contenido técnico, lo clasifica con Inteligencia Artificial,
extrae palabras clave y devuelve métricas en formato JSON.

[![Tests](https://img.shields.io/badge/tests-48%20passed-brightgreen)](docs/QA_TESTING_GUIDE.md)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](backend/)
[![Frontend](https://img.shields.io/badge/frontend-React%2019-61DAFB?logo=react&logoColor=black)](frontend/)
[![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](backend/requirements.txt)
[![Tailwind](https://img.shields.io/badge/styles-Tailwind%20v4-06B6D4?logo=tailwindcss&logoColor=white)](frontend/src/index.css)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](backend/Dockerfile)
[![Status](https://img.shields.io/badge/MVP-Semanas%201--2-8b5cf6)]()

Hackathon **ONE Alura + Oracle** / **No Country** — Generación 9

</div>

---

## 📑 Tabla de contenido

- [Propuesta de valor](#-propuesta-de-valor)
- [Stack tecnológico](#-stack-tecnológico)
- [Arquitectura del repositorio](#-arquitectura-del-repositorio)
- [Requisitos previos](#-requisitos-previos)
- [Instalación paso a paso](#-instalación-paso-a-paso)
- [Ejecutar el proyecto](#-ejecutar-el-proyecto)
- [API — Endpoints](#-api--endpoints)
- [Ejemplos con curl](#-ejemplos-con-curl)
- [Pruebas](#-pruebas)
- [Docker](#-docker)
- [Variables de entorno](#-variables-de-entorno)
- [Integración del modelo de IA](#-integración-del-modelo-de-ia)
- [Roadmap](#-roadmap)

---

## 🎯 Propuesta de valor

AthenIA utiliza Inteligencia Artificial y Ciencia de Datos para **organizar, clasificar
y recomendar contenido técnico**, facilitando el aprendizaje y la gestión del
conocimiento.

El usuario pega el temario de un curso, un artículo o cualquier texto técnico, y AthenIA
responde con:

| Campo | Descripción |
|-------|-------------|
| `categoria` | Área de conocimiento detectada (Backend, Data Science, DevOps…) |
| `probabilidad` | Confianza del modelo, entre `0.0` y `1.0` |
| `informacion_adicional` | Tecnologías y palabras clave encontradas en el texto |

Cada análisis queda guardado en el historial, lo que alimenta el **Dashboard de métricas**
y la vista de **búsqueda en tiempo real**.

---

## 🧰 Stack tecnológico

| Capa | Tecnologías |
|------|-------------|
| **Frontend** | React 19 · Vite 8 · Tailwind CSS v4 · React Router 7 · Axios · Lucide React |
| **Backend** | Python 3.13 · FastAPI · Uvicorn · Pydantic v2 |
| **IA / Data Science** | Scikit-Learn · Pandas · TF-IDF *(integración Semana 3)* |
| **QA** | Pytest · HTTPX · TestClient |
| **Infraestructura** | Docker · Oracle Cloud Infrastructure (OCI) |

---

## 🗂️ Arquitectura del repositorio

```
proyecto-mvp-hakaton/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Variables de entorno, CORS, rutas OCI
│   │   ├── main.py            # Rutas FastAPI y middleware
│   │   ├── schemas.py         # ContenidoInput, AnalisisOutput, ErrorResponse
│   │   └── services.py        # Clasificación, keywords, historial, fallback
│   ├── models/
│   │   ├── .gitkeep           # Aquí llega classifier.joblib (Data Science)
│   │   └── README.md          # Guía de integración del modelo
│   ├── tests/
│   │   ├── conftest.py        # Fixtures compartidas
│   │   └── test_api.py        # 48 casos de prueba
│   ├── Dockerfile             # Imagen multi-stage python:3.13-slim
│   ├── .dockerignore
│   └── requirements.txt
│
├── frontend/
│   ├── public/athenia.svg
│   ├── src/
│   │   ├── components/        # Sidebar, Header, StatCard, ContentForm…
│   │   ├── pages/             # Dashboard, AgregarContenido, BuscarContenidos
│   │   ├── hooks/             # useContenidos, useMetricas
│   │   ├── services/api.js    # Cliente HTTP (único punto que conoce la API)
│   │   ├── data/categorias.js # Colores y helpers de presentación
│   │   ├── App.jsx
│   │   └── index.css          # Tokens de branding (tema oscuro/morado)
│   ├── .env.example
│   └── vite.config.js         # Proxy /api -> localhost:8000
│
├── docs/
│   └── QA_TESTING_GUIDE.md    # Guía completa de pruebas para QA
│
├── scripts/                   # Lanzadores multiplataforma (Windows/macOS/Linux)
├── pytest.ini
└── package.json               # Orquesta backend + frontend con un solo comando
```

---

## ✅ Requisitos previos

| Herramienta | Versión mínima | Verificar |
|-------------|----------------|-----------|
| Node.js | 20+ | `node -v` |
| npm | 10+ | `npm -v` |
| Python | 3.11+ (probado en 3.13) | `python --version` |

---

## 📦 Instalación paso a paso

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
```

### 2. Crear el entorno virtual de Python

En **Windows (PowerShell)**:

```bash
python -m venv .venv
```

En **macOS / Linux**:

```bash
python3 -m venv .venv
```

### 3. Instalar las dependencias del backend

Windows:

```bash
.venv\Scripts\python -m pip install -r backend/requirements.txt
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

### 4. Instalar las dependencias de Node

```bash
npm run install:all
```

> Instala `concurrently` en la raíz y todas las dependencias de `frontend/`.

---

## 🚀 Ejecutar el proyecto

### Opción A — Backend y Frontend a la vez (recomendada)

Desde la **raíz del repositorio**:

```bash
npm run dev
```

Esto levanta ambos servicios en la misma terminal, con salida etiquetada
`[BACKEND]` y `[FRONTEND]`:

| Servicio | URL |
|----------|-----|
| Frontend (Vite) | http://localhost:5173 |
| Backend (FastAPI) | http://localhost:8000 |
| Documentación Swagger | http://localhost:8000/docs |
| Documentación ReDoc | http://localhost:8000/redoc |

Detener ambos: `Ctrl + C`.

### Opción B — Terminales separadas

**Terminal 1 — Backend:**

```bash
npm run dev:backend
```

**Terminal 2 — Frontend:**

```bash
npm run dev:frontend
```

### Opción C — Comandos nativos (sin npm)

**Backend** (desde `backend/`, con el entorno virtual activado):

```bash
uvicorn app.main:app --reload --port 8000
```

**Frontend** (desde `frontend/`):

```bash
npm run dev
```

### Scripts disponibles

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Backend + Frontend simultáneamente |
| `npm run dev:backend` | Solo la API FastAPI |
| `npm run dev:frontend` | Solo la aplicación React |
| `npm test` | Suite de pruebas Pytest |
| `npm run build` | Build de producción del frontend |
| `npm run install:all` | Instala dependencias de Node en raíz y frontend |

---

## 🔌 API — Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Información de la API y endpoints disponibles |
| `GET` | `/salud` | **Health check** para QA y monitoreo de OCI |
| `GET` | `/categorias` | Catálogo de categorías que el modelo reconoce |
| `POST` | `/contenido` | **Contrato del Hackathon** — clasifica contenido técnico |
| `GET` | `/contenidos` | Historial de análisis (filtros: `categoria`, `buscar`, `limite`) |
| `GET` | `/contenidos/{id}` | Detalle de un análisis |
| `DELETE` | `/contenidos` | Vacía el historial (utilidad de QA) |
| `GET` | `/metricas` | Agregados que alimentan el Dashboard |

---

## 🧪 Ejemplos con curl

### `POST /contenido` — clasificar contenido técnico

```bash
curl -X POST http://localhost:8000/contenido -H "Content-Type: application/json" -d "{\"titulo\":\"Introduccion a Spring Boot\",\"texto\":\"En este curso aprenderas a desarrollar APIs REST con Spring Boot, implementando buenas practicas, autenticacion con JWT y conexion a bases de datos con Spring Data JPA.\"}"
```

**Respuesta esperada (200):**

```json
{
  "categoria": "Backend",
  "probabilidad": 0.95,
  "informacion_adicional": ["Spring Boot", "Spring Data JPA", "API REST", "Autenticacion"],
  "id": 9,
  "resumen": "En este curso aprenderas a desarrollar APIs REST con Spring Boot...",
  "categorias_relacionadas": [],
  "modelo": "reglas-keywords-v1"
}
```

### `GET /salud` — verificación de uptime

```bash
curl http://localhost:8000/salud
```

```json
{
  "estado": "ok",
  "version": "0.3.0",
  "entorno": "development",
  "modelo_cargado": "reglas-keywords-v1",
  "es_mock": true,
  "contenidos_en_historial": 8
}
```

### `GET /contenidos` — historial con filtros

```bash
curl "http://localhost:8000/contenidos?buscar=docker&limite=5"
```

```bash
curl "http://localhost:8000/contenidos?categoria=Backend"
```

### `GET /contenidos/{id}` — detalle

```bash
curl http://localhost:8000/contenidos/1
```

### `GET /metricas` — métricas del Dashboard

```bash
curl http://localhost:8000/metricas
```

### Validación — payload incompleto devuelve `422`

```bash
curl -i -X POST http://localhost:8000/contenido -H "Content-Type: application/json" -d "{\"titulo\":\"Solo titulo\"}"
```

```json
{
  "error": "validacion",
  "mensaje": "Los datos enviados no son validos. Revisa que 'titulo' y 'texto' esten presentes y no vacios.",
  "detail": [{ "type": "missing", "loc": ["body", "texto"], "msg": "Field required" }]
}
```

> **Nota para macOS / Linux:** usa comillas simples alrededor del JSON
> (`-d '{"titulo":"..."}'`) en lugar de escapar las comillas dobles.

---

## 🔬 Pruebas

Ejecutar la suite completa desde la raíz:

```bash
npm test
```

O directamente con pytest:

```bash
pytest
```

Filtrar por grupo de casos:

```bash
pytest -k "validacion or historial"
```

**Estado actual: 48 pruebas en verde** — contrato del Hackathon, validaciones,
historial, métricas, CORS y mecanismo de fallback.

📖 Guía detallada para QA: [`docs/QA_TESTING_GUIDE.md`](docs/QA_TESTING_GUIDE.md)

---

## 🐳 Docker

Construir y ejecutar el backend en contenedor:

```bash
docker build -t athenia-backend:latest ./backend
```

```bash
docker run -p 8000:8000 --name athenia-api athenia-backend:latest
```

Con el modelo entrenado montado desde el host:

```bash
docker run -p 8000:8000 -v "$(pwd)/backend/models:/app/models:ro" athenia-backend:latest
```

La imagen usa `python:3.13-slim`, build multi-stage, usuario sin privilegios y un
`HEALTHCHECK` que consulta `/salud`.

---

## ⚙️ Variables de entorno

### Backend

| Variable | Defecto | Descripción |
|----------|---------|-------------|
| `ATHENIA_ENV` | `development` | `development` \| `production` |
| `ATHENIA_LOG_LEVEL` | `INFO` | Nivel de logging |
| `ATHENIA_CORS_ORIGINS` | `*` | Orígenes permitidos, separados por coma |
| `ATHENIA_HOST` | `127.0.0.1` | Host de Uvicorn |
| `ATHENIA_PORT` | `8000` | Puerto de Uvicorn |
| `ATHENIA_MODELO_PATH` | `backend/models/classifier.joblib` | Artefacto entrenado |
| `ATHENIA_SEED_DEMO` | `true` | Precarga contenido de ejemplo al arrancar |
| `ATHENIA_MAX_HISTORIAL` | `500` | Tope de ítems en el historial |
| `ATHENIA_DB_URL` | — | Reservado: Oracle Autonomous DB (Semana 3) |
| `ATHENIA_OCI_BUCKET` | — | Reservado: Object Storage |

### Frontend

Copiar `frontend/.env.example` a `frontend/.env`:

| Variable | Defecto | Descripción |
|----------|---------|-------------|
| `VITE_API_URL` | `/api` (proxy de Vite) | URL del backend en despliegue |

---

## 🤖 Integración del modelo de IA

El backend funciona **hoy** con un clasificador por reglas (`reglas-keywords-v1`), que
sirve de *fallback* permanente.

Para activar el modelo real, el equipo de Data Science solo debe dejar el archivo:

```
backend/models/classifier.joblib
```

y reiniciar el servidor. `app/services.py` lo detecta automáticamente y cambia de
clasificador — **sin tocar rutas, esquemas, frontend ni pruebas**. Verificar con:

```bash
curl http://localhost:8000/salud
```

Debe responder `"es_mock": false`.

Si el archivo no existe, no carga o falla al predecir, la API **sigue respondiendo**
con el clasificador por reglas. La demo nunca se cae por un problema del modelo.

📖 Detalles del contrato: [`backend/models/README.md`](backend/models/README.md)

---

## 🗺️ Roadmap

| Semana | Objetivo | Estado |
|--------|----------|--------|
| 1 | Descubrimiento, arquitectura y plan de trabajo | ✅ |
| 2 | Frontend base + API mock + suite de pruebas | ✅ |
| 3 | Integración del modelo de IA real + Oracle DB | 🔜 |
| 4 | Recomendaciones, dashboard analítico y mejoras UX | 🔜 |
| 5 | Pulido, despliegue en OCI y Demo Day | 🔜 |

---

<div align="center">

**AthenIA** — *"El conocimiento es como un jardín: si no se cultiva, no puede ser cosechado."*

</div>
