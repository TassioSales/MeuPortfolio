@echo off
REM L'Aquila AI - WhatsApp Clone Launcher (Windows)
REM This script starts the backend, database, and opens the dashboard

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  L'Aquila AI - WhatsApp Clone
echo  Starting Services (Windows)
echo ========================================
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Docker is not installed or not in PATH
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

REM Check if docker-compose is available
where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] docker-compose is not available
    echo Modern Docker includes docker compose. Please update Docker.
    echo.
    pause
    exit /b 1
)

REM Parse command line arguments
set MODE=dev
set ACTION=start

if "%1"=="" (
    goto :start_services
)

if /i "%1"=="dev" set MODE=dev & shift
if /i "%1"=="prod" set MODE=prod & shift
if /i "%1"=="logs" (
    echo Showing logs... (Press Ctrl+C to stop)
    docker compose -f docker-compose.yml logs -f backend
    exit /b 0
)
if /i "%1"=="stop" (
    echo Stopping services...
    docker compose -f docker-compose.yml down
    echo All services stopped.
    exit /b 0
)
if /i "%1"=="clean" (
    echo Cleaning up Docker volumes and containers...
    docker compose -f docker-compose.yml down -v
    echo Cleanup complete.
    exit /b 0
)

:start_services
echo [INFO] Mode: %MODE%
echo [INFO] Checking docker-compose configuration...

if not exist docker-compose.yml (
    echo.
    echo [ERROR] docker-compose.yml not found
    echo Make sure you run this script from the project root directory
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting services with docker-compose...
echo.

REM Start services
docker compose -f docker-compose.yml up -d

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start services
    echo Check Docker daemon and docker-compose logs above
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Services Starting...
echo ========================================
echo.
echo [INFO] Waiting for services to be ready...

REM Wait for API to be healthy
set retry=0
set max_retries=30

:health_check
timeout /t 2 /nobreak >nul

curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend API is ready at http://localhost:8000
    goto :open_browser
)

set /a retry=retry+1
if %retry% lss %max_retries% (
    echo [INFO] Waiting for API... (attempt %retry%/%max_retries%)
    goto :health_check
)

echo [WARNING] API health check timed out, but services may still be starting
echo.

:open_browser
echo.
echo ========================================
echo  Ready!
echo ========================================
echo.
echo Backend API:      http://localhost:8000
echo Documentation:    http://localhost:8000/docs
echo Database:         PostgreSQL on localhost:5432
echo Cache:            Redis on localhost:6379
echo.
echo [INFO] Opening browser...
timeout /t 3 /nobreak >nul

REM Try to open browser
start http://localhost:8000/docs

echo.
echo [INFO] Services running in the background
echo [INFO] To stop: Use "run.bat stop"
echo [INFO] To view logs: Use "run.bat logs"
echo [INFO] To clean up: Use "run.bat clean"
echo.
echo Press Ctrl+C to stop docker-compose, or let it run in background
echo.

docker compose -f docker-compose.yml logs -f backend

goto :end

:end
echo.
echo ========================================
echo  Shutdown Complete
echo ========================================
echo.
pause
exit /b 0
