<#
.SYNOPSIS
  Instala a Evolution API no Windows, SEM Docker, e a registra como serviço.

.DESCRIPTION
  Roda como Administrador, no servidor, uma vez. Idempotente.

  POR QUE ESTE SCRIPT EXISTE

  A Evolution é distribuída como imagem Docker. O Windows Server 2016 não roda
  contêiner Linux (o Docker EE dele só executa contêiner Windows, e o LCOW que
  cobria esse caso foi descontinuado), então a imagem não é uma opção nesta
  máquina. O que sobra é o caminho de código-fonte: Node instalado na máquina,
  `npm ci`, build, e o processo vigiado pelo Windows como qualquer serviço.

  É o MESMO desenho que o `instalar.ps1` já usa para o bot e o painel — WinSW,
  conta virtual, log rotativo, restart com recuo. A Evolution vira o terceiro
  serviço do conjunto.

  O QUE ELE FAZ

  1. confere Node, Git e Postgres;
  2. baixa a Evolution na versão pedida (tag fixa, não `latest`);
  3. instala dependências e compila;
  4. escreve o `.env` dela A PARTIR do .env do projeto — o segredo do webhook e
     a apikey são os mesmos dos dois lados por construção, e não por você ter
     copiado certo;
  5. cria o banco e aplica as migrações dela;
  6. registra, sobe e sonda o serviço.

  O QUE ELE NÃO FAZ

  Não instala o Postgres nem o Node: os dois têm instalador próprio e pedem
  decisão (versão, senha do superusuário, diretório de dados) que não cabe a um
  script adivinhar. Ver docs/WA Evolution no Windows.md.

  Não pareia o WhatsApp. Isso é uma vez só, pelo navegador, e vem no fim da
  saída deste script.

.PARAMETER Raiz
  Onde instalar. Fora da pasta do projeto de propósito: é software de terceiro,
  com ciclo de atualização próprio, e não deve entrar no versionamento daqui.

.PARAMETER Versao
  Tag da Evolution. Fixa, e não `latest`: reinstalar daqui a seis meses tem de
  trazer a mesma coisa que está rodando hoje.

.EXAMPLE
  .\instalar-evolution.ps1
  .\instalar-evolution.ps1 -Versao v2.2.3 -Raiz D:\evolution
  .\instalar-evolution.ps1 -Desinstalar
#>
[CmdletBinding()]
param(
  [string]$Raiz = 'C:\evolution',
  [string]$Versao = 'v2.2.3',
  [string]$PostgresHost = '127.0.0.1',
  [int]$PostgresPorta = 5432,
  [string]$PostgresUsuario = 'postgres',
  [string]$PostgresBanco = 'evolution',
  [securestring]$PostgresSenha,
  [switch]$Desinstalar,
  [string]$VersaoWinSW = '3.0.0-alpha.11'
)

$ErrorActionPreference = 'Stop'
$PROJETO = Split-Path -Parent $PSScriptRoot

function Passo($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Ok($t)    { Write-Host "   $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "   $t" -ForegroundColor Yellow }

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
      ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw 'Rode como Administrador: registrar serviço exige elevação.'
}

# --- desinstalar ------------------------------------------------------------

if ($Desinstalar) {
  Passo 'Removendo'
  $exe = Join-Path $Raiz 'evolution.exe'
  if (Test-Path $exe) {
    & $exe stop | Out-Null
    & $exe uninstall | Out-Null
    Ok 'painel-evolution removido'
  } else {
    Aviso "nada a remover em $Raiz"
  }
  Write-Host @"

O SERVIÇO saiu. O que ficou, de propósito:

  $Raiz\instances\   a sessão pareada do WhatsApp
  o banco '$PostgresBanco' no Postgres

Apagar qualquer um dos dois obriga a parear o número de novo, pelo QR Code.
Remova à mão só se for essa a intenção.
"@ -ForegroundColor Cyan
  return
}

# --- pré-requisitos ---------------------------------------------------------

Passo 'Pré-requisitos'

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw 'node não está no PATH da máquina. O serviço roda fora da sua sessão e precisa dele no PATH do SISTEMA, não do usuário.'
}
$verNode = (node -v) -replace '^v', ''
$maiorNode = [int]($verNode -split '\.')[0]
if ($maiorNode -lt 20) {
  throw "A Evolution exige Node 20 ou mais novo; esta máquina tem $verNode."
}
Ok "node v$verNode"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw 'git não está no PATH. É como a Evolution é baixada na versão exata. Instale o Git for Windows.'
}
Ok "git presente"

