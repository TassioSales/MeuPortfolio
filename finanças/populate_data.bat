@echo off
setlocal
echo ==========================================
echo      Gerando Dados de Exemplo
echo ==========================================

if not exist venv (
    echo Erro: Ambiente virtual nao encontrado. Execute 'install.bat' primeiro.
    pause
    exit /b
)

echo Executando script de populacao...
venv\Scripts\python.exe examples.py

echo.
echo Dados populados com sucesso!
pause
