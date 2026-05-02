@echo off
setlocal

echo Stopping Neon Snake on port 8091...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8091" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F >nul 2>&1
)

echo Done.
pause

endlocal
