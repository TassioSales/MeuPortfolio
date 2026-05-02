@echo off
setlocal

cd /d "%~dp0"

echo Starting Neon Snake at http://localhost:8091
start "Neon Snake Backend" cmd /k "cd /d ""%~dp0backend"" && go run ./cmd/server"
timeout /t 2 /nobreak >nul
start "" "http://localhost:8091"

endlocal
