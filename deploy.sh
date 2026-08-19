#!/bin/bash

set -e

APP_DIR="/home/ubuntu/app"

echo "========================================"
echo " AthenIA - Deploy"
echo "========================================"

cd "$APP_DIR"

echo "[1/6] Verificando repositorio..."
git fetch origin main

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

echo "Commit local : $LOCAL_COMMIT"
echo "Commit GitHub: $REMOTE_COMMIT"

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo "[2/6] Actualizando código desde GitHub..."
    git pull --ff-only origin main
else
    echo "[2/6] El código ya está actualizado."
fi

echo "[3/6] Construyendo imágenes Docker..."
docker compose build

echo "[4/6] Levantando servicios..."
docker compose up -d

echo "[5/6] Esperando healthchecks..."
sleep 10

echo "Estado de los servicios:"
docker compose ps

echo "[6/6] Verificando servicios..."

BACKEND_STATUS=$(docker inspect --format='{{.State.Health.Status}}' athenia-backend 2>/dev/null || echo "not_found")
FRONTEND_STATUS=$(docker inspect --format='{{.State.Health.Status}}' athenia-frontend 2>/dev/null || echo "not_found")

echo "Backend : $BACKEND_STATUS"
echo "Frontend: $FRONTEND_STATUS"

if [ "$BACKEND_STATUS" != "healthy" ]; then
    echo "ERROR: El backend no está healthy."
    docker compose logs --tail=50 athenia-backend
    exit 1
fi

if [ "$FRONTEND_STATUS" != "healthy" ]; then
    echo "ERROR: El frontend no está healthy."
    docker compose logs --tail=50 athenia-frontend
    exit 1
fi

echo "========================================"
echo " DEPLOY COMPLETADO CORRECTAMENTE"
echo "========================================"

exit 0
