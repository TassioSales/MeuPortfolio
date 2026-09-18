@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Painel de chamados - WhatsApp Suporte

REM ===========================================================================
REM  Sobe SO o painel de chamados (activity-dashboard\).
REM
REM  Existe porque o painel nao depende do bot para funcionar: ele serve a
REM  pagina e so procura o bot quando alguem pede um chamado. Com o bot fora, o
REM  quadro abre e mostra "bot fora do ar" no lugar dos cartoes - e volta
REM  sozinho quando o bot subir, sem reiniciar nada aqui.
REM
REM  Use quando a janela do painel foi fechada, a maquina reiniciou, ou o
REM  painel vai para o Agendador de Tarefas. Para subir os DOIS, use run.bat.
REM
REM  Diferente do run.bat, o painel roda NESTA janela: fechar a janela para o
REM  painel, e uma tarefa agendada consegue esperar pelo processo em vez de
REM  achar que terminou.
REM
REM  A porta sai do .env - a mesma fonte do run.bat e do bot. Nao ha build, nem
REM  banco, nem migracao: este servidor e so a biblioteca padrao do Node.
REM ===========================================================================

cd /d "%~dp0"

set "ENV_FILE=%~dp0.env"

echo.
echo  ================================================================
echo   PAINEL DE CHAMADOS
echo  ================================================================
echo.

where node >nul 2>&1
if errorlevel 1 goto :sem_node

if not exist "%~dp0activity-dashboard\index.html" goto :sem_pasta

set "PAINEL_PORT="
if exist "%ENV_FILE%" for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"PAINEL_PORT=" "%ENV_FILE%"') do set "PAINEL_PORT=%%b"
if not defined PAINEL_PORT set "PAINEL_PORT=8511"

REM Com certificado no .env o painel sobe em HTTPS, e o endereco deixa de ser
REM localhost: o certificado vale para um nome DNS, que e o mesmo registrado
REM como redirect URI no Entra.
set "PAINEL_URL="
if exist "%ENV_FILE%" for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"PAINEL_URL_BASE=" "%ENV_FILE%"') do set "PAINEL_URL=%%b"
if not defined PAINEL_URL set "PAINEL_URL=http://localhost:%PAINEL_PORT%"

call :porta_ocupada %PAINEL_PORT%
if not errorlevel 1 goto :porta_em_uso

echo   Painel   !PAINEL_URL!
echo.
echo   O modo ^(com ou sem login, HTTP ou HTTPS^) aparece nas linhas
echo   [painel] logo abaixo.
echo   Para parar: feche esta janela, ou Ctrl+C.
echo.
echo  ----------------------------------------------------------------
echo.

REM Sem `start`: o servidor fica NESTA janela. O servidor-painel.mjs le o .env
REM por conta propria, entao a porta do bot sai do mesmo arquivo - este script
REM nao precisa passar nada por ambiente, e nada fica dependendo de ter sido
REM ele a subir o processo.
node servidor-painel.mjs

echo.
echo  O painel encerrou. Se foi por erro, a mensagem esta acima.
pause
exit /b 0

REM ===========================================================================
REM  Sub-rotina: a porta esta ocupada? errorlevel 0 = sim
REM ===========================================================================
:porta_ocupada
set "ACHOU="
for /f "tokens=5" %%p in ('netstat -ano -p TCP ^| findstr /R /C:":%~1 " ^| findstr "LISTENING"') do set "ACHOU=%%p"
if defined ACHOU (
    set "PID_X=!ACHOU!"
    exit /b 0
)
exit /b 1

REM ===========================================================================
REM  Erros - cada um diz o que fazer, nao so o que quebrou
REM ===========================================================================

:sem_node
echo  [ERRO] Node.js nao encontrado no PATH.
echo         Instale a versao 24 LTS ou superior: https://nodejs.org
goto :fim_erro

:sem_pasta
echo  [ERRO] Nao encontrei activity-dashboard\index.html nesta pasta.
echo         Este arquivo precisa ficar na raiz do projeto, ao lado do
echo         servidor-painel.mjs.
goto :fim_erro

:porta_em_uso
echo  [ERRO] A porta %PAINEL_PORT% ja esta em uso (PID !PID_X!).
echo.
echo         O mais provavel e o painel ja estar no ar - tente abrir
echo         http://localhost:%PAINEL_PORT% antes de subir outro.
echo         Se nao for ele, veja quem e:
echo.
echo           tasklist /FI "PID eq !PID_X!"
echo           taskkill /PID !PID_X! /F
goto :fim_erro

:fim_erro
echo.
pause
exit /b 1
