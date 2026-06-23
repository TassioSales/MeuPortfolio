@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

REM Re-invoca via PowerShell para gravar log com Tee-Object
if /I "%~1"=="--internal" (
  shift
  goto :main
)

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "RUN_LOG=%LOG_DIR%\run.log"
del /f /q "%RUN_LOG%" 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'SilentlyContinue';" ^
  "$start = Get-Date;" ^
  "'[' + $start.ToString('yyyy-MM-dd HH:mm:ss') + '] START' | Tee-Object '%RUN_LOG%';" ^
  "& '%~f0' --internal %* 2>&1 | Tee-Object '%RUN_LOG%' -Append;" ^
  "$code = $LASTEXITCODE;" ^
  "'[' + (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + '] END exit=' + $code | Tee-Object '%RUN_LOG%' -Append;" ^
  "exit $code"
exit /b %ERRORLEVEL%

:main
cd /d "%~dp0"

echo ========================================
echo  Fuel Control Room - Live Intelligence
echo ========================================
echo.

set "ROOT=%cd%"
set "PIPELINE_DIR=%ROOT%\data-pipeline-python"
set "BACKEND_DIR=%ROOT%\backend-go"
set "FRONTEND_DIR=%ROOT%\frontend-next"
set "LOG_DIR=%ROOT%\logs"
set "API_LOG=%LOG_DIR%\backend.log"
set "FRONTEND_LOG=%LOG_DIR%\frontend.log"
set "PIPELINE_LOG=%LOG_DIR%\pipeline.stdout.log"
set "SNAPSHOTS_DIR=%ROOT%\models"
set "DUCKDB_PATH=%ROOT%\data-lake\warehouse\fuel_analytics.duckdb"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Parse flags
set "FORCE_PIPELINE=0"
:parse_args
if /I "%~1"=="--pipeline" ( set "FORCE_PIPELINE=1" & shift & goto :parse_args )
if not "%~1"=="" ( shift & goto :parse_args )

REM --- Env vars ---
if exist "%ROOT%\.env.local" (
  echo [env] Carregando .env.local...
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\.env.local") do (
    if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
  )
) else (
  echo [env] .env.local nao encontrado. Criando a partir de .env.example...
  if exist "%ROOT%\.env.example" (
    copy /y "%ROOT%\.env.example" "%ROOT%\.env.local" >nul
  ) else (
    (echo MISTRAL_API_KEY=)>"%ROOT%\.env.local"
    (echo MISTRAL_MODEL=mistral-small-latest)>>"%ROOT%\.env.local"
    (echo NEXT_PUBLIC_API_URL=http://localhost:8080)>>"%ROOT%\.env.local"
  )
  echo [env] Edite .env.local e defina MISTRAL_API_KEY.
)
echo.

REM --- Verificar ferramentas ---
set "PY_CMD="
where python >nul 2>nul && set "PY_CMD=python"
if not defined PY_CMD (
  where py >nul 2>nul && set "PY_CMD=py -3"
)
if not defined PY_CMD (
  echo [ERRO] Python nao encontrado no PATH.
  goto :fail
)

where go >nul 2>nul
if errorlevel 1 ( echo [ERRO] Go nao encontrado no PATH. & goto :fail )

where node >nul 2>nul
if errorlevel 1 ( echo [ERRO] Node.js nao encontrado no PATH. & goto :fail )

REM --- Liberar portas ---
echo [0/5] Liberando portas 3000 e 8080...
for %%P in (3000 8080) do (
  for /f "tokens=5" %%I in ('netstat -ano 2^>nul ^| findstr /r /c:":%%P .*LISTENING"') do (
    if not "%%I"=="0" ( taskkill /PID %%I /F >nul 2>nul )
  )
)

REM --- Python venv ---
echo [1/5] Ambiente virtual Python...

REM Detecta venv corrompido: tem python.exe mas nao tem activate.bat
if exist "%PIPELINE_DIR%\.venv\Scripts\python.exe" (
  if not exist "%PIPELINE_DIR%\.venv\Scripts\activate.bat" (
    echo [AVISO] venv corrompido. Recriando...
    rmdir /s /q "%PIPELINE_DIR%\.venv" 2>nul
  )
)

if not exist "%PIPELINE_DIR%\.venv\Scripts\activate.bat" (
  echo Criando venv...
  %PY_CMD% -m venv "%PIPELINE_DIR%\.venv"
  if errorlevel 1 ( echo [ERRO] Falha ao criar venv. & goto :fail )
)

call "%PIPELINE_DIR%\.venv\Scripts\activate.bat"
if errorlevel 1 ( echo [ERRO] Falha ao ativar venv. & goto :fail )

python -m pip install --upgrade pip --quiet
if errorlevel 1 ( echo [AVISO] Falha ao atualizar pip. Continuando... )

echo Instalando dependencias do pipeline (isso pode demorar alguns minutos)...
python -m pip install --prefer-binary -e "%PIPELINE_DIR%[dev]"
if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias Python.
  goto :fail
)
echo [OK] Pipeline Python pronto.

