@echo off
echo ==========================================
echo      Gerando Executavel (Build)
echo ==========================================

if not exist venv (
    echo Erro: Ambiente virtual nao encontrado. Execute 'install.bat' primeiro.
    pause
    exit /b
)

call venv\Scripts\activate

echo [1/3] Coletando arquivos estaticos...
python manage.py collectstatic --noinput

echo [2/3] Executando PyInstaller...
pyinstaller finance_project.spec

echo.
echo ==========================================
echo      Build Concluido!
echo ==========================================
echo O executavel esta na pasta: dist\finance_project.exe
echo.
pause
