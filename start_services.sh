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
echo "\nFrontend: http://localhost:4174"
echo "Backend:  http://localhost:8080"
echo "Postgres: host=localhost port=5432 user=${POSTGRES_USER:-cvjd_user} db=${POSTGRES_DB:-cv_jd_db}"
echo "\nTo view logs: ${COMPOSE[*]} logs -f"
echo "To stop services: ${COMPOSE[*]} down"
