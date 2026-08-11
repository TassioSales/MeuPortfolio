@echo off
REM L'Aquila AI - Initial Setup Script (Windows)
REM This script prepares the environment for first run

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  L'Aquila AI - Initial Setup
echo  Windows Configuration
echo ========================================
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Docker is not installed
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    echo After installation, run this script again
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is installed

REM Check if docker compose is available (mesmo motivo do run.bat: o binario
REM com hifen e o shim antigo, nao o que os scripts usam).
docker compose version >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] docker compose not available - update Docker Desktop
)

echo [OK] Docker setup verified
echo.

REM Create .env from .env.example if it doesn't exist
if exist .env (
    echo [INFO] .env file already exists, skipping copy
    echo [INFO] To reset, delete .env and run setup again
) else (
    if exist .env.example (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env >nul
        echo [OK] .env created
        echo.
        echo [ACTION REQUIRED] Please update .env with your configuration:
        echo   - ANTHROPIC_API_KEY: Your Anthropic API key
        echo   - EVOLUTION_API_KEY: Your Evolution API key
        echo   - DATABASE_URL: PostgreSQL connection string ^(or use default^)
        echo   - REDIS_URL: Redis connection string ^(or use default^)
        echo.
        echo You can edit .env now with your text editor
    ) else (
        echo.
        echo [ERROR] .env.example not found
        echo Make sure you run this script from the project root directory
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Checking required environment variables...

REM Check if .env exists and has required keys.
REM
REM Aqui vai `!errorlevel!`, e nao `%errorlevel%`: o cmd expande o bloco `( )`
REM inteiro de uma vez, antes de executar qualquer linha dele, entao o
REM `%errorlevel%` traria o valor de antes do findstr: o resultado do proprio
REM findstr nunca era lido. E por isso que o script abre com
REM `setlocal enabledelayedexpansion`.
if exist .env (
    findstr /i "ANTHROPIC_API_KEY" .env >nul
    if !errorlevel! neq 0 (
        echo [WARNING] ANTHROPIC_API_KEY not configured
    ) else (
        echo [OK] ANTHROPIC_API_KEY is configured
    )

    findstr /i "DATABASE_URL" .env >nul
    if !errorlevel! neq 0 (
        echo [WARNING] DATABASE_URL not configured ^(will use defaults^)
    ) else (
        echo [OK] DATABASE_URL is configured
    )
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env with your API keys and configuration
echo   2. Run: run.bat
echo      (to start all services)
echo.
echo For more information, see:
echo   - CLAUDE.md for project structure
echo   - laquilaia_whatsapp/GUIA_WEBHOOK.md for webhook docs
echo   - laquilaia_whatsapp/GUIA_LLM.md for LLM docs
echo.
pause
exit /b 0
