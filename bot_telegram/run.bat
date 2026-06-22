@echo off
echo Iniciando Bot Telegram...
echo.
if not exist ".env" (
  echo [AVISO] Arquivo .env nao encontrado. Copie .env.example para .env e configure seu TELEGRAM_BOT_TOKEN.
  pause
  exit /b 1
)
docker-compose up --build %*
