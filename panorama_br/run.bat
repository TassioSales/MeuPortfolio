@echo off
echo Iniciando Panorama BR...
echo.
if not exist ".env" (
  copy .env.example .env >nul
  echo [INFO] .env criado a partir do .env.example
)
docker-compose up --build %*
