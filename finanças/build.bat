@echo off
setlocal
echo.
echo  ============================================
echo    PATRIMÔNIO — Geração do Executável
echo  ============================================
echo.

if not exist venv (
    echo  [ERRO] Ambiente virtual nao encontrado.
    echo  Execute install.bat primeiro.
    echo.
    pause
    exit /b 1
)

echo  [1/4] Coletando arquivos estaticos...
venv\Scripts\python.exe manage.py collectstatic --noinput --clear
if %errorlevel% neq 0 (
    echo  [ERRO] collectstatic falhou.
    pause
    exit /b 1
)

echo  [2/4] Aplicando migracoes (verifica modelo)...
venv\Scripts\python.exe manage.py migrate --check
if %errorlevel% neq 0 (
    echo  [AVISO] Ha migracoes pendentes. Rode: python manage.py migrate
)

echo  [3/4] Gerando executavel com PyInstaller...
venv\Scripts\python.exe -m PyInstaller finance_project.spec --noconfirm
if %errorlevel% neq 0 (
    echo  [ERRO] PyInstaller falhou. Veja as mensagens acima.
    pause
    exit /b 1
)

echo  [4/4] Limpando arquivos temporarios de build...
if exist build rmdir /s /q build

echo.
echo  ============================================
echo    Build concluido com sucesso!
echo  ============================================
echo.
echo  Executavel gerado em:
echo    dist\Patrimonio.exe
echo.
echo  Para distribuir, copie a pasta dist\ inteira
echo  ou apenas o arquivo Patrimonio.exe.
echo  O banco de dados (patrimonio.db) sera criado
echo  automaticamente na primeira execucao.
echo.
pause