# O .env do PROJETO é a fonte dos valores compartilhados. Ler dele evita o erro
# mais caro desta instalação: segredo do webhook diferente dos dois lados. Nesse
# caso a Evolution entrega tudo certinho, o bot recusa com 401, e nada no log de
# nenhum dos dois diz "o segredo não bate".
$envProjeto = Join-Path $PROJETO '.env'
if (-not (Test-Path $envProjeto)) {
  throw "Falta o .env em $PROJETO. Ele é lido para alinhar apikey, segredo do webhook e porta do bot."
}

$cfg = @{}
foreach ($linha in Get-Content $envProjeto) {
  if ($linha -match '^\s*#') { continue }
  if ($linha -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
    # Aspas em volta do valor são sintaxe do dotenv, não parte do valor.
    $cfg[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
  }
}

foreach ($chave in @('EVOLUTION_API_KEY', 'WEBHOOK_SEGREDO')) {
  if (-not $cfg[$chave] -or $cfg[$chave] -like 'PREENCHER*' -or $cfg[$chave] -like 'troque_por*') {
    throw "$chave não está preenchida no .env do projeto. Gere um valor longo e aleatório antes de continuar."
  }
}
$apiKey    = $cfg['EVOLUTION_API_KEY']
$segredo   = $cfg['WEBHOOK_SEGREDO']
$portaBot  = if ($cfg['PORT']) { $cfg['PORT'] } else { '9511' }
$instancia = if ($cfg['EVOLUTION_INSTANCIA']) { $cfg['EVOLUTION_INSTANCIA'] } else { 'suporte' }
Ok ".env do projeto lido (instância '$instancia', bot na porta $portaBot)"

# A URL que o bot usa para FALAR com a Evolution tem de apontar para esta
# máquina. Se o .env ainda estiver com a Evolution de mentira (porta 4000), o
# conjunto sobe inteiro e não entrega uma única mensagem - sem erro nenhum.
if ($cfg['EVOLUTION_URL'] -and $cfg['EVOLUTION_URL'] -notmatch ':8080') {
  Aviso "EVOLUTION_URL no .env do projeto e '$($cfg['EVOLUTION_URL'])'."
  Aviso "Depois desta instalacao ela precisa ser http://127.0.0.1:8080 - anote."
}

if (-not $PostgresSenha) {
  $PostgresSenha = Read-Host "Senha do usuário '$PostgresUsuario' no Postgres" -AsSecureString
}
$senhaTexto = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($PostgresSenha))

# Só confirma que o Postgres ATENDE. Criar o banco vem depois; aqui o objetivo é
# falhar cedo, antes de baixar algumas centenas de MB à toa.
$sonda = Test-NetConnection -ComputerName $PostgresHost -Port $PostgresPorta -WarningAction SilentlyContinue
if (-not $sonda.TcpTestSucceeded) {
  throw "Nada atende em ${PostgresHost}:${PostgresPorta}. A Evolution exige Postgres (ela não usa SQLite). Ver docs/WA Evolution no Windows.md."
}
Ok "postgres respondendo em ${PostgresHost}:${PostgresPorta}"

# --- baixar -----------------------------------------------------------------

Passo "Evolution $Versao"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (Test-Path (Join-Path $Raiz '.git')) {
  Ok "já existe em $Raiz - atualizando para $Versao"
  Push-Location $Raiz
  try {
    & git fetch --tags --quiet
    & git checkout --quiet $Versao
  } finally { Pop-Location }
} else {
  if (Test-Path $Raiz) {
    $vazia = -not (Get-ChildItem $Raiz -Force -ErrorAction SilentlyContinue)
    if (-not $vazia) { throw "$Raiz existe, tem conteúdo e não é um clone da Evolution. Escolha outro -Raiz ou esvazie a pasta." }
  }
  & git clone --depth 1 --branch $Versao https://github.com/EvolutionAPI/evolution-api.git $Raiz
  if ($LASTEXITCODE -ne 0) { throw "git clone falhou. Confira se a tag '$Versao' existe em github.com/EvolutionAPI/evolution-api/tags." }
}
Ok "código em $Raiz"

