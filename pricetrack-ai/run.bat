@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   PriceTrack AI - Rastreador de Precos com IA
echo ============================================
echo.
if not exist ".env" (
  if exist "config.env.example" (
    copy config.env.example .env >nul
    echo [INFO] .env criado. Configure GEMINI_API_KEY no arquivo .env.
  ) else (
    echo [INFO] Configure GEMINI_API_KEY no arquivo .env antes de iniciar.
  )
)
echo Iniciando com Docker Compose...
docker-compose up --build %*
