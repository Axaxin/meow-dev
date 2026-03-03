#!/bin/bash

# Quick PostgreSQL container setup
# Run this in a separate terminal and wait for completion

set -e

echo "=================================================="
echo "PostgreSQL Setup for memU"
echo "=================================================="
echo ""
echo "This will:"
echo "1. Download postgres:16-alpine image (~80MB)"
echo "2. Start PostgreSQL container"
echo "3. Create 'memu' database"
echo ""
echo "Press Ctrl+C to cancel"
echo ""
read -p "Press Enter to continue..."
echo ""

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q '^memu-postgres$'; then
    echo "⚠️  Container 'memu-postgres' already exists"
    echo "Starting existing container..."
    docker start memu-postgres
    echo "✅ Container started!"
else
    echo "Creating new container..."
    docker run -d \
      --name memu-postgres \
      --restart unless-stopped \
      -e POSTGRES_USER=postgres \
      -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=memu \
      -v memu-postgres-data:/var/lib/postgresql/data \
      -p 5432:5432 \
      postgres:16-alpine
    
    echo "✅ Container created and started!"
fi

echo ""
echo "Waiting for PostgreSQL to initialize..."
sleep 5

# Check if ready
for i in {1..10}; do
    if docker exec memu-postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    echo "  Attempt $i/10..."
    sleep 2
done

# Show connection info
echo ""
echo "=================================================="
echo "✅ PostgreSQL Setup Complete!"
echo "=================================================="
echo ""
echo "Connection Details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  User: postgres"
echo "  Password: postgres"
echo "  Database: memu"
echo ""
echo "Add to your .env file:"
echo "  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/memu"
echo ""
echo "Then restart your application:"
echo "  uv run main.py"
echo ""
echo "To stop PostgreSQL:"
echo "  docker stop memu-postgres"
echo ""
