#!/usr/bin/env pwsh
<#
.SYNOPSIS
Deploy changed files from asc-lite repo to Home Assistant on Raspberry Pi and reload integration.

.EXAMPLE
.\deploy-to-ha.ps1 -HaUrl http://raspberrypi:8123 -HaToken "your-long-lived-token"
#>

param(
    [string]$HaUrl = "http://raspberrypi:8123",
    [string]$HaToken = $env:HA_TOKEN,
    [string]$SshHost = "pi@raspberrypi",
    [string]$RemotePath = "/home/pi/hass/hass-config/custom_components/asc_lite/"
)

# Check prerequisites
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Error "SSH not found. Install OpenSSH or Git Bash."
    exit 1
}

if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Error "SCP not found. Install OpenSSH or Git Bash."
    exit 1
}

# Get changed files in custom_components/asc_lite/
Write-Host "[CHECK] Detecting changed files..." -ForegroundColor Cyan
$changedFiles = & git diff --name-only HEAD | Where-Object { $_ -match "^custom_components/asc_lite/" }

if ($changedFiles.Count -eq 0) {
    Write-Host "[INFO] No changed files in custom_components/asc_lite/" -ForegroundColor Yellow
    exit 0
}

Write-Host "[OK] Found $($changedFiles.Count) changed file(s):" -ForegroundColor Green
$changedFiles | ForEach-Object { Write-Host "     $_" }

# Copy each file via SCP
Write-Host "`n[COPY] Copying to RPi..." -ForegroundColor Cyan
foreach ($file in $changedFiles) {
    $localFile = $file
    $remoteFile = $RemotePath + ($file -replace "^custom_components/asc_lite/", "")
    
    Write-Host "     $localFile -> $remoteFile" -ForegroundColor Gray
    & scp -q "$localFile" "${SshHost}:${remoteFile}"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to copy $file"
        exit 1
    }
}

Write-Host "[OK] Files copied successfully" -ForegroundColor Green

# Reload integration via HA REST API
if (-not $HaToken) {
    Write-Host "`n[INFO] HA_TOKEN not set. Skipping integration reload." -ForegroundColor Yellow
    Write-Host "       To auto-reload, set: `$env:HA_TOKEN = 'your-long-lived-token'" -ForegroundColor Gray
    exit 0
}

Write-Host "`n[RELOAD] Reloading ASC Lite integration in Home Assistant..." -ForegroundColor Cyan

# Try new config_entries endpoint first
$reloadUrl = "$HaUrl/api/config/config_entries/reload"
$headers = @{
    "Authorization" = "Bearer $HaToken"
    "Content-Type"  = "application/json"
}

Write-Host "[DEBUG] Reload URL: $reloadUrl" -ForegroundColor Gray
Write-Host "[DEBUG] Token length: $($HaToken.Length)" -ForegroundColor Gray

try {
    # Use config_entries.reload service
    $serviceUrl = "$HaUrl/api/services/config_entries/reload"
    $body = @{ "entry_id" = "asc_lite" } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri $serviceUrl -Method POST -Headers $headers -Body $body -ErrorAction Stop
    Write-Host "[OK] Integration reloaded successfully" -ForegroundColor Green
} catch {
    # If that fails, try alternate endpoint
    Write-Host "[DEBUG] First attempt failed, trying alternate endpoint..." -ForegroundColor Gray
    try {
        $altUrl = "$HaUrl/api/config/config_entries"
        $response = Invoke-RestMethod -Uri $altUrl -Method GET -Headers $headers -ErrorAction Stop
        Write-Host "[WARN] Could not reload automatically" -ForegroundColor Yellow
    } catch {
        Write-Host "[ERROR] API Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host "`n[INFO] Files copied successfully - manual reload required" -ForegroundColor Yellow
    Write-Host "       Go to: Einstellungen > Geraete und Dienste > ASC Lite > Neu laden" -ForegroundColor Gray
}

Write-Host "`n[DONE] Deploy complete!" -ForegroundColor Green
