@echo off
setlocal EnableExtensions
title Parar - WhatsApp Suporte + Painel

REM ===========================================================================
REM  Derruba o que estiver escutando nas portas do go-live.
REM
REM  Mata por PORTA, e nao por "node.exe": um taskkill em node.exe levaria
REM  junto qualquer outro processo Node da maquina - o `npm run dev`, um editor,
REM  o que estiver aberto.
REM
REM  A porta do bot sai do .env, a mesma fonte que o run.bat usa. Fixar
REM  8511 aqui faria este script errar o alvo em silencio no dia em que aquele
REM  arquivo mudasse.
REM ===========================================================================

cd /d "%~dp0"

set "ENV_FILE=%~dp0.env"
set "PAINEL_PORT="

set "BOT_PORT="
if exist "%ENV_FILE%" for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"PORT=" "%ENV_FILE%"') do set "BOT_PORT=%%b"
if not defined BOT_PORT set "BOT_PORT=8511"

REM O PAINEL_PORT sai do .env pelo mesmo motivo que o BOT_PORT: fixar 8511 aqui
REM faria este script errar o alvo em silencio no dia em que aquele arquivo
REM mudasse - e deixaria um painel orfao segurando a porta.
if exist "%ENV_FILE%" for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"PAINEL_PORT=" "%ENV_FILE%"') do set "PAINEL_PORT=%%b"
if not defined PAINEL_PORT set "PAINEL_PORT=8511"

echo.
echo  Parando os servicos do go-live...
echo.

call :matar %BOT_PORT% "bot - whatsapp-suporte"
call :matar %PAINEL_PORT% "painel de chamados"

echo.
echo  Pronto. As janelas BOT... e PAINEL... podem ser fechadas.
echo.
pause
exit /b 0

REM ===========================================================================
REM  :matar <porta> <descricao>
REM
REM  Sem blocos entre parenteses de proposito: o cmd faz a expansao de %~2
REM  ANTES de casar os parenteses do bloco, entao uma descricao que contenha
REM  ")" fecharia o "if (" mais cedo e a sub-rotina inteira seria pulada em
REM  silencio - sem erro, sem saida, sem matar nada. Com goto isso nao existe.
REM ===========================================================================
:matar
set "PORTA=%~1"
set "DESC=%~2"
set "ALVO="

for /f "tokens=5" %%p in ('netstat -ano -p TCP ^| findstr /R /C:":%PORTA% " ^| findstr "LISTENING"') do set "ALVO=%%p"

if not defined ALVO goto :ja_livre

taskkill /PID %ALVO% /T /F >nul 2>&1
if errorlevel 1 goto :nao_matou

echo  [ok]   porta %PORTA% liberada, PID %ALVO% - %DESC%
exit /b 0

:ja_livre
echo  [--]   porta %PORTA% ja estava livre - %DESC%
exit /b 0

:nao_matou
echo  [ERRO] nao consegui matar o PID %ALVO% na porta %PORTA% - %DESC%
echo         Se o processo subiu por outro usuario, rode este .bat como
echo         administrador.
exit /b 1
