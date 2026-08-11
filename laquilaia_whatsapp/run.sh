#!/bin/bash

# L'Aquila AI - WhatsApp Clone Launcher (Linux/Mac)
# This script starts the backend, database, and opens the dashboard

set -e

echo ""
echo "========================================"
echo " L'Aquila AI - WhatsApp Clone"
echo " Starting Services (Linux/Mac)"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo ""
    echo "[ERROR] Docker is not installed"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    echo ""
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo ""
    echo "[ERROR] docker-compose is not available"
    echo "Please install docker-compose or update Docker"
    echo ""
    exit 1
fi

# Parse command line arguments
MODE="dev"

while [[ $# -gt 0 ]]; do
    case $1 in
        dev)
            MODE="dev"
            shift
            ;;
        prod)
            MODE="prod"
            shift
            ;;
        logs)
            echo "Showing logs... (Press Ctrl+C to stop)"
            docker compose -f docker-compose.yml logs -f backend
            exit 0
            ;;
        stop)
            echo "Stopping services..."
            docker compose -f docker-compose.yml down
            echo "All services stopped."
            exit 0
            ;;
        clean)
            echo "Cleaning up Docker volumes and containers..."
            docker compose -f docker-compose.yml down -v
            echo "Cleanup complete."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [dev|prod|logs|stop|clean]"
            exit 1
            ;;
    esac
done

echo "[INFO] Mode: $MODE"
echo "[INFO] Checking docker-compose configuration..."

if [ ! -f docker-compose.yml ]; then
    echo ""
    echo "[ERROR] docker-compose.yml not found"
    echo "Make sure you run this script from the project root directory"
    echo ""
    exit 1
fi

echo "[INFO] Starting services with docker-compose..."
echo ""

# Start services
docker compose -f docker-compose.yml up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to start services"
    echo "Check Docker daemon and docker-compose logs above"
    echo ""
    exit 1
fi

echo ""
echo "========================================"
echo " Services Starting..."
echo "========================================"
echo ""
echo "[INFO] Waiting for services to be ready..."

# Wait for API to be healthy
retry=0
max_retries=30

while [ $retry -lt $max_retries ]; do
    sleep 2

    if curl -s http://localhost:8000/health &> /dev/null; then
        echo "[OK] Backend API is ready at http://localhost:8000"
        break
    fi

    retry=$((retry + 1))
    echo "[INFO] Waiting for API... (attempt $retry/$max_retries)"
done

if [ $retry -ge $max_retries ]; then
    echo "[WARNING] API health check timed out, but services may still be starting"
fi

echo ""
echo "========================================"
echo " Ready!"
echo "========================================"
echo ""
echo "Backend API:      http://localhost:8000"
echo "Documentation:    http://localhost:8000/docs"
echo "Database:         PostgreSQL on localhost:5432"
echo "Cache:            Redis on localhost:6379"
echo ""
echo "[INFO] Opening browser..."
sleep 3

# Try to open browser (works on most Linux/Mac systems)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000/docs &
elif command -v open &> /dev/null; then
    open http://localhost:8000/docs &
else
    echo "[INFO] Manual browser opening not supported on this system"
    echo "[INFO] Please visit http://localhost:8000/docs manually"
fi

echo ""
echo "[INFO] Services running in the background"
echo "[INFO] To stop: Use 'run.sh stop'"
echo "[INFO] To view logs: Use 'run.sh logs'"
echo "[INFO] To clean up: Use 'run.sh clean'"
echo ""
echo "Showing logs (Press Ctrl+C to stop)..."
echo ""

docker compose -f docker-compose.yml logs -f backend

echo ""
echo "========================================"
echo " Shutdown Complete"
echo "========================================"
echo ""