# --- .env da Evolution ------------------------------------------------------

Passo 'Configuração'

# Redis fica DESLIGADO: ele não tem build oficial para Windows, e a Evolution
# funciona com o cache em memória do próprio processo. O que se perde é
# compartilhar cache entre várias instâncias dela - e aqui só existe uma.
# A senha entra numa URL, entao precisa ser percent-encoded: um `@` ou `:` cru
# corta a URL no lugar errado e o erro que aparece e "host desconhecido", que nao
# tem nada a ver com a senha.
$senhaUrl = [uri]::EscapeDataString($senhaTexto)
$usuarioUrl = [uri]::EscapeDataString($PostgresUsuario)
$urlBanco = "postgresql://${usuarioUrl}:${senhaUrl}@${PostgresHost}:${PostgresPorta}/${PostgresBanco}?schema=public"

# O webhook aponta para o BOT, direto. O desvio pelo painel que o GOLIVE.md
# descreve existe porque lá fora uma porta pública atende os dois; aqui os três
# processos estão na mesma máquina e a Evolution alcança o bot em 127.0.0.1.
$conteudoEnv = @"
# Gerado por servicos/instalar-evolution.ps1. Reinstalar sobrescreve.
SERVER_TYPE=http
SERVER_PORT=8080
SERVER_URL=http://127.0.0.1:8080

AUTHENTICATION_API_KEY=$apiKey

DATABASE_ENABLED=true
DATABASE_PROVIDER=postgresql
DATABASE_CONNECTION_URI=$urlBanco
DATABASE_CONNECTION_CLIENT_NAME=evolution_exchange
DATABASE_SAVE_DATA_INSTANCE=true
DATABASE_SAVE_DATA_NEW_MESSAGE=true
DATABASE_SAVE_MESSAGE_UPDATE=true
DATABASE_SAVE_DATA_CONTACTS=true
DATABASE_SAVE_DATA_CHATS=true

# Sem Redis no Windows: cache no proprio processo.
CACHE_REDIS_ENABLED=false
CACHE_LOCAL_ENABLED=true

# Webhook global: vale para qualquer instancia, inclusive uma recriada depois.
# O segredo vai no CAMINHO porque a Evolution nao assina o corpo (ver o
# comentario em src/config.ts do projeto).
WEBHOOK_GLOBAL_ENABLED=true
WEBHOOK_GLOBAL_URL=http://127.0.0.1:$portaBot/webhook/$segredo
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false

LOG_LEVEL=ERROR,WARN,INFO
LOG_COLOR=false
DEL_INSTANCE=false
QRCODE_LIMIT=30
"@

$envEvolution = Join-Path $Raiz '.env'
Set-Content -Path $envEvolution -Value $conteudoEnv -Encoding UTF8

# Este arquivo guarda a senha do Postgres e a apikey em texto puro. Herdar as
# permissoes de C:\ deixaria qualquer usuario da maquina le-lo. Quebra a heranca
# e deixa so quem precisa: SYSTEM, Administradores e a conta do servico - esta
# ultima so depois do `install`, mais abaixo.
& icacls $envEvolution /inheritance:r /Q | Out-Null
& icacls $envEvolution /grant 'SYSTEM:(R)' 'BUILTIN\Administrators:(F)' /Q | Out-Null
Ok '.env da Evolution escrito, leitura restrita (apikey e segredo vieram do .env do projeto)'

