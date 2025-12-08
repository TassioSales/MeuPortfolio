@echo off
echo ==========================================
echo      Criando Backup do Projeto
echo ==========================================

if not exist venv (
    echo Erro: Ambiente virtual nao encontrado. Execute 'install.bat' primeiro.
    pause
    exit /b
)

call venv\Scripts\activate

python backup_project.py

echo.
pause
