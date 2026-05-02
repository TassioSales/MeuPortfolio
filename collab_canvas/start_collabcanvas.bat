@echo off
setlocal

cd /d "%~dp0"

echo Starting CollabCanvas backend on http://localhost:8080
start "CollabCanvas Backend" cmd /k "cd /d ""%~dp0backend"" && go run ./cmd/server"

echo Starting CollabCanvas frontend on http://localhost:3000
start "CollabCanvas Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- -p 3000"

echo.
echo CollabCanvas is starting:
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8080/healthz
echo.
echo Close the opened terminal windows to stop the servers,
echo or run stop_collabcanvas.bat.
timeout /t 4 /nobreak >nul
start "" "http://localhost:3000"

endlocal