foreach ($d in @('logs', 'instances')) {
  $p = Join-Path $Raiz $d
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

# --- banco ------------------------------------------------------------------

Passo 'Banco'

$psql = Get-Command psql -ErrorAction SilentlyContinue
if ($psql) {
  $env:PGPASSWORD = $senhaTexto
  $existe = & psql -h $PostgresHost -p $PostgresPorta -U $PostgresUsuario -tAc `
    "SELECT 1 FROM pg_database WHERE datname='$PostgresBanco'" 2>$null
  if ($existe -ne '1') {
    & psql -h $PostgresHost -p $PostgresPorta -U $PostgresUsuario -c "CREATE DATABASE $PostgresBanco" | Out-Null
    Ok "banco '$PostgresBanco' criado"
  } else {
    Ok "banco '$PostgresBanco' já existe"
  }
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
} else {
  Aviso "psql não está no PATH - não deu para criar o banco automaticamente."
  Aviso "Crie à mão antes de seguir:  CREATE DATABASE $PostgresBanco;"
}

# --- instalar e compilar ----------------------------------------------------

Passo 'Dependências e build'

Push-Location $Raiz
try {
  # `npm ci` exige lockfile e respeita as versões exatas; é o certo aqui. Se a
  # tag não trouxer lockfile, `npm install` resolve - com o aviso, porque aí a
  # árvore instalada pode não ser a mesma da próxima vez.
  if (Test-Path (Join-Path $Raiz 'package-lock.json')) {
    & npm ci
  } else {
    Aviso 'sem package-lock.json na tag - usando npm install'
    & npm install
  }
  if ($LASTEXITCODE -ne 0) { throw 'npm falhou ao instalar as dependências. A saída acima diz qual pacote.' }

  # Os nomes dos scripts variam entre versões da Evolution, então em vez de
  # chutar, lemos o package.json dela e usamos o que existir.
  $pkg = Get-Content (Join-Path $Raiz 'package.json') -Raw | ConvertFrom-Json
  $scripts = $pkg.scripts

  foreach ($nome in @('db:generate', 'db:deploy', 'prisma:generate', 'prisma:deploy')) {
    if ($scripts.PSObject.Properties.Name -contains $nome) {
      Ok "npm run $nome"
      & npm run $nome
      if ($LASTEXITCODE -ne 0) { throw "npm run $nome falhou - normalmente é a URL do banco ou permissão do usuário do Postgres." }
    }
  }

  if ($scripts.PSObject.Properties.Name -contains 'build') {
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'npm run build falhou.' }
  }
} finally { Pop-Location }
Ok 'compilada'

# --- qual arquivo o serviço executa ----------------------------------------

Passo 'Entrada'

# Onde fica o arquivo compilado muda entre versões (dist/main.js, dist/src/main.js...).
# Procurar é mais honesto que fixar um caminho que numa atualização vira "cannot
# find module" DEPOIS de o serviço já ter sido registrado.
$candidatos = @('dist\main.js', 'dist\src\main.js', 'dist\index.js', 'dist\server.js')
$entrada = $null
foreach ($c in $candidatos) {
  if (Test-Path (Join-Path $Raiz $c)) { $entrada = $c; break }
}
if (-not $entrada) {
  $achado = Get-ChildItem (Join-Path $Raiz 'dist') -Filter '*.js' -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 5 -ExpandProperty FullName
  throw @"
Não achei o arquivo de entrada compilado em $Raiz\dist.
Procurei por: $($candidatos -join ', ')
O que existe lá: $($achado -join ', ')
Ajuste <arguments> no evolution.xml para o arquivo certo e rode de novo.
"@
}
Ok "node $entrada"

# --- WinSW ------------------------------------------------------------------

Passo 'WinSW'
$exe = Join-Path $Raiz 'evolution.exe'
if (-not (Test-Path $exe)) {
  $tmp = Join-Path $env:TEMP 'WinSW.exe'
  if (-not (Test-Path $tmp)) {
    Invoke-WebRequest -UseBasicParsing -OutFile $tmp `
      -Uri "https://github.com/winsw/winsw/releases/download/v$VersaoWinSW/WinSW-x64.exe"
  }
  # O WinSW acha a própria configuração pelo NOME: evolution.exe procura evolution.xml.
  Copy-Item $tmp $exe
}
Ok 'evolution.exe'

