@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   VoxBR - Plataforma de Transcricao de Audio
echo ============================================
echo.
echo NOTA: A primeira inicializacao baixa o modelo
echo       Whisper 'base' (~150MB). Aguarde...
echo.
if not exist ".env" (
  if exist ".env.example" (
    copy .env.example .env >nul
    echo [INFO] .env criado. Adicione MISTRAL_API_KEY para habilitar resumos com IA.
    echo.
  )
)
echo Iniciando com Docker Compose...
docker-compose up --build %*
