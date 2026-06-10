# prod_up.ps1 - bring up the full AI Manager production stack on Windows.
#
# One command: builds images, pulls Ollama models, runs migrations, seeds
# the admin, and starts every service. Run from the repo root:
#     .\scripts\prod_up.ps1

$ErrorActionPreference = 'Stop'
$repo = (Get-Item -Path "$PSScriptRoot\..").FullName
Set-Location $repo

# 1. .env
if (-not (Test-Path .\.env)) {
    Write-Host "[prod] .env not found - copying from .env.example" -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "  >>> Edit .env: set POSTGRES_PASSWORD, JWT_SECRET, ADMIN_PASSWORD," -ForegroundColor Yellow
    Write-Host "      AIM_ROOT, and (optional) ANTHROPIC_API_KEY, then re-run." -ForegroundColor Yellow
    exit 1
}

# 2. Ensure AIM_ROOT exists and the KB tree is bootstrapped.
$aimRoot = (Select-String -Path .\.env -Pattern '^\s*AIM_ROOT=(.+)$').Matches.Groups[1].Value.Trim()
if ($aimRoot -and -not (Test-Path $aimRoot)) {
    Write-Host "[prod] AIM_ROOT '$aimRoot' missing - bootstrapping KB tree..." -ForegroundColor Green
    powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_root.ps1
}

# 3. Build + up. --env-file makes ${AIM_ROOT} etc. available for compose
#    interpolation (env_file: only injects into containers).
Write-Host "[prod] building images..." -ForegroundColor Green
docker compose --env-file .env -f infra\docker-compose.yml build

Write-Host "[prod] starting stack (first run pulls ~10GB of Ollama models - be patient)..." -ForegroundColor Green
docker compose --env-file .env -f infra\docker-compose.yml up -d

Write-Host ""
Write-Host "--------------------------------------------------------------"
Write-Host " AI Manager Platform - production stack starting" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------"
Write-Host " Web : http://localhost:3000/dashboard"
Write-Host " API : http://localhost:8000/docs"
Write-Host " Login: the ADMIN_USERNAME / ADMIN_PASSWORD from your .env"
Write-Host ""
Write-Host " Follow startup:  docker compose --env-file .env -f infra\docker-compose.yml logs -f"
Write-Host " ollama-init pulls models on first run; api waits for it, then"
Write-Host " migrates + seeds the admin automatically."
Write-Host "--------------------------------------------------------------"
