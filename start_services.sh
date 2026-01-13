#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Prefer modern docker compose, fall back to legacy docker-compose
if command -v docker compose >/dev/null 2>&1; then
  COMPOSE=(docker compose -f "$COMPOSE_FILE")
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose -f "$COMPOSE_FILE")
else
  echo "docker compose is required but not found" >&2
  exit 1
fi

echo "=== CV-JD Matching System ==="
echo "Project root: $PROJECT_ROOT"
echo "Compose file: $COMPOSE_FILE"

# Ensure we are using latest images where applicable
echo "\n=== Pulling images ==="
"${COMPOSE[@]}" pull

# Build local images (backend)
echo "\n=== Building backend image ==="
"${COMPOSE[@]}" build api

# Start all services in detached mode
echo "\n=== Starting services ==="
"${COMPOSE[@]}" up -d

# Show status
echo "\n=== Service status ==="
"${COMPOSE[@]}" ps

# Helpful endpoints
FRONTEND_PORT=${FRONTEND_PORT:-4174}
API_PORT=${API_PORT:-8080}
CURRENT_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

echo "\n=== Access URLs ==="
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "          http://$CURRENT_IP:$FRONTEND_PORT (if accessing from other machines)"
echo "Backend:  http://localhost:$API_PORT"
echo "          http://$CURRENT_IP:$API_PORT (if accessing from other machines)"
echo "Postgres: host=localhost port=5432 user=${POSTGRES_USER:-cvjd_user} db=${POSTGRES_DB:-cv_jd_db}"
echo "\nTo view logs: ${COMPOSE[*]} logs -f"
echo "To stop services: ${COMPOSE[*]} down"
