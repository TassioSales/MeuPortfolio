@echo off
echo Iniciando WealthMap Analytics...
echo.
if not exist ".env" (
  echo [AVISO] Configure MISTRAL_API_KEY no arquivo .env para habilitar IA.
)
docker-compose up --build %*
