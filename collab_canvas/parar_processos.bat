@echo off
setlocal

echo Parando processos do CollabCanvas nas portas 3000 e 8080...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
  echo Encerrando processo da porta 3000: %%a
  taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
  echo Encerrando processo da porta 8080: %%a
  taskkill /PID %%a /F >nul 2>&1
)

echo Concluido.
pause

endlocal
