@echo off
echo === Encurtador URL ===

REM Start Go backend
start "Backend" cmd /k "cd /d %~dp0backend && go run ./cmd/api"

REM Install frontend deps if needed
if not exist "%~dp0frontend\node_modules" (
    echo Installing frontend dependencies...
    cd /d "%~dp0frontend"
    npm install
)

REM Start Next.js frontend
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Backend  → http://localhost:8080
echo Frontend → http://localhost:3000
echo.
pause
