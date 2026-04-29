@echo off
setlocal EnableExtensions EnableDelayedExpansion

if /I "%~1"=="--internal" (
  shift
  goto :main
)

set "BOOTSTRAP_LOG_DIR=%~dp0logs"
if not exist "%BOOTSTRAP_LOG_DIR%" mkdir "%BOOTSTRAP_LOG_DIR%"
set "BOOTSTRAP_LOG=%BOOTSTRAP_LOG_DIR%\run.log"
del /f /q "%BOOTSTRAP_LOG%" 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$start = Get-Date;" ^
  "'[' + $start.ToString('yyyy-MM-dd HH:mm:ss') + '] START run.bat' | Tee-Object -FilePath '%BOOTSTRAP_LOG%';" ^
  "& '%~f0' --internal 2>&1 | Tee-Object -FilePath '%BOOTSTRAP_LOG%';" ^
  "$exitCode = $LASTEXITCODE;" ^
  "$end = Get-Date;" ^
  "$status = if ($exitCode -eq 0) { 'SUCCESS' } else { 'FAIL' };" ^
  "'[' + $end.ToString('yyyy-MM-dd HH:mm:ss') + '] END run.bat STATUS=' + $status + ' EXIT_CODE=' + $exitCode | Tee-Object -FilePath '%BOOTSTRAP_LOG%' -Append;" ^
  "exit $LASTEXITCODE"
exit /b %ERRORLEVEL%

:main
cd /d "%~dp0"

echo ========================================
echo Fuel Control Room - Live Intelligence
echo ========================================
echo.

set "ROOT=%cd%"
set "PIPELINE_DIR=%ROOT%\data-pipeline-python"
set "BACKEND_DIR=%ROOT%\backend-go"
set "FRONTEND_DIR=%ROOT%\frontend-next"
set "LOG_DIR=%ROOT%\logs"
set "API_LOG=%LOG_DIR%\backend.log"
set "FRONTEND_LOG=%LOG_DIR%\frontend.log"
set "PIPELINE_LOG=%LOG_DIR%\pipeline.log"
set "PIPELINE_STDOUT_LOG=%LOG_DIR%\pipeline.stdout.log"
set "DUCKDB_PATH=%ROOT%\data-lake\warehouse\fuel_analytics.duckdb"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
del /f /q "%API_LOG%" 2>nul
del /f /q "%FRONTEND_LOG%" 2>nul
del /f /q "%PIPELINE_LOG%" 2>nul
del /f /q "%PIPELINE_STDOUT_LOG%" 2>nul

echo System Hub: "%LOG_DIR%\run.log"
echo Data Engine: "%PIPELINE_STDOUT_LOG%"
echo Intelligence API: "%API_LOG%"
echo Control Interface: "%FRONTEND_LOG%"
echo.

if exist "%ROOT%\.env.local" (
  echo [env] Synchronizing operational variables from "%ROOT%\.env.local"...
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\.env.local") do (
    if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
  )
  echo.
)

set "PY_CMD="
where python >nul 2>nul && set "PY_CMD=python"
if not defined PY_CMD (
  where py >nul 2>nul && set "PY_CMD=py -3"
)

where go >nul 2>nul
if errorlevel 1 (
  echo [CRITICAL] Go environment not found in PATH.
  goto :fail
)

where node >nul 2>nul
if errorlevel 1 (
  echo [CRITICAL] Node.js environment not found in PATH.
  goto :fail
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [CRITICAL] npm environment not found in PATH.
  goto :fail
)

if not defined PY_CMD (
  echo [CRITICAL] Python environment not found in PATH.
  echo Recommended: Python 3.11+ with "Add to PATH" enabled.
  goto :fail
)

echo [0/6] Clearing port conflicts (3000, 8080)...
for %%P in (3000 8080) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
    if not "%%I"=="0" (
      echo Terminating process ID %%I on port %%P
      taskkill /PID %%I /F >nul 2>nul
    )
  )
)

echo [1/6] Initializing Python Virtual Environment...
if not exist "%PIPELINE_DIR%\.venv\Scripts\python.exe" (
  call %PY_CMD% -m venv "%PIPELINE_DIR%\.venv"
  if errorlevel 1 (
    echo [CRITICAL] Failed to build virtual environment.
    goto :fail
  )
)

call "%PIPELINE_DIR%\.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [CRITICAL] Failed to activate virtual environment.
  goto :fail
)

python -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 goto :fail

echo [2/6] Synchronizing Data Engine dependencies...
python -m pip install -e "%PIPELINE_DIR%[dev]" >nul 2>&1
if errorlevel 1 (
  echo [CRITICAL] Failed to install Python dependencies.
  goto :fail
)

echo [3/6] Running Data Pipeline and Materializing DuckDB Warehouse...
python -m fuel_analytics.cli run 1>>"%PIPELINE_STDOUT_LOG%" 2>&1
if errorlevel 1 (
  echo [CRITICAL] Data Engine failure. Check "%PIPELINE_STDOUT_LOG%".
  goto :fail
)

if not exist "%DUCKDB_PATH%" (
  echo [WARNING] DuckDB Warehouse was not generated. API will run in Snapshot mode.
) else (
  echo [OK] DuckDB Warehouse materialized at "%DUCKDB_PATH%".
)

echo [4/6] Synchronizing Intelligence API (Go) dependencies...
pushd "%BACKEND_DIR%"
call go mod tidy
if errorlevel 1 (
  echo [CRITICAL] Go dependency synchronization failed.
  popd
  goto :fail
)
popd

echo [5/6] Instalando dependencias do frontend...
pushd "%FRONTEND_DIR%"
call npm install
if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias do frontend.
  popd
  goto :fail
)
popd

echo [6/6] Launching Operations...
start "Fuel Intelligence API" powershell -NoExit -ExecutionPolicy Bypass -Command ^
  "$Host.UI.RawUI.WindowTitle = 'Fuel Intelligence API';" ^
  "Set-Location '%BACKEND_DIR%';" ^
  "Write-Host '[System] Initializing Intelligence API (Go)...' -ForegroundColor Cyan;" ^
  "& { go run ./cmd/api *>&1 | Tee-Object -FilePath '%API_LOG%' -Append }"
start "Fuel Control Interface" powershell -NoExit -ExecutionPolicy Bypass -Command ^
  "$Host.UI.RawUI.WindowTitle = 'Fuel Control Interface';" ^
  "Set-Location '%FRONTEND_DIR%';" ^
  "Write-Host '[System] Initializing Control Interface (Next.js)...' -ForegroundColor Cyan;" ^
  "& { npm run dev *>&1 | Tee-Object -FilePath '%FRONTEND_LOG%' -Append }"
timeout /t 8 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo Operation active.
echo Command Center: http://localhost:3000
echo Intelligence Hub: http://localhost:8080
echo.
if defined MISTRAL_API_KEY (
  echo [AI] Intelligence Layer enabled (Mistral AI).
) else (
  echo [AI] Intelligence Layer offline. (Set MISTRAL_API_KEY to enable).
)
goto :eof

:fail
echo.
echo Bootstrap interrompido.
exit /b 1
