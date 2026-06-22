@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   Panorama BR - Indicadores Economicos do Brasil
echo ============================================
echo.
if not exist ".env" (
  if exist ".env.example" (
    copy .env.example .env >nul
    echo [INFO] .env criado a partir do .env.example
  )
)
echo Iniciando com Docker Compose...
docker-compose up --build %*
