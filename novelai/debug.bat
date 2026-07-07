@echo off
echo Iniciando debug...
echo.

echo Passo 1: Testando Python
python --version
echo errorlevel=%errorlevel%
echo.

echo Passo 2: Testando Docker
docker --version
echo errorlevel=%errorlevel%
echo.

echo Passo 3: Testando Node
node --version
echo errorlevel=%errorlevel%
echo.

echo Passo 4: Verificando pastas
dir "%~dp0"
echo.

echo Debug concluido.
pause
