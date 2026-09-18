<#
    ATENÇÃO AO SALVAR ESTE ARQUIVO: ele precisa de BOM.

    O PowerShell 5.1 lê `.ps1` como ANSI quando não há BOM. Sem ele, todo
    acento e travessão deste arquivo chega ao parser como lixo e o script
    morre com "Missing closing '}'" — um erro que não tem nada a ver com
    chaves. É o inverso do `.env`, que quebra COM BOM.
#>

<#
.SYNOPSIS
    Sobe o sistema e o publica na internet, em um comando.

.DESCRIPTION
    Toda vez que a máquina reinicia, publicar o painel exigia cinco passos:
    subir os containers, abrir dois túneis, copiar as duas URLs que mudam a
    cada vez, editar o .env e recriar dois containers. Cinco passos com uma
    ordem que não é óbvia — trocar as URLs de lugar faz o painel abrir em
    branco, e o sintoma não diz o motivo.

    São dois túneis e não um porque o painel roda no navegador de quem
    acessa: o `localhost:8000` que ele chamaria seria o celular de quem
    abriu, não este PC.

.NOTES
    O .env é gravado em UTF-8 sem BOM. O jeito padrão do PowerShell 5.1
    (`Set-Content`) grava com BOM, e um BOM no começo do .env quebra a
    primeira variável do arquivo — em silêncio.

.EXAMPLE
    .\subir.ps1
    .\subir.ps1 -SoLocal      # sobe sem publicar na internet
#>

[CmdletBinding()]
param(
    [switch]$SoLocal
)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$ArquivoEnv = Join-Path $PSScriptRoot '.env'
$Cloudflared = Join-Path $PSScriptRoot 'cloudflared.exe'

function Escrever($texto, $cor = 'Gray') { Write-Host $texto -ForegroundColor $cor }

function Ajustar-Env {
    <#
        Troca as três variáveis de endereço, preservando o resto do arquivo.

        Lê e grava explicitamente em UTF-8 sem BOM: o .env tem comentários
        acentuados, e reescrevê-lo com a codificação padrão do PowerShell os
        corromperia.
    #>
    param([string]$Api, [string]$Painel)

    Copy-Item $ArquivoEnv "$ArquivoEnv.backup" -Force

    $linhas = [System.IO.File]::ReadAllLines($ArquivoEnv, [System.Text.Encoding]::UTF8)
    $novas = $linhas | ForEach-Object {
        if ($_ -like 'NEXT_PUBLIC_API_URL=*') { "NEXT_PUBLIC_API_URL=$Api" }
        elseif ($_ -like 'FRONTEND_URL=*') { "FRONTEND_URL=$Painel" }
        elseif ($_ -like 'ALLOWED_ORIGINS=*') {
            "ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,$Painel"
        }
        else { $_ }
    }
    [System.IO.File]::WriteAllLines(
        $ArquivoEnv, $novas, (New-Object System.Text.UTF8Encoding $false)
    )
}

function Abrir-Tunel {
    <#
        Sobe um túnel e devolve a URL que ele imprimiu.

        A URL só aparece na saída do processo, e o cloudflared escreve em
        stderr. Daí o redirecionamento para arquivo e a espera lendo-o: não
        há como perguntar a URL depois, e ela muda a cada execução.
    #>
    param([int]$Porta, [string]$Rotulo)

    # O log do túnel anterior pode continuar aberto por alguns instantes: o
    # `Stop-Process` sinaliza e segue, sem esperar o Windows soltar o handle.
    # Apagar na primeira tentativa falhava com "being used by another
    # process" e derrubava o script inteiro.
    $log = Join-Path $PSScriptRoot "tunel-$Rotulo.log"
    for ($i = 0; $i -lt 20 -and (Test-Path $log); $i++) {
        try { Remove-Item $log -Force -ErrorAction Stop }
        catch { Start-Sleep -Milliseconds 250 }
    }
    if (Test-Path $log) {
        # Ainda preso depois de 5s: usa outro nome em vez de desistir. Um log
        # a mais na pasta é melhor que não subir.
        $log = Join-Path $PSScriptRoot "tunel-$Rotulo-$(Get-Date -Format 'HHmmss').log"
    }

    $processo = Start-Process -FilePath $Cloudflared `
        -ArgumentList 'tunnel', '--url', "http://localhost:$Porta" `
        -RedirectStandardError $log -PassThru -WindowStyle Hidden

    $limite = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $limite) {
        Start-Sleep -Milliseconds 500
        if (-not (Test-Path $log)) { continue }
        $texto = Get-Content $log -Raw -ErrorAction SilentlyContinue
        if ($texto -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
            return [pscustomobject]@{ Url = $Matches[0]; Processo = $processo }
        }
    }

    $processo | Stop-Process -Force -ErrorAction SilentlyContinue
    throw "O túnel de $Rotulo não devolveu URL em 60s. Veja $log."
}

