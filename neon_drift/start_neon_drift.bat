@echo off
setlocal

cd /d "%~dp0"

echo Starting Neon Drift at http://localhost:8090
start "Neon Drift Backend" cmd /k "cd /d ""%~dp0backend"" && go run ./cmd/server"

echo.
echo Open http://localhost:8090 in your browser.
timeout /t 2 /nobreak >nul
start "" "http://localhost:8090"

endlocal