REM --- Pipeline de dados ---
echo.
set "RUN_PIPELINE=%FORCE_PIPELINE%"
if "%RUN_PIPELINE%"=="0" (
  if not exist "%SNAPSHOTS_DIR%\overview.json" ( set "RUN_PIPELINE=1" )
  if not exist "%SNAPSHOTS_DIR%\history.json"  ( set "RUN_PIPELINE=1" )
  if not exist "%SNAPSHOTS_DIR%\fuels.json"    ( set "RUN_PIPELINE=1" )
)

if "%RUN_PIPELINE%"=="1" (
  echo [2/5] Executando pipeline ANP...
  echo       Isso pode demorar varios minutos na primeira vez.
  del /f /q "%PIPELINE_LOG%" 2>nul
  python -m fuel_analytics.cli run 1>>"%PIPELINE_LOG%" 2>&1
  if errorlevel 1 (
    echo [AVISO] Pipeline falhou. Veja: %PIPELINE_LOG%
    if exist "%SNAPSHOTS_DIR%\overview.json" (
      echo [INFO] Usando snapshots anteriores.
    ) else (
      echo [ERRO] Sem snapshots disponiveis. Abortando.
      goto :fail
    )
  ) else (
    echo [OK] Pipeline concluido.
  )
) else (
  echo [2/5] Snapshots existentes encontrados. Pulando pipeline.
  echo       Use  run.bat --pipeline  para forcar atualizacao.
)

if exist "%DUCKDB_PATH%" (
  echo [OK] DuckDB encontrado.
) else (
  echo [INFO] DuckDB ausente - API usara snapshots JSON.
)

REM --- Backend Go ---
echo.
echo [3/5] Compilando backend Go...
pushd "%BACKEND_DIR%"
go build ./cmd/api
if errorlevel 1 (
  echo [ERRO] Falha ao compilar backend Go.
  popd
  goto :fail
)
popd
echo [OK] Backend compilado.

REM --- Frontend ---
echo.
echo [4/5] Frontend Next.js...
if not exist "%FRONTEND_DIR%\node_modules" (
  echo Instalando dependencias npm...
  pushd "%FRONTEND_DIR%"
  call npm install --silent
  if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias do frontend.
    popd
    goto :fail
  )
  popd
) else (
  echo [OK] node_modules ja existe. Pulando npm install.
)

REM --- Iniciar servicos ---
echo.
echo [5/5] Iniciando servicos...
del /f /q "%API_LOG%" 2>nul
del /f /q "%FRONTEND_LOG%" 2>nul

start "Fuel Intelligence API" powershell -NoExit -ExecutionPolicy Bypass -Command ^
  "$Host.UI.RawUI.WindowTitle = 'Fuel Intelligence API';" ^
  "Set-Location '%BACKEND_DIR%';" ^
  "Write-Host '[API] http://localhost:8080' -ForegroundColor Cyan;" ^
  "& { go run ./cmd/api *>&1 | Tee-Object -FilePath '%API_LOG%' -Append }"

start "Fuel Control Interface" powershell -NoExit -ExecutionPolicy Bypass -Command ^
  "$Host.UI.RawUI.WindowTitle = 'Fuel Control Interface';" ^
  "Set-Location '%FRONTEND_DIR%';" ^
  "Write-Host '[UI] http://localhost:3000' -ForegroundColor Cyan;" ^
  "& { npm run dev *>&1 | Tee-Object -FilePath '%FRONTEND_LOG%' -Append }"

timeout /t 8 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo ========================================
echo  Aplicacao ativa!
echo ========================================
echo  Dashboard : http://localhost:3000
echo  API       : http://localhost:8080
echo  Log API   : %API_LOG%
echo  Log UI    : %FRONTEND_LOG%
echo  Log Geral : %LOG_DIR%\run.log
echo.
if defined MISTRAL_API_KEY (
  echo  [IA] Mistral AI ativo.
) else (
  echo  [IA] Mistral offline. Defina MISTRAL_API_KEY em .env.local
)
echo.
echo  Para atualizar dados ANP: run.bat --pipeline
echo ========================================
goto :eof

:fail
echo.
echo Bootstrap falhou. Verifique os erros acima.
pause
exit /b 1
