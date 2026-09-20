# subir.ps1 — Expõe o Financas (Patrimônio) na internet via Cloudflare Quick Tunnel.
#
# Requer cloudflared instalado e no PATH:
#   winget install --id Cloudflare.cloudflared
#   (ou: choco install cloudflared)
#
# Fluxo:
#   1. Mata túnel(is) cloudflared antigo(s) e espera o processo morrer.
#   2. Abre um novo túnel apontando para http://localhost:8080.
#   3. Espera a URL pública (https://algo.trycloudflare.com) aparecer no log.
#   4. Grava essa URL em .env como CSRF_TRUSTED_ORIGINS — sem isso o Django
#      rejeita os formulários (login, transações, etc.) vindos do domínio
#      público do túnel com erro 403 CSRF.
#   5. Reinicia o servidor local (run.bat) para ele ler o .env atualizado.
#   6. Espera o servidor responder e imprime o link público.
#
# Mantenha esta janela aberta — fechá-la encerra o túnel (mas não o servidor;
# feche a janela "Financas" separadamente se quiser parar tudo).

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "============================================"
Write-Host "  Financas - Expondo via Cloudflare Tunnel"
Write-Host "============================================"
Write-Host ""

# --- 1. Confirma que o cloudflared está instalado ---------------------------
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared nao encontrado no PATH. Instale com: winget install --id Cloudflare.cloudflared"
}

# --- 2. Mata túnel(is) antigo(s) ---------------------------------------------
$oldTunnels = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($oldTunnels) {
    Write-Host "[INFO] Encerrando tunel(is) antigo(s)..."
    $oldTunnels | Stop-Process -Force
    $oldTunnels | Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
}

$logPath = Join-Path $PSScriptRoot "tunel-financas.log"
if (Test-Path $logPath) {
    $removed = $false
    for ($i = 0; $i -lt 20; $i++) {
        try { Remove-Item $logPath -Force -ErrorAction Stop; $removed = $true; break }
        catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $removed) {
        $logPath = Join-Path $PSScriptRoot "tunel-financas-$(Get-Date -Format 'yyyyMMddHHmmss').log"
    }
}

# --- 3. Abre o túnel ----------------------------------------------------------
Write-Host "[INFO] Abrindo tunel para http://localhost:8080 ..."
$tunnelProcess = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://localhost:8080" `
    -RedirectStandardError $logPath -PassThru -WindowStyle Hidden

$publicUrl = $null
$deadline = (Get-Date).AddSeconds(60)
while ((Get-Date) -lt $deadline) {
    if (Test-Path $logPath) {
        $content = Get-Content $logPath -Raw -ErrorAction SilentlyContinue
        if ($content -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
            $publicUrl = $matches[0]
            break
        }
    }
    Start-Sleep -Milliseconds 500
}

if (-not $publicUrl) {
    Stop-Process -Id $tunnelProcess.Id -Force -ErrorAction SilentlyContinue
    throw "Nao consegui obter a URL publica do tunel em 60s. Veja $logPath para detalhes."
}

Write-Host "[OK] Tunel aberto: $publicUrl"

# --- 4. Grava a URL em .env (CSRF_TRUSTED_ORIGINS) ---------------------------
$envPath = Join-Path $PSScriptRoot ".env"
$lines = @()
if (Test-Path $envPath) {
    Copy-Item $envPath "$envPath.backup" -Force
    $lines = [System.IO.File]::ReadAllLines($envPath) | Where-Object { $_ -notmatch '^CSRF_TRUSTED_ORIGINS=' }
}
$lines += "CSRF_TRUSTED_ORIGINS=$publicUrl"
[System.IO.File]::WriteAllLines($envPath, $lines, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "[OK] .env atualizado (CSRF_TRUSTED_ORIGINS=$publicUrl)"

# --- 5. Reinicia o servidor local, para ele ler o .env novo ------------------
$portInUse = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[INFO] Encerrando instancia anterior do servidor (porta 8080 em uso)..."
    $portInUse | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

Write-Host "[INFO] Iniciando o servidor (run.bat)..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "run.bat" -WorkingDirectory $PSScriptRoot -WindowStyle Normal

# --- 6. Espera o servidor local responder ------------------------------------
$serverReady = $false
$deadline = (Get-Date).AddSeconds(60)
while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8080/login/" -UseBasicParsing -TimeoutSec 3
        if ($resp.StatusCode -eq 200) { $serverReady = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}

Write-Host ""
Write-Host "============================================"
if ($serverReady) {
    Write-Host "  Financas disponivel publicamente em:"
    Write-Host "  $publicUrl"
} else {
    Write-Host "  Tunel aberto, mas o servidor local ainda nao respondeu."
    Write-Host "  URL publica: $publicUrl"
    Write-Host "  Verifique a janela do servidor (run.bat)."
}
Write-Host "============================================"
Write-Host ""
Write-Host "Mantenha esta janela aberta -- fecha-la encerra o tunel."
Write-Host "Pressione Ctrl+C para encerrar."
Write-Host ""

# Mantém o script (e o túnel) vivo até a janela ser fechada.
Wait-Process -Id $tunnelProcess.Id
