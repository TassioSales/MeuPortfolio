@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   WealthMap Analytics - Gestao de Patrimonio
echo ============================================
echo.
if not exist ".env" (
  echo [AVISO] Configure MISTRAL_API_KEY no arquivo .env para habilitar IA.
)
echo Iniciando com Docker Compose...
docker-compose up --build %*
