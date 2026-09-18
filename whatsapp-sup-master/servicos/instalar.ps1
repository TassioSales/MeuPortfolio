<#
.SYNOPSIS
  Registra o bot e o painel como serviços do Windows. Substitui o run.bat.

.DESCRIPTION
  Roda como Administrador, no servidor, uma vez. Idempotente.

  O QUE ISTO RESOLVE

  O `run.bat` sobe os dois processos e pronto — a própria WA Implantação
  registrava: "se a máquina reiniciar, alguém precisa rodá-lo de novo". Como
  serviço, os dois sobem no boot sem ninguém logado, reiniciam sozinhos se
  morrerem, e param de forma ordenada (o que importa: é no fechamento que o WAL
  do SQLite é incorporado ao arquivo).

  O `run.bat` continua útil para desenvolvimento e para o primeiro teste
  manual — só deixa de ser o caminho de produção.

.EXAMPLE
  .\instalar.ps1
  .\instalar.ps1 -Desinstalar
#>
[CmdletBinding()]
param(
  [switch]$Desinstalar,
  [string]$VersaoWinSW = '3.0.0-alpha.11'
)

$ErrorActionPreference = 'Stop'
$RAIZ = Split-Path -Parent $PSScriptRoot
$SERVICOS = @('bot', 'painel')

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
  # Ordem inversa da dependência: o painel depende do bot.
  foreach ($s in @('painel', 'bot')) {
    $exe = Join-Path $PSScriptRoot "$s.exe"
    if (Test-Path $exe) {
      & $exe stop | Out-Null
      & $exe uninstall | Out-Null
      Ok "$s removido"
    }
  }
  Write-Host "`nOs dados em dados\ NÃO foram tocados." -ForegroundColor Cyan
  return
}

# --- pré-requisitos ---------------------------------------------------------

Passo 'Pré-requisitos'

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw 'node não está no PATH da máquina. O serviço roda fora da sua sessão e precisa dele no PATH do SISTEMA, não do usuário.'
}
Ok "node $(node -v)"

if (-not (Test-Path (Join-Path $RAIZ '.env'))) {
  throw "Falta o .env em $RAIZ."
}
Ok '.env presente'

# `dist/` é gerado pelo tsc — sem ele o serviço sobe e morre em "cannot find module".
if (-not (Test-Path (Join-Path $RAIZ 'dist\server.js'))) {
  Aviso 'dist\server.js não existe — rodando npm run build'
  Push-Location $RAIZ
  try { & npm run build | Out-Null } finally { Pop-Location }
}
Ok 'dist\ pronto'

foreach ($d in @('dados', 'dados\logs')) {
  $p = Join-Path $RAIZ $d
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

# --- WinSW ------------------------------------------------------------------

Passo 'WinSW'
foreach ($s in $SERVICOS) {
  $exe = Join-Path $PSScriptRoot "$s.exe"
  if (Test-Path $exe) { Aviso "$s.exe já presente"; continue }
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $tmp = Join-Path $env:TEMP 'WinSW.exe'
  if (-not (Test-Path $tmp)) {
    Invoke-WebRequest -UseBasicParsing -OutFile $tmp `
      -Uri "https://github.com/winsw/winsw/releases/download/v$VersaoWinSW/WinSW-x64.exe"
  }
  # O WinSW acha a própria configuração pelo NOME: bot.exe procura bot.xml.
  Copy-Item $tmp $exe
  Ok "$s.exe"
}

# --- registrar --------------------------------------------------------------

Passo 'Serviços'
foreach ($s in $SERVICOS) {
  $exe = Join-Path $PSScriptRoot "$s.exe"
  $id  = if ($s -eq 'bot') { 'painel-bot' } else { 'painel-web' }

  if (Get-Service -Name $id -ErrorAction SilentlyContinue) {
    & $exe stop | Out-Null
    & $exe uninstall | Out-Null
    Start-Sleep -Seconds 2
  }
  & $exe install | Out-Null
  Ok "$id registrado"
}

# --- permissões -------------------------------------------------------------

Passo 'Permissões'
# As contas virtuais só existem depois do install. Sem escrita em dados\ o
# serviço sobe e morre na primeira gravação do SQLite — e o erro fala de acesso
# negado a um caminho, não de permissão de serviço.
foreach ($id in @('painel-bot', 'painel-web')) {
  & icacls (Join-Path $RAIZ 'dados') /grant "NT SERVICE\${id}:(OI)(CI)M" /T /Q | Out-Null
}
# Leitura no código e no .env. O .env tem credenciais da Meta: leitura só, e só
# para quem precisa.
foreach ($par in @(
  @{ id = 'painel-bot';  alvos = @('dist', 'prisma', 'node_modules', '.env') },
  @{ id = 'painel-web';  alvos = @('activity-dashboard', 'node_modules', '.env', 'servidor-painel.mjs', 'painel-entra.mjs', 'painel-metricas.mjs') }
)) {
  foreach ($a in $par.alvos) {
    $p = Join-Path $RAIZ $a
    if (Test-Path $p) { & icacls $p /grant "NT SERVICE\$($par.id):(OI)(CI)RX" /T /Q | Out-Null }
  }
}
Ok 'escrita em dados\, leitura no código e no .env'

# --- subir ------------------------------------------------------------------

Passo 'Subindo'
Start-Service painel-bot
Start-Sleep -Seconds 3
Start-Service painel-web
Start-Sleep -Seconds 3

Get-Service painel-bot, painel-web | Select-Object Name, Status, StartType | Format-Table -AutoSize

Passo 'Sondas'
foreach ($p in @(@{n='bot'; u='http://127.0.0.1:9511/health'}, @{n='bot ready'; u='http://127.0.0.1:9511/ready'})) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri $p.u -TimeoutSec 5
    Ok "$($p.n): HTTP $($r.StatusCode)"
  } catch {
    Aviso "$($p.n): $($_.Exception.Message) — veja dados\logs\"
  }
}

Write-Host @"

Pronto. Os dois sobem sozinhos no boot.

  Estado:     Get-Service painel-bot, painel-web
  Log:        dados\logs\
  Parar:      Stop-Service painel-web, painel-bot
  Remover:    .\instalar.ps1 -Desinstalar

O run.bat continua servindo para desenvolvimento — só não é mais o caminho de
produção.
"@ -ForegroundColor Cyan
