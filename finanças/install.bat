@echo off
echo ==========================================
echo      Instalando Dependencias do Projeto
echo ==========================================

echo [1/3] Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo Erro: Python nao encontrado. Por favor instale o Python.
    pause
    exit /b
)

echo [2/3] Criando Ambiente Virtual (venv)...
if not exist venv (
    python -m venv venv
    echo Venv criado com sucesso.
) else (
    echo Venv ja existe.
)

echo [3/3] Instalando bibliotecas...
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo ==========================================
echo      Instalacao Concluida com Sucesso!
echo ==========================================
echo.
pause
