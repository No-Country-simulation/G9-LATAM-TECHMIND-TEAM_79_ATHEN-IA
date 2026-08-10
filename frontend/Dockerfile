# =============================================================================
# AthenIA - Frontend (React + Vite) servido con Nginx
#
# Construir (desde la raiz del repositorio):
#   docker build -t athenia-frontend:latest ./frontend
#
# Ejecutar suelto (sin backend, solo para ver la UI):
#   docker run -p 8080:80 athenia-frontend:latest
#
# Lo normal es levantarlo con el stack completo:
#   docker compose up --build
# =============================================================================

# -----------------------------------------------------------------------------
# Etapa 1 - build: genera los estaticos con Vite.
# -----------------------------------------------------------------------------
FROM node:24-alpine AS builder

WORKDIR /build

# Capa cacheable: solo se reinstala si cambian las dependencias.
COPY package*.json ./
RUN npm ci

COPY . .

# VITE_API_URL se puede fijar en build si el backend vive en otro dominio.
# Por defecto se deja vacio a proposito: el frontend usa rutas relativas
# (`/api/...`) y Nginx las proxea al backend, evitando CORS y contenido mixto.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# -----------------------------------------------------------------------------
# Etapa 2 - runtime: Nginx sirviendo los estaticos.
# -----------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="AthenIA Frontend" \
      org.opencontainers.image.description="Interfaz React de AthenIA servida con Nginx" \
      org.opencontainers.image.vendor="Equipo AthenIA - Hackathon ONE Alura + Oracle"

# La configuracion por defecto de Nginx no sabe de SPA routing ni del proxy.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/athenia.conf

COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
