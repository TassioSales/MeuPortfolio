@echo off
echo Iniciando PriceTrack AI...
echo.
if not exist ".env" (
  if exist "config.env.example" copy config.env.example .env >nul
  echo [INFO] Configure sua GEMINI_API_KEY no arquivo .env
)
docker-compose up --build %*
