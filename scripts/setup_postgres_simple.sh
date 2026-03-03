#!/bin/bash

# Simple PostgreSQL setup for memU (without pgvector)
# Uses standard PostgreSQL image

set -e

echo "=================================================="
echo "Setting up PostgreSQL for memU (Simple)"
echo "=================================================="
echo ""

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi

echo "✅ Docker is running"

# Remove existing container
if docker ps -a --format '{{.Names}}' | grep -q '^memu-postgres$'; then
    echo "Removing existing container..."
    docker rm -f memu-postgres
fi

echo ""
echo "Creating PostgreSQL container..."

# Try standard PostgreSQL first
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -v memu-postgres-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:16-alpine

echo ""
echo "Waiting for PostgreSQL to start..."

for i in {1..30}; do
    if docker exec memu-postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL failed to start"
        exit 1
    fi
    sleep 1
done

echo ""
echo "=================================================="
echo "Configuration"
echo "=================================================="
echo ""
echo "Add to .env:"
echo "  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/memu"
echo ""
