<div align="center">

# 🏛️ AthenIA

**Organización Inteligente del Conocimiento Técnico**

Plataforma que recibe contenido técnico, lo clasifica con Inteligencia Artificial,
extrae palabras clave y devuelve métricas en formato JSON.

[![Tests](https://img.shields.io/badge/tests-120%20passed-brightgreen)](docs/QA_TESTING_GUIDE.md)
[![Coverage](https://img.shields.io/badge/coverage-96.72%25-brightgreen)](docs/QA_TESTING_GUIDE.md)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](backend/)
[![Frontend](https://img.shields.io/badge/frontend-React%2019-61DAFB?logo=react&logoColor=black)](frontend/)
[![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](backend/requirements.txt)
[![Scikit-Learn](https://img.shields.io/badge/ML-scikit--learn-F7931E?logo=scikitlearn&logoColor=white)](backend/models/README.md)
[![Tailwind](https://img.shields.io/badge/styles-Tailwind%20v4-06B6D4?logo=tailwindcss&logoColor=white)](frontend/src/index.css)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](backend/Dockerfile)
[![Status](https://img.shields.io/badge/MVP-Semana%205%20·%20Demo%20Day-8b5cf6)]()

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
- [Autenticación y usuarios](#-autenticación-y-usuarios-semana-5)
- [Integración del modelo de IA](#-integración-del-modelo-de-ia)
- [Documentación del proyecto](#-documentación-del-proyecto)
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
| **IA / Data Science** | Scikit-Learn 1.6.1 · TF-IDF + MultinomialNB · joblib |
| **QA** | Pytest · pytest-cov · HTTPX · TestClient · GitHub Actions |
| **Infraestructura** | Docker · Docker Compose · Nginx · Oracle Cloud Infrastructure (OCI) |

---

## 🗂️ Arquitectura del repositorio

```
proyecto-mvp-hakaton/
│
├── backend/                          FastAPI + modelo de IA
│   ├── app/
│   │   ├── main.py                   Composición de la app (119 líneas)
│   │   ├── config.py                 Configuración por variables de entorno
│   │   ├── schemas.py                Contratos Pydantic (Request/Response)
│   │   ├── errors.py                 Manejo uniforme de errores HTTP
│   │   ├── dependencies.py           Proveedores de Depends (inversión de dependencias)
│   │   ├── services.py               Casos de uso + raíz de composición
│   │   ├── recomendador.py           Motor de recomendaciones (Jaccard)
│   │   │
│   │   ├── domain/                   Abstracciones y reglas de negocio puras
│   │   │   ├── protocols.py          Protocol: Clasificador, Repositorio, MotorRecomendaciones
│   │   │   ├── taxonomia.py          Categorías, palabras clave, normalización
│   │   │   └── similitud.py          Índice de Jaccard y puntaje combinado
│   │   │
│   │   ├── ml/                       Motores de clasificación
│   │   │   ├── registro.py           Decide qué motor está activo (extension point)
│   │   │   ├── reglas.py             Clasificador por palabras clave (fallback)
│   │   │   ├── modelo.py             Envoltorio del artefacto entrenado
│   │   │   ├── adaptador.py          Normaliza las 3 formas de entrega del .pkl
│   │   │   └── carga.py              Localizar + deserializar + sondear
│   │   │
│   │   ├── repositories/
│   │   │   └── memoria.py            Historial en memoria (Semana 5+: Oracle DB)
│   │   │
│   │   └── routers/                  Endpoints agrupados por área
│   │       ├── salud.py              GET /, /salud, /categorias
│   │       ├── contenido.py          POST /contenido, historial, recomendaciones
│   │       └── analiticas.py         GET /analiticas
│   │
│   ├── models/
│   │   ├── clasificador_cursos.pkl   Artefacto entrenado (Pipeline TF-IDF + MultinomialNB)
│   │   └── README.md                 Contrato del artefacto para Data Science
│   │
│   ├── tests/                        120 pruebas · 96.72% cobertura
│   │   ├── conftest.py               Fixtures compartidas
│   │   ├── test_api.py               Contrato, reglas de negocio y modelo ML
│   │   ├── test_recomendaciones.py   CP-200…CP-222 (Semana 4)
│   │   ├── test_analiticas.py        CP-230…CP-252 (Semana 4)
│   │   ├── test_integration.py       Flujo E2E
│   │   ├── test_performance.py       Latencia y SLA
│   │   └── test_resilience.py        Casos borde y degradación
│   │
│   ├── Dockerfile                    Multi-stage python:3.13-slim
│   ├── .env.example                  Plantilla de variables de entorno
│   └── requirements.txt
│
├── frontend/                         React 19 + Vite + Tailwind v4
│   ├── src/
│   │   ├── pages/                    Dashboard, AgregarContenido, BuscarContenidos, Categorias
│   │   ├── components/               Sidebar, Header, ContentDetail, Recomendaciones,
│   │   │                             AnalyticsPanel, SearchHistory, ConfirmDialog…
│   │   ├── hooks/                    useContenidos, useAnaliticas, useRecomendaciones,
│   │   │                             useHistorialBusquedas
│   │   ├── services/api.js           Cliente HTTP (único punto que conoce la API)
│   │   ├── data/                     categorias.js (colores), usuario.js (identidad)
│   │   └── index.css                 Tokens de branding (tema oscuro/morado)
│   │
│   ├── Dockerfile                    Build con Node 24 → servido por Nginx
│   ├── nginx.conf                    SPA routing + proxy /api → backend
│   └── vite.config.js                Proxy /api → localhost:8000 (desarrollo)
│
├── docs/
│   ├── QA_TESTING_GUIDE.md                                 Guía completa para QA
│   ├── GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md              Arquitectura SOLID + ML
│   ├── GUIA_EXPLICATIVA_SEMANA4_RECOMENDACIONES_Y_ANALITICAS.md
│   └── PRESENTACION_EQUIPO_SEMANA4_5.md                    Guion del Demo Day
│
├── notebooks/EDA_Model_Training.ipynb   Entrenamiento (Data Science)
├── Data/                                Dataset limpio
├── scripts/                             Lanzadores multiplataforma
├── .github/workflows/ci.yml             CI: pytest + umbral de cobertura 85%
├── docker-compose.yml                   Stack completo (backend + frontend)
├── pytest.ini
└── package.json                         Orquesta backend + frontend
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

### 3.1. Precargar el modelo de embeddings (una sola vez)

`GET /cursos` y `GET /cursos/buscar` (el catálogo semántico de +5.000 cursos)
necesitan el modelo `paraphrase-multilingual-MiniLM-L12-v2` para poder abrir
el índice de Chroma, incluso solo para listar sin buscar nada. En OCI ese
modelo viaja horneado en la imagen de Docker; en local nadie lo precarga por
vos, así que la primera vez se descarga (~470 MB) desde Hugging Face.

Si este paso se salta, el síntoma es exactamente "0 cursos en el catálogo" en
la vista Buscar, aunque el índice tenga los datos completos — un fallo
silencioso, documentado en `backend/app/busqueda/almacen.py`.

Windows:

```bash
.venv\Scripts\python backend\scripts\precargar_modelo.py
```

macOS / Linux:

```bash
.venv/bin/python backend/scripts/precargar_modelo.py
```

> Sin salida a internet: copiá la carpeta que el build de Docker deja en
> `/opt/modelos` (ver `backend/Dockerfile`) a tu cache local y fijá
> `SENTENCE_TRANSFORMERS_HOME` a esa ruta en tu `.env`.

Para confirmar en cualquier momento si el catálogo y el recomendador por
matriz están sanos (sin tener que leer los logs del proceso), con el backend
corriendo entrá a **`GET /cursos/estado`** — devuelve `disponible`,
`total_indexado` y, si algo falló, el motivo exacto en texto plano.

### 3.2. Si tu copia usa el modelo relacional (`Data/matriz_similitud_cursos.pkl`)

Ese archivo pesa ~190 MB y viaja por **Git LFS** (`.gitattributes`). Si tu
clon no tiene `git-lfs` instalado o nunca corriste `git lfs pull`, el archivo
en disco es apenas el *puntero* de texto de LFS, no la matriz real — y
`/cursos/{id}/relacionados-matriz` responde `recomendaciones: []` siempre.
`GET /cursos/estado` distingue este caso explícitamente en
`recomendador_matriz.motivo`.

```bash
git lfs install
git lfs pull
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

### Opción C — Comandos nativos (uvicorn / vite, sin npm en la raíz)

**Backend** — desde `backend/`, con el entorno virtual activado:

```bash
uvicorn app.main:app --reload --port 8000
```

> Activar el entorno virtual primero:
> Windows `..\.venv\Scripts\activate` · macOS/Linux `source ../.venv/bin/activate`

**Frontend** — desde `frontend/`:

```bash
npm run dev
```

Vite arranca en el puerto 5173 y proxea `/api` hacia `http://127.0.0.1:8000`
(configurado en `vite.config.js`), así que **no hace falta tocar CORS** ni
definir `VITE_API_URL` en desarrollo.

### Opción D — Docker Compose (igual que en producción)

```bash
docker compose up --build
```

Levanta el stack completo tal y como corre en OCI: el frontend servido por
Nginx en el puerto 8080, con `/api` proxeado al backend por la red interna.

### Scripts disponibles

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Backend + Frontend simultáneamente |
| `npm run dev:backend` | Solo la API FastAPI |
| `npm run dev:frontend` | Solo la aplicación React |
| `npm test` | Suite de pruebas Pytest con reporte de cobertura |
| `npm run build` | Build de producción del frontend |
| `npm run install:all` | Instala dependencias de Node en raíz y frontend |

### Verificar que todo arrancó bien

```bash
curl http://localhost:8000/salud
```

Debe responder `"motor": "modelo_ml_real"`. Si dice `"clasificador_reglas"`,
el modelo no se cargó — revisa que exista `backend/models/clasificador_cursos.pkl`
y consulta los logs del backend, que indican en qué etapa falló.

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
| `GET` | `/contenidos/{id}/recomendaciones` | **Semana 4** — contenido relacionado por similitud |
| `GET` | `/metricas` | Resumen básico del historial |
| `GET` | `/analiticas` | **Semana 4** — panel completo del Dashboard |
| `POST` | `/auth/registro` | **Semana 5** — crea una cuenta (login automático) |
| `POST` | `/auth/login` | **Semana 5** — inicia sesión, devuelve un JWT |
| `GET` | `/auth/me` | **Semana 5** — usuario dueño del token enviado |
| `GET` | `/auth/usuarios` | **Semana 5** — catálogo de cuentas (solo rol `admin`) |

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
  "version": "0.4.0",
  "entorno": "development",
  "motor": "modelo_ml_real",
  "modelo_cargado": "clasificador_cursos.pkl",
  "detalle_modelo": "Pipeline",
  "es_mock": false,
  "contenidos_en_historial": 8
}
```

El campo **`motor`** indica qué engine responde las predicciones:

| Valor | Significado |
|-------|-------------|
| `modelo_ml_real` | El artefacto entrenado está cargado y verificado |
| `clasificador_reglas` | Fallback por taxonomía de palabras clave |

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

### `GET /metricas` — resumen básico del historial

```bash
curl http://localhost:8000/metricas
```

### `GET /contenidos/{id}/recomendaciones` — contenido relacionado *(Semana 4)*

```bash
curl "http://localhost:8000/contenidos/2/recomendaciones?limite=3"
```

**Respuesta esperada (200):**

```json
{
  "contenido_id": 2,
  "titulo": "Docker para Principiantes",
  "estrategia": "keywords-jaccard-v1",
  "total": 1,
  "items": [
    {
      "id": 8,
      "titulo": "Kubernetes en Produccion",
      "categoria": "Cloud Computing y DevOps",
      "puntaje": 0.438,
      "palabras_compartidas": ["Docker"]
    }
  ]
}
```

La relevancia combina similitud de palabras clave (índice de Jaccard, 75%) con
coincidencia de categoría (25%). `palabras_compartidas` es la evidencia que la
UI usa para explicar *por qué* se recomendó cada elemento.

### `GET /analiticas` — panel completo del Dashboard *(Semana 4)*

```bash
curl http://localhost:8000/analiticas
```

Superset de `/metricas`: añade distribución de confianza (Alta / Media / Baja),
distribución por origen, actividad por día y el motor de clasificación activo.

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

### `POST /auth/registro` — crear una cuenta *(Semana 5)*

El primer usuario que se registra en una instalación nueva de AthenIA recibe
el rol `admin` automáticamente; el resto entra como `estudiante`.

```bash
curl -X POST http://localhost:8000/auth/registro \
  -H "Content-Type: application/json" \
  -d '{"email":"ferney@athenia.dev","password":"unaClaveSegura123","nombre":"Ferney"}'
```

Respuesta esperada (`201`):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "usuario": {
    "id": 1,
    "email": "ferney@athenia.dev",
    "nombre": "Ferney",
    "rol": "admin",
    "creado_en": "2026-08-21T03:14:00Z"
  }
}
```

### `POST /auth/login` — iniciar sesión *(Semana 5)*

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ferney@athenia.dev","password":"unaClaveSegura123"}'
```

`401` si el correo o la contraseña no coinciden.

### `GET /auth/me` y `/auth/usuarios` — sesión y roles *(Semana 5)*

El token se envía como header `Authorization: Bearer <token>` en cada
petición protegida:

```bash
curl http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"

# Solo responde 200 si $TOKEN pertenece a un usuario con rol "admin".
# Un rol "estudiante" recibe 403 aunque el token sea valido.
curl http://localhost:8000/auth/usuarios -H "Authorization: Bearer $TOKEN"
```

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

### Estado actual: 120 pruebas en verde · 96.72% de cobertura

La cobertura se mide en cada ejecución (`pytest.ini` incluye
`--cov-fail-under=85`), así que **la suite falla si baja del 85%**. Es la misma
regla que aplica el pipeline de CI.

```
Name                                   Stmts   Miss  Cover
--------------------------------------------------------------------
backend/app/__init__.py                    1      0   100%
backend/app/config.py                     46      4    91%
backend/app/dependencies.py               11      0   100%
backend/app/domain/protocols.py           43      0   100%
backend/app/domain/similitud.py           33      0   100%
backend/app/domain/taxonomia.py           26      0   100%
backend/app/errors.py                     29      2    93%
backend/app/main.py                       36      1    97%
backend/app/ml/adaptador.py               50      0   100%
backend/app/ml/carga.py                   63      4    94%
backend/app/ml/modelo.py                  44      2    95%
backend/app/ml/registro.py                30      3    90%
backend/app/ml/reglas.py                  38      0   100%
backend/app/recomendador.py               24      0   100%
backend/app/repositories/memoria.py       45      1    98%
backend/app/routers/analiticas.py         10      0   100%
backend/app/routers/contenido.py          39      0   100%
backend/app/routers/salud.py              16      0   100%
backend/app/schemas.py                   110      1    99%
backend/app/services.py                   64      7    89%
--------------------------------------------------------------------
TOTAL                                    762     25    97%

Required test coverage of 85% reached. Total coverage: 96.72%
============================= 120 passed in 2.81s =============================
```

**Qué cubre la suite:**

| Grupo | Casos | Qué valida |
|-------|-------|------------|
| Contrato del Hackathon | CP-01…CP-40 | `POST /contenido`, validaciones 422, CORS |
| Historial y métricas | CP-50…CP-81 | Filtros, detalle, agregados |
| Integración ML | CP-90…CP-113 | Modelo real, formatos de artefacto, fallback |
| Arquitectura SOLID | CP-106, CP-107 | OCP y DIP verificados en ejecución |
| Recomendaciones | CP-200…CP-222 | Jaccard, ranking, evidencia, motor sustituible |
| Analíticas | CP-230…CP-252 | Distribuciones, regresión de `/metricas` |

Reporte navegable en HTML:

```bash
pytest --cov-report=html
```

📖 Guía detallada para QA: [`docs/QA_TESTING_GUIDE.md`](docs/QA_TESTING_GUIDE.md)

---

## 🐳 Docker

### Stack completo (recomendado)

Levanta backend + frontend con una sola orden, desde la raíz:

```bash
docker compose up --build
```

| Servicio | URL |
|----------|-----|
| Frontend (Nginx) | http://localhost:8080 |
| API vía Nginx | http://localhost:8080/api/salud |
| API directa (Swagger) | http://localhost:8000/docs |

Parar y limpiar:

```bash
docker compose down
```

**Cómo se comunican:** el frontend llama a rutas relativas (`/api/...`) y Nginx
las proxea al backend por la red interna de Docker. El navegador nunca hace
peticiones cross-origin, así que no hay CORS que configurar ni riesgo de
contenido mixto (HTTPS → HTTP) al desplegar en OCI.

### Servicios por separado

```bash
docker build -t athenia-backend:latest ./backend
```

```bash
docker build -t athenia-frontend:latest ./frontend
```

La imagen del backend usa `python:3.13-slim`, build multi-stage, usuario sin
privilegios y `HEALTHCHECK` contra `/salud`. **Incluye el modelo entrenado**
(`clasificador_cursos.pkl`), así que el contenedor arranca con el motor real,
no con el fallback.

La del frontend compila con Node 24 y sirve los estáticos con Nginx, con SPA
routing (`try_files`) para que recargar `/buscar` no dé 404.

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
| `ATHENIA_DB_URL` | SQLite local (`backend/data/`) | Base de usuarios. Postgres en producción (ver `docker-compose.yml`) |
| `ATHENIA_JWT_SECRET` | clave de desarrollo | Firma los JWT de sesión. **Cambiar en producción** |
| `ATHENIA_JWT_EXPIRA_MIN` | `1440` (24 h) | Vigencia del token de sesión, en minutos |
| `ATHENIA_OCI_BUCKET` | — | Reservado: Object Storage |

### Frontend

Copiar `frontend/.env.example` a `frontend/.env`:

| Variable | Defecto | Descripción |
|----------|---------|-------------|
| `VITE_API_URL` | `/api` (proxy de Vite) | URL del backend en despliegue |

---

## 🔐 Autenticación y usuarios (Semana 5)

AthenIA tiene login y registro reales — no una maqueta visual. Sigue el mismo
patrón SOLID que el resto del backend: `domain/protocols.py` define el
contrato `RepositorioUsuarios`, `repositories/usuarios_sql.py` lo implementa
sobre SQLAlchemy, y ni las rutas ni `auth_service.py` conocen el motor de base
de datos concreto.

| Pieza | Detalle |
|-------|---------|
| Contraseñas | Hasheadas con `bcrypt` (vía `passlib`). Nunca se guardan ni se loggean en texto plano |
| Sesión | JWT firmado (`HS256`), enviado como `Authorization: Bearer <token>`, vigente 24 h por defecto |
| Roles | El **primer usuario registrado** en una instalación nueva recibe `admin` automáticamente; el resto entra como `estudiante` |
| Base de datos | SQLite local sin configurar nada (`backend/data/`, ideal para desarrollo); Postgres en producción vía `ATHENIA_DB_URL` — ver el servicio `athenia-db` en `docker-compose.yml` |
| Control de acceso | `GET /auth/usuarios` solo responde a `admin` (403 para `estudiante`), demostrando RBAC sobre el mismo mecanismo que protegería cualquier endpoint futuro |

**Antes de desplegar en OCI**, cambiar dos valores en `docker-compose.yml` /
el `.env` real (vienen con un placeholder a propósito, para que
`docker compose up` funcione de entrada en la demo):

```bash
# Genera un secreto real para producción:
python -c "import secrets; print(secrets.token_hex(32))"
```

- `ATHENIA_JWT_SECRET` — con el placeholder, cualquiera que lea este repo
  público puede firmar tokens válidos.
- La contraseña de `athenia-db` (Postgres) en `docker-compose.yml`.

Ver ejemplos con `curl` en la sección [Ejemplos con curl](#-ejemplos-con-curl)
y las pruebas en `backend/tests/test_auth.py`.

---

## 🤖 Integración del modelo de IA

### Modelo activo (Semana 3)

El backend usa el modelo entrenado por el equipo de Data Science:

| Propiedad | Valor |
|-----------|-------|
| Archivo | `backend/models/clasificador_cursos.pkl` |
| Arquitectura | `Pipeline(TfidfVectorizer → MultinomialNB)` |
| Entrenado con | scikit-learn **1.6.1** |
| Entrada | Texto crudo (`f"{titulo}. {texto}"`) |

**Clases que predice:**

| Clase | |
|-------|-|
| Desarrollo de Software y Web | Ciencia de Datos y Analítica |
| Cloud Computing y DevOps | Inteligencia Artificial y ML |
| Ciberseguridad y Redes | |

> ⚠️ El pin `scikit-learn==1.6.1` en `requirements.txt` **debe coincidir** con la
> versión de entrenamiento. Con otra versión el artefacto carga pero sklearn
> advierte de posibles resultados inválidos.

### Dos motores, un contrato

`GET /salud` reporta cuál está respondiendo:

```bash
curl http://localhost:8000/salud | grep motor
```

| `motor` | Clase | Cuándo |
|---------|-------|--------|
| `modelo_ml_real` | `ClasificadorML` | Artefacto cargado y verificado |
| `clasificador_reglas` | `ClasificadorReglas` | Fallback |

La respuesta de `POST /contenido` es idéntica en ambos casos — el frontend no
necesita saber cuál está activo.

### Mecanismo de fallback (4 etapas)

`obtener_clasificador()` degrada a reglas si falla cualquier etapa:

| # | Etapa | Qué detecta |
|---|-------|-------------|
| 1 | **Localizar** | El archivo no está en `backend/models/` |
| 2 | **Deserializar** | Pickle corrupto, versión incompatible, dependencia ausente |
| 3 | **Adaptar** | Estructura desconocida o sin `.predict()` |
| 4 | **Sondear** | Carga bien pero revienta al predecir |

Además, un error de inferencia **en caliente** se responde con reglas en vez de
devolver un 500. **La demo nunca se cae por un problema del modelo.**

### Formatos de artefacto aceptados

El backend acepta las tres formas en que un notebook suele guardar el modelo:
`Pipeline` completo, `dict` con modelo y vectorizador por separado, o `tuple`.
Sirven tanto `joblib.dump` como `pickle.dump`.

📖 Guía completa para Data Science: [`backend/models/README.md`](backend/models/README.md)

---

## 📚 Documentación del proyecto

| Documento | Para quién | Qué contiene |
|-----------|-----------|--------------|
| [`docs/QA_TESTING_GUIDE.md`](docs/QA_TESTING_GUIDE.md) | QA | Catálogo de los 120 casos, fixtures, checklist manual de UI y troubleshooting |
| [`docs/GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md`](docs/GUIA_TECNICA_Y_PRESENTACION_SEMANA3.md) | Backend / Arquitectura | Arquitectura SOLID, integración del modelo ML y mecanismo de fallback |
| [`docs/GUIA_EXPLICATIVA_SEMANA4_RECOMENDACIONES_Y_ANALITICAS.md`](docs/GUIA_EXPLICATIVA_SEMANA4_RECOMENDACIONES_Y_ANALITICAS.md) | Full Stack | Jaccard paso a paso, flujo de analíticas y debounce del historial |
| [`docs/PRESENTACION_EQUIPO_SEMANA4_5.md`](docs/PRESENTACION_EQUIPO_SEMANA4_5.md) | Todo el equipo | Guion diapositiva por diapositiva para el Demo Day |
| [`backend/models/README.md`](backend/models/README.md) | Data Science | Contrato del artefacto, formatos aceptados y versiones |

---

## 🗺️ Roadmap

| Semana | Objetivo | Estado |
|--------|----------|--------|
| 1 | Descubrimiento, arquitectura y plan de trabajo | ✅ |
| 2 | Frontend base + API mock + suite de pruebas | ✅ |
| 3 | Integración del modelo de IA real + refactor SOLID | ✅ |
| 4 | Recomendaciones, dashboard analítico y mejoras UX | ✅ |
| 5 | Pulido, documentación, Docker Compose y Demo Day | ✅ |

### Pendiente tras el MVP

Se documenta explícitamente lo que **no** está resuelto, para que nadie lo
descubra en producción:

| Tema | Estado actual | Siguiente paso |
|------|---------------|----------------|
| **Persistencia del historial** | El historial de análisis vive en memoria y se pierde al reiniciar el contenedor | Implementar `RepositorioOracle` contra Autonomous Database cumpliendo el `Protocol` existente |
| ~~**Autenticación**~~ | ✅ Resuelto (Semana 5): login/registro reales con JWT, roles (`admin`/`estudiante`) y base de usuarios en Postgres | Conectar el frontend a un flujo de recuperación de contraseña |
| **CORS** | Por defecto `*`; en `docker-compose.yml` ya va restringido | Enumerar dominios reales en la variable `ATHENIA_CORS_ORIGINS` |
| **Notificaciones** | Botón deshabilitado en la UI | Fuera del alcance del MVP |

---

<div align="center">

**AthenIA** — *"El conocimiento es como un jardín: si no se cultiva, no puede ser cosechado."*

</div>
