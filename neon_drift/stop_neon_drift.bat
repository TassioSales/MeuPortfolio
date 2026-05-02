@echo off
setlocal

echo Stopping Neon Drift on port 8090...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8090" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F >nul 2>&1
)

echo Done.
pause

endlocal
