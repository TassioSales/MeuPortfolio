@echo off
setlocal
echo ==========================================
echo      Criando Backup do Projeto
echo ==========================================

if not exist venv (
    echo Erro: Ambiente virtual nao encontrado. Execute 'install.bat' primeiro.
    pause
    exit /b
)

echo Executando script de backup...
venv\Scripts\python.exe backup_project.py

echo.
echo Backup concluido com sucesso!
pause
