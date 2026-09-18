@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Go-live - WhatsApp Suporte + Painel de Chamados

REM ===========================================================================
REM  Sobe os dois servicos do go-live, NESTA janela (ver iniciar.mjs):
REM
REM    PORT         - bot (este projeto)   <- e para CA que a Meta aponta
REM    PAINEL_PORT  - painel de chamados (activity-dashboard\)
REM
REM  As duas saem do .env. Sem elas: 8511 para o painel, 9511 para o bot.
REM
REM  O PAINEL fica na 8511 porque e para la que o tunel da Cloudflare aponta -
REM  e, como ele repassa /webhook e /internal/* para o bot, uma porta publica
REM  atende os dois. O BOT foi para a 9511, fora da faixa 8500-8600 que o
REM  servidor reservou para outros servicos.
REM
REM  O painel repassa /internal/* para o bot, entao os dois ficam na mesma
REM  origem para o navegador e nao existe CORS no caminho.
REM
REM  Na SUBIDA, porem, um nao depende do outro: se o bot falhar, o painel
REM  sobe do mesmo jeito e diz no quadro o que falta. Para subir so o painel
REM  - janela fechada, maquina reiniciada, tarefa agendada - use painel.bat.
REM
REM  CONFIGURACAO: um arquivo so, o .env desta pasta - o mesmo que o
REM  `npm run dev` usa. Nao existe .env.producao nem nada paralelo.
REM
REM  Antes de subir, este script CONFERE o que costuma derrubar um go-live:
REM  Node ausente ou velho, .env sem preencher, porta ocupada,
REM  migracao pendente, build desatualizado. Falha aqui e barata; falha depois
REM  que a Meta ja esta apontando para a maquina, nao.
REM ===========================================================================

cd /d "%~dp0"

set "ENV_FILE=%~dp0.env"
set "NODE_MIN=24"

echo.
echo  ================================================================
echo  -  bot + painel de chamados
echo  ================================================================
echo.

REM --- 1. Node ---------------------------------------------------------------
where node >nul 2>&1
if errorlevel 1 goto :sem_node

for /f "tokens=1 delims=." %%v in ('node -v') do set "NODE_MAJ=%%v"
set "NODE_MAJ=!NODE_MAJ:v=!"
if !NODE_MAJ! LSS %NODE_MIN% goto :node_velho

for /f %%v in ('node -v') do echo  [ok]   Node %%v

where npm >nul 2>&1
if errorlevel 1 goto :sem_npm

REM --- 2. .env ------------------------------------------------------
if not exist "%ENV_FILE%" goto :sem_env

REM O ^[^#]* nao e decoracao: sem ele o proprio comentario do .env que
REM explica os PREENCHER_ casaria aqui, e o run.bat recusaria subir para
REM sempre - apontando uma linha de comentario como pendencia.
findstr /R /C:"^[^#]*PREENCHER_" "%ENV_FILE%" >nul 2>&1
if not errorlevel 1 goto :env_incompleto

echo  [ok]   .env preenchido

REM --- 2b. WEBHOOK_SEGREDO: o tamanho ---------------------------------------
REM Este valor e a UNICA coisa que separa "a Evolution mandou" de "qualquer um
REM que descobriu a URL mandou". Com a Meta havia um HMAC sobre o corpo; aqui
REM ha um segredo no caminho, e so. Curto demais, ele e adivinhavel.
REM
REM Por que isso merece parar o go-live: um segredo errado NAO impede o bot de
REM subir. O /health e o /ready respondem, o painel funciona, e so os webhooks
REM da Evolution voltam 404 - em silencio. O sintoma e "o WhatsApp nao
REM responde", sem uma linha de erro em lugar nenhum.
set "WH_SEGREDO="
for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"WEBHOOK_SEGREDO=" "%ENV_FILE%"') do set "WH_SEGREDO=%%b"
if not defined WH_SEGREDO goto :sem_webhook_segredo
call :tamanho "!WH_SEGREDO!"
if !TAMANHO! LSS 16 goto :segredo_curto
echo  [ok]   WEBHOOK_SEGREDO com !TAMANHO! caracteres

REM --- 2c. Login pelo Entra ID: tudo ou nada ---------------------------------
REM O painel-entra.mjs ENCERRA o processo quando so parte das variaveis esta
REM preenchida - de proposito, para ninguem ficar sem a protecao que pediu.
REM Conferir aqui troca "o painel morreu numa janela que ninguem leu" por uma
REM lista do que falta preencher.
REM
REM Linha comentada nao conta: o /B do findstr ancora no inicio da linha, e as
REM linhas do bloco de exemplo comecam com "# ".
set "ENTRA_N=0"
for %%v in (ENTRA_TENANT_ID ENTRA_CLIENT_ID ENTRA_CLIENT_SECRET PAINEL_URL_BASE) do (
    findstr /B /C:"%%v=" "%ENV_FILE%" >nul 2>&1
    if not errorlevel 1 set /a ENTRA_N+=1
)
if !ENTRA_N! GTR 0 if !ENTRA_N! LSS 4 goto :entra_incompleto
if "!ENTRA_N!"=="4" (
    findstr /B /C:"PAINEL_SESSAO_SEGREDO=" "%ENV_FILE%" >nul 2>&1
    if errorlevel 1 goto :entra_sem_segredo
    echo  [ok]   login pelo Entra ID configurado
)

REM --- 3. Portas: as duas saem do .env --------------------------------------

REM  QUEM FICA ONDE, e por que
REM
REM    painel  8511  <- FIXO. E a porta que o tunel da Cloudflare aponta, e
REM                     mudar aquilo e mais caro do que mudar isto aqui.
REM                     Como o painel repassa /webhook e /internal/* para o
REM                     bot, uma porta publica basta para os dois.
REM    bot     9511  <- interno, nao aparece na internet. Saiu da faixa
REM                     8500-8600, reservada a outros servicos do servidor.
set "BOT_PORT="
for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"PORT=" "%ENV_FILE%"') do set "BOT_PORT=%%b"
if not defined BOT_PORT (
    set "BOT_PORT=9511"
    echo  [AVISO] o .env nao define PORT, e o padrao do bot NAO e 9511 - e
    echo          3000 ^(src/config.ts^). Fixando 9511 nesta subida.
    echo          Grave PORT no .env para nao depender deste padrao.
)

set "PAINEL_PORT="
for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"PAINEL_PORT=" "%ENV_FILE%"') do set "PAINEL_PORT=%%b"
if not defined PAINEL_PORT set "PAINEL_PORT=8511"

REM Duas portas iguais nao param em nenhuma checagem adiante: a sonda do
REM /health seria respondida pelo servico errado, e o painel repassaria
REM /internal/* para ele mesmo. Conferir aqui e barato.
if "%BOT_PORT%"=="%PAINEL_PORT%" goto :portas_iguais

REM O painel na 8511 e o que faz o tunel continuar valendo sem edicao. Se
REM alguem trocar isto, o dominio passa a bater no bot - que nao tem rota `/`
REM e responde {"erro":"rota nao encontrada"}, com o painel inacessivel e o
REM login do Entra quebrado. Ja aconteceu; e um aviso, e nao um erro, porque
REM mudar o ingress do tunel e uma decisao legitima.
if not "%PAINEL_PORT%"=="8511" (
    echo  [AVISO] PAINEL_PORT=%PAINEL_PORT%, e nao 8511.
    echo          O tunel da Cloudflare aponta para a 8511: se ele nao for
    echo          reapontado, o dominio vai bater no bot e o painel fica
    echo          inacessivel.
)

REM A faixa 8500-8600 e reservada a outros servicos deste servidor. A 8511 e a
REM excecao, carimbada para o painel porque o tunel ja apontava para ela - o
REM BOT, esse, tem de ficar fora da faixa. A checagem pega o caso que ja
REM aconteceu: PORT e PAINEL_PORT trocados de lugar, os dois numeros certos nos
REM papeis errados, com sintoma de "bot fora do ar" que parece falha do bot.
set "BOT_NA_FAIXA="
if %BOT_PORT% GEQ 8500 if %BOT_PORT% LEQ 8600 set "BOT_NA_FAIXA=1"
if defined BOT_NA_FAIXA goto :bot_na_faixa_reservada

echo  [ok]   painel na porta %PAINEL_PORT%, bot na %BOT_PORT%  ^(do .env^)


REM --- 3b. HTTPS e endereco do painel ----------------------------------------
REM Com certificado no .env, o painel sobe em HTTPS. A sonda e a URL do resumo
REM tem de acompanhar: sondando http numa porta TLS, este script diria que o
REM painel nao respondeu enquanto ele responde muito bem, do outro lado.
set "PAINEL_ESQUEMA=http"
set "CURL_TLS="
findstr /B /C:"PAINEL_TLS_CERT=" "%ENV_FILE%" >nul 2>&1
if not errorlevel 1 (
    set "PAINEL_ESQUEMA=https"
    REM -k porque o certificado costuma sair da CA interna do dominio, que o
    REM curl nao conhece. A sonda so quer saber se ALGUEM atende ali.
    set "CURL_TLS=-k"
)

REM O endereco que as pessoas usam. Em HTTPS ele NAO e localhost: o certificado
REM vale para um nome DNS, e e esse nome que o Entra tem registrado.
set "PAINEL_URL="
for /f "tokens=1,* delims==" %%a in ('findstr /B /C:"PAINEL_URL_BASE=" "%ENV_FILE%"') do set "PAINEL_URL=%%b"
if not defined PAINEL_URL set "PAINEL_URL=!PAINEL_ESQUEMA!://localhost:%PAINEL_PORT%"

REM --- 4. Portas livres ------------------------------------------------------
call :porta_ocupada %BOT_PORT%
if not errorlevel 1 (
    set "PORTA_X=%BOT_PORT%"
    goto :porta_em_uso
)
call :porta_ocupada %PAINEL_PORT%
if not errorlevel 1 (
    set "PORTA_X=%PAINEL_PORT%"
    goto :porta_em_uso
)
echo  [ok]   portas %BOT_PORT% e %PAINEL_PORT% livres

REM --- 5. Dependencias -------------------------------------------------------
REM  Conferir uma pasta so (era node_modules\fastify) nao basta: um npm ci
REM  interrompido - ou o OneDrive que ainda nao baixou os arquivos desta
REM  pasta - deixa node_modules PELA METADE, com fastify presente e outro
REM  pacote faltando. O script dizia "dependencias presentes" e a falha
REM  reaparecia tres passos depois, no build, como um TS2307 em
REM  @prisma/adapter-better-sqlite3 - erro que parece de codigo e nao e.
REM  `npm ls` confere a arvore de producao INTEIRA contra o package.json,
REM  nao usa rede e leva cerca de 1,5s.
call npm ls --omit=dev --all >nul 2>&1
if not errorlevel 1 goto :deps_ok

echo  [..]   instalando dependencias (npm ci) - pode demorar
call npm ci
if errorlevel 1 goto :falhou_npm

:deps_ok
echo  [ok]   dependencias presentes

REM --- 6. Prisma: cliente + migracoes ----------------------------------------
echo  [..]   gerando o cliente do Prisma
call npx prisma generate >nul 2>&1
if errorlevel 1 (
    echo         falhou; repetindo para mostrar o erro:
    call npx prisma generate
    goto :falhou_prisma
)
echo  [ok]   cliente do Prisma gerado

echo  [..]   aplicando migracoes no banco (prisma migrate deploy)
call npx prisma migrate deploy
if errorlevel 1 goto :falhou_migracao
echo  [ok]   banco na versao das migracoes

REM --- 7. Build --------------------------------------------------------------
echo  [..]   compilando o TypeScript (npm run build)
call npm run build
if errorlevel 1 goto :falhou_build
if not exist "%~dp0dist\server.js" goto :falhou_build
echo  [ok]   build pronto

REM --- 8. Sobe os dois servicos, NESTA janela --------------------------------
REM Um terminal so, e nao tres. Antes eram duas janelas novas (`start cmd /k`)
REM mais esta - e tres janelas custam mais do que parecem: ninguem sabe qual
REM olhar quando algo falha, fechar a errada derruba metade do sistema sem
REM aviso, e a maquina reiniciada volta sem nenhuma delas.
REM
REM O iniciar.mjs sobe o bot e o painel como FILHOS dele, marca cada linha de
REM log com a origem ([bot   ] / [painel]) e encerra os dois com um Ctrl+C.
REM As sondas de /health, /ready e do painel foram para la junto: quem sobe e
REM quem confere que subiu tem de ser o mesmo processo.
REM
REM Daqui em diante quem manda na janela e o supervisor. Este script so volta
REM a rodar quando ele terminar.
echo.
echo  [ok]   ambiente conferido - passando o bastao para o supervisor
echo.

node "%~dp0iniciar.mjs"
set "SAIDA=%ERRORLEVEL%"

echo.
echo  ================================================================
echo   Aplicacao encerrada.
echo  ================================================================
echo.
REM Sem `pause` quando saiu limpo: quem deu Ctrl+C quis fechar, e mais uma
REM tecla so atrasa. Com falha, a janela fica de pe para a mensagem ser lida.
if not "%SAIDA%"=="0" pause
exit /b %SAIDA%


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
REM  Sub-rotina: tamanho de uma string, devolvido em !TAMANHO!
REM
REM  O cmd nao tem funcao de tamanho: o jeito e comer um caractere por vez.
REM  Sao 32 voltas no caso bom, entao o custo nao aparece.
REM ===========================================================================
:tamanho
set "STR=%~1"
set "TAMANHO=0"
:tamanho_conta
if not defined STR exit /b 0
set "STR=!STR:~1!"
set /a TAMANHO+=1
goto :tamanho_conta

REM ===========================================================================
REM  Erros - cada um diz o que fazer, nao so o que quebrou
REM ===========================================================================

:sem_webhook_segredo
echo  [ERRO] O .env nao tem a linha WEBHOOK_SEGREDO.
echo         E voce que escolhe o valor: uma string longa e aleatoria, sem
echo         acento e sem barra. Ele vira o final da URL que voce cadastra
echo         na Evolution:
echo           https://SEU_DOMINIO/webhook/^<WEBHOOK_SEGREDO^>
echo         Sem ela o bot nem sobe: a variavel e obrigatoria.
goto :fim_erro

:segredo_curto
echo  [ERRO] WEBHOOK_SEGREDO tem so !TAMANHO! caracteres.
echo.
echo         Ele e a UNICA prova de que o POST veio da sua instancia da
echo         Evolution - nao ha assinatura de corpo para conferir junto.
echo         Curto demais, ele e adivinhavel, e quem acertar abre chamado
echo         em nome de qualquer numero.
echo.
echo         Use 32 caracteres ou mais. Para gerar um:
echo           node -e "console.log(require('crypto').randomBytes(24).toString('hex'))"
goto :fim_erro

:entra_incompleto
echo  [ERRO] O login pelo Entra ID esta configurado pela metade
echo         ^(!ENTRA_N! de 4 variaveis preenchidas^).
echo.
echo         O painel se RECUSA a subir nesse estado, de proposito: ficar de
echo         pe sem a protecao que alguem pediu e pior que nao subir.
echo.
echo         Preencha as quatro, ou apague/comente todas para subir sem login:
echo           ENTRA_TENANT_ID       Azure ^> Entra ID ^> Overview ^> Directory ID
echo           ENTRA_CLIENT_ID       o Application ^(client^) ID do App Registration
echo           ENTRA_CLIENT_SECRET   Certificates ^& secrets ^> New client secret
echo           PAINEL_URL_BASE       o endereco publico do painel, com https
goto :fim_erro

:entra_sem_segredo
echo  [ERRO] Falta PAINEL_SESSAO_SEGREDO no .env.
echo.
echo         Com o login ligado ele passa a ser obrigatorio: e o que assina o
echo         cookie de sessao. Sem ele, qualquer um poderia forjar uma sessao -
echo         pior que nao ter login. Gerar um a cada subida tambem nao serve:
echo         deslogaria todo mundo em cada reinicio.
echo.
echo         Gere o seu:
echo           node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
goto :fim_erro

:sem_node
echo  [ERRO] Node.js nao encontrado no PATH.
echo         Instale a versao %NODE_MIN% LTS ou superior: https://nodejs.org
goto :fim_erro

:node_velho
for /f %%v in ('node -v') do echo  [ERRO] Node %%v e antigo demais.
echo         O projeto exige Node ^>= %NODE_MIN% (package.json, campo "engines").
echo         Instale o Node %NODE_MIN% LTS: https://nodejs.org
goto :fim_erro

:sem_npm
echo  [ERRO] npm nao encontrado no PATH, apesar de o node existir.
echo         Reinstale o Node.js pelo instalador oficial (ele traz o npm).
goto :fim_erro

:sem_env
echo  [ERRO] Nao existe .env nesta pasta.
echo.
echo         Crie um a partir do exemplo:
echo.
echo           copy .env.example .env
echo.
echo         e ajuste, no minimo: PORT ^(porta do bot^), os tres valores da
echo         Meta e os tokens. O DATABASE_URL ja vem funcionando ^(e um
echo         arquivo local, nao um servidor^). Veja GOLIVE.md.
goto :fim_erro

:env_incompleto
echo  [ERRO] O .env ainda tem valores por preencher. Estas linhas:
echo.
findstr /N /R /C:"^[^#]*PREENCHER_" "%ENV_FILE%"
echo.
echo         Abra  .env  e troque cada uma pelo valor real:
echo.
echo           EVOLUTION_URL             endereco da sua Evolution, com https
echo                                     e sem barra no fim.
echo           EVOLUTION_API_KEY         a AUTHENTICATION_API_KEY da instalacao,
echo                                     ou o token da instancia.
echo           EVOLUTION_INSTANCIA       o nome da instancia conectada
echo                                     ^(o que aparece em /instance/fetchInstances^).
echo.
echo         Os demais tokens (WEBHOOK_SEGREDO, INTERNAL_API_TOKEN, PAINEL_TOKEN)
echo         ja vieram gerados - nao precisa mexer.
goto :fim_erro

:portas_iguais
echo  [ERRO] PORT e PAINEL_PORT valem a mesma porta ^(%BOT_PORT%^) no .env.
echo         O bot e o painel nao podem dividir porta: o painel repassa
echo         /internal/* para o bot, entao um teria de responder pelo outro.
echo         Ajuste PAINEL_PORT no .env.
goto :fim_erro

:bot_na_faixa_reservada
echo  [ERRO] PORT=%BOT_PORT%, dentro da faixa 8500-8600.
echo.
echo         Essa faixa esta reservada para outros servicos deste servidor. A
echo         unica excecao e a 8511, carimbada para o PAINEL - e para onde o
echo         tunel da Cloudflare aponta. O bot fica fora da faixa:
echo.
echo           PAINEL_PORT=8511   o painel  ^(publico, pelo tunel^)
echo           PORT=9511          o bot     ^(interno^)
echo.
echo         Se PORT=8511, os dois estao TROCADOS no .env: o painel sobe na
echo         porta do bot e vai procurar o bot na 9511, onde nao ha ninguem.
echo         O sintoma e o quadro abrir com "HTTP 502" e zero chamados - que
echo         parece falha de banco, e e so a porta errada.
echo.
echo         Para usar outra porta para o bot, so troque PORT ^(fora da faixa^).
goto :fim_erro

:porta_em_uso
echo  [ERRO] A porta %PORTA_X% ja esta em uso (PID !PID_X!).
echo.
echo         Duas causas comuns: um servico de uma execucao anterior ainda
echo         rodando, ou o `npm run dev` aberto noutra janela.
echo         Rode parar.bat, ou veja quem e:
echo.
echo           tasklist /FI "PID eq !PID_X!"
echo           taskkill /PID !PID_X! /F
goto :fim_erro

:falhou_npm
echo  [ERRO] npm ci falhou.
echo         Causa comum: a maquina nao alcanca o registry do npm.
echo         Se nao ha internet aqui, copie a pasta node_modules de uma
echo         maquina onde o `npm ci` ja rodou.
goto :fim_erro

:falhou_prisma
echo  [ERRO] prisma generate falhou (mensagem acima).
echo         Se reclamou de DATABASE_URL, o valor no .env esta mal
echo         formado - mantenha as aspas e o prefixo file::
echo           DATABASE_URL="file:./dados/whatsapp-suporte.db"
goto :fim_erro

:falhou_migracao
echo  [ERRO] prisma migrate deploy falhou - o banco NAO foi migrado.
echo.
echo         O banco e um arquivo SQLite: nao ha servidor para subir, nem
echo         senha, nem banco para criar antes. Confira, nesta ordem:
echo           1. o DATABASE_URL do .env comeca com file: e aponta para um
echo              caminho gravavel - o padrao e file:./dados/whatsapp-suporte.db;
echo           2. nenhum outro processo esta com o arquivo aberto (outro
echo              `npm run dev`, um sqlite3) - SQLite aceita um escritor;
echo           3. se a mensagem falou em "unable to open database file", o
echo              problema e permissao na pasta, nao a migracao.
echo.
echo         Nada foi subido: sem banco migrado o bot perderia os chamados.
goto :fim_erro

:falhou_build
echo  [ERRO] O build falhou (mensagem acima) e dist\server.js nao existe.
echo         Nada foi subido - o bot rodaria com codigo desatualizado.
goto :fim_erro

:fim_erro
echo.
pause
exit /b 1