# ---------------------------------------------------------------- containers

# O daemon, nao o binario.
#
# `where docker` passa com o Docker Desktop fechado, e o compose so falha
# depois, com "failed to connect to the docker API at npipe://..." — uma
# mensagem que nao diz o que fazer. `docker info` pergunta ao servidor, que
# e a coisa que precisa estar de pe.
docker info --format '{{.ServerVersion}}' 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw ("O Docker Desktop nao esta rodando. Abra-o, espere a baleia na " +
           "bandeja parar de animar, e rode este script de novo.")
}

Escrever "Subindo os containers..." 'Cyan'
docker compose --profile whatsapp up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose falhou." }

if ($SoLocal) {
    Escrever "`nPronto. Painel em http://localhost:3000" 'Green'
    Escrever "(sem publicar na internet — rode sem -SoLocal para isso)"
    return
}

# -------------------------------------------------------------------- túneis

if (-not (Test-Path $Cloudflared)) {
    throw "cloudflared.exe não está em $PSScriptRoot. Baixe-o antes de publicar."
}

# Túneis antigos morrem primeiro: dois cloudflared apontando para a mesma
# porta funcionam, e aí sobram URLs válidas que ninguém sabe quais são.
#
# O `Wait-Process` não é zelo: sem ele o script seguia enquanto o Windows
# ainda segurava o log do túnel anterior, e a próxima linha morria tentando
# apagá-lo.
$antigos = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($antigos) {
    $antigos | Stop-Process -Force
    $antigos | Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
}

Escrever "Abrindo o túnel do backend..." 'Cyan'
$backend = Abrir-Tunel -Porta 8000 -Rotulo 'backend'
Escrever "  $($backend.Url)"

Escrever "Abrindo o túnel do painel..." 'Cyan'
$painel = Abrir-Tunel -Porta 3000 -Rotulo 'painel'
Escrever "  $($painel.Url)"

# ----------------------------------------------------------------------- env

Escrever "`nAjustando o .env..." 'Cyan'
Ajustar-Env -Api $backend.Url -Painel $painel.Url

# A `NEXT_PUBLIC_API_URL` é lida na build do Next, e o CORS no arranque do
# backend: sem recriar os dois, o .env novo não vale para nenhum deles.
Escrever "Recriando backend e frontend com os endereços novos..." 'Cyan'
docker compose up -d --force-recreate backend frontend
if ($LASTEXITCODE -ne 0) { throw "Falha ao recriar os containers." }

Escrever "`nAguardando o painel compilar..." 'Cyan'
$limite = (Get-Date).AddSeconds(90)
$pronto = $false
while ((Get-Date) -lt $limite) {
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest 'http://localhost:3000' -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { $pronto = $true; break }
    } catch { }
}

Escrever ""
if ($pronto) {
    Escrever "======================================================" 'Green'
    Escrever "  Painel:  $($painel.Url)" 'Green'
    Escrever "======================================================" 'Green'
    Escrever ""
    Escrever "Deixe esta janela aberta: fechá-la derruba os túneis."
    Escrever "Os endereços mudam a cada execução — é assim que o túnel"
    Escrever "gratuito funciona."
} else {
    Escrever "O painel não respondeu em 90s. Veja: docker compose logs frontend" 'Yellow'
}
