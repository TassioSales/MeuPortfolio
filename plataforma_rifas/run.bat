@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   Plataforma de Rifas
echo ============================================
echo.
echo Iniciando com Docker Compose...
docker-compose up --build %*