# O nome do serviço do Postgres muda com a versão do instalador. Sem acertá-lo,
# o <depend> aponta para um serviço inexistente e o Windows recusa a iniciar a
# Evolution - com um erro que fala de dependência, não de Postgres.
$svcPg = Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue | Select-Object -First 1
$xml = Get-Content (Join-Path $PSScriptRoot 'evolution.xml') -Raw
$xml = $xml.Replace('__RAIZ_EVOLUTION__', $Raiz).Replace('__ENTRADA__', $entrada)
if ($svcPg) {
  $xml = $xml.Replace('__SERVICO_POSTGRES__', $svcPg.Name)
  Ok "dependência: $($svcPg.Name)"
} else {
  $xml = $xml -replace '(?m)^\s*<depend>__SERVICO_POSTGRES__</depend>\r?\n', ''
  Aviso 'nenhum serviço postgresql* encontrado - <depend> removido; no boot a Evolution pode reiniciar até o banco subir'
}
Set-Content -Path (Join-Path $Raiz 'evolution.xml') -Value $xml -Encoding UTF8
Ok 'evolution.xml gerado'

# --- registrar --------------------------------------------------------------

Passo 'Serviço'
if (Get-Service -Name 'painel-evolution' -ErrorAction SilentlyContinue) {
  & $exe stop | Out-Null
  & $exe uninstall | Out-Null
  Start-Sleep -Seconds 2
}
& $exe install | Out-Null
Ok 'painel-evolution registrado'

# --- permissões -------------------------------------------------------------

Passo 'Permissões'
# A conta virtual só existe depois do install. `instances\` é onde a sessão
# pareada é gravada: sem escrita ali, a Evolution sobe, mostra o QR Code, você
# pareia, e o pareamento se perde no primeiro restart.
& icacls $Raiz /grant "NT SERVICE\painel-evolution:(OI)(CI)M" /T /Q | Out-Null
# O .env teve a heranca quebrada acima, entao o grant recursivo nao o alcancou:
# ele precisa do seu proprio, e de leitura apenas.
& icacls $envEvolution /grant "NT SERVICE\painel-evolution:(R)" /Q | Out-Null
Ok 'escrita em instances\ e logs\, leitura no .env'

# --- subir ------------------------------------------------------------------

Passo 'Subindo'
Start-Service painel-evolution
Start-Sleep -Seconds 8
Get-Service painel-evolution | Select-Object Name, Status, StartType | Format-Table -AutoSize

Passo 'Sonda'
try {
  $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8080' -TimeoutSec 10
  Ok "evolution: HTTP $($r.StatusCode)"
} catch {
  Aviso "evolution não respondeu: $($_.Exception.Message)"
  Aviso "veja $Raiz\logs\ - a Evolution registra ali o motivo real"
}

Write-Host @"

Pronto. A Evolution sobe sozinha no boot, depois do Postgres.

FALTAM DOIS PASSOS, e nenhum script faz por você:

1. APONTE O BOT PARA ELA
   No .env do projeto ($envProjeto):

     EVOLUTION_URL=http://127.0.0.1:8080
     EVOLUTION_INSTANCIA=$instancia

   Depois:  Restart-Service painel-bot

2. PAREIE O NÚMERO (uma vez só)
   Crie a instância e leia o QR Code:

     `$h = @{ apikey = '<EVOLUTION_API_KEY do .env>' }
     Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8080/instance/create ``
       -Headers `$h -ContentType application/json ``
       -Body '{"instanceName":"$instancia","integration":"WHATSAPP-BAILEYS","qrcode":true}'

   Leia o QR com o celular em Aparelhos conectados. Confirme com:

     Invoke-RestMethod -Uri http://127.0.0.1:8080/instance/connectionState/$instancia -Headers `$h

   'open' = conectado.

  Estado:   Get-Service painel-evolution, painel-bot, painel-web
  Log:      $Raiz\logs\
  Parar:    Stop-Service painel-evolution
  Remover:  .\instalar-evolution.ps1 -Desinstalar

Passo a passo completo: docs/WA Evolution no Windows.md
"@ -ForegroundColor Cyan
