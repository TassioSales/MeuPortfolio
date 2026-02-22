@echo off
setlocal
echo ==========================================
echo      Gerando Executavel (Build)
echo ==========================================

if not exist venv (
    echo Erro: Ambiente virtual nao encontrado. Execute 'install.bat' primeiro.
    pause
    exit /b
)

echo [1/3] Coletando arquivos estaticos...
venv\Scripts\python.exe manage.py collectstatic --noinput

echo [2/3] Executando PyInstaller...
venv\Scripts\python.exe -m PyInstaller finance_project.spec --noconfirm

echo [3/3] Limpando arquivos temporarios...
if exist build rmdir /s /q build

echo.
echo ==========================================
echo      Build Concluido!
echo ==========================================
echo O executavel esta na pasta: dist\finance_project.exe
echo.
pause
