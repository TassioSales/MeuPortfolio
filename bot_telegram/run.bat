@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   Bot Telegram - Assistente de Produtividade
echo ============================================
echo.
if not exist ".env" (
  echo [AVISO] Arquivo .env nao encontrado.
  echo Copie .env.example para .env e configure TELEGRAM_BOT_TOKEN.
  pause
  exit /b 1
)
echo Iniciando com Docker Compose...
docker-compose up --build %*
