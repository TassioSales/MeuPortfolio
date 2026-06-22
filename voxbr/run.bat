@echo off
echo ============================================
echo    VoxBR - Plataforma de Transcricao de Audio
echo ============================================
echo.
echo NOTA: A primeira inicializacao baixa o modelo
echo       Whisper 'base' (~150MB). Aguarde...
echo.

if not exist ".env" (
    if exist ".env.example" (
        echo Arquivo .env nao encontrado. Copiando .env.example...
        copy .env.example .env
        echo Edite .env e adicione sua MISTRAL_API_KEY para habilitar resumos com IA.
        echo.
    )
)

echo Iniciando servicos com Docker Compose...
echo.
docker-compose up --build %*
