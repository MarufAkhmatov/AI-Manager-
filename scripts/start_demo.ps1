# start_demo.ps1 — one-shot Windows launcher for the AI Manager Platform
#
# Boots the backend in DEMO mode (no Postgres / Redis / Ollama / Docker
# required) and the Next.js dev server in parallel. Open the dashboard at
# http://localhost:3000/dashboard — login as admin (any password).
#
# Usage from PowerShell, run from the repo root:
#     .\scripts\start_demo.ps1

$ErrorActionPreference = 'Stop'
$repo = (Get-Item -Path "$PSScriptRoot\..").FullName
Set-Location $repo

# ─────────── Backend ───────────
Write-Host "[AI Manager] starting backend (demo mode)…" -ForegroundColor Green

if (-not (Test-Path .\.venv)) {
    Write-Host "  creating virtualenv at .venv …"
    python -m venv .venv
}

# Activate the venv for this script's scope.
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --quiet
pip install --quiet --upgrade `
    "fastapi>=0.115" "uvicorn[standard]>=0.32" `
    "sqlalchemy[asyncio]>=2.0" "aiosqlite>=0.20" `
    "redis>=5.2" "httpx>=0.27" "tiktoken>=0.8" `
    "pydantic>=2.9" "pydantic-settings>=2.6" `
    "passlib[bcrypt]>=1.7" "pyjwt>=2.10" `
    "watchdog>=5" "apscheduler>=3.10" "pgvector>=0.3.6" `
    "python-multipart>=0.0.12"

# AIM_ROOT just needs to be a writable directory for the audit log.
$env:AIM_ROOT = (Join-Path $repo "aim-demo-root")
$env:AIM_DEMO = "1"
$env:DATABASE_URL = "sqlite+aiosqlite:///./aim-demo.db"
$env:JWT_SECRET = if ($env:JWT_SECRET) { $env:JWT_SECRET } else { "demo-secret-replace-for-prod" }
$env:PYTHONPATH = "$repo\backend"
New-Item -ItemType Directory -Force -Path $env:AIM_ROOT | Out-Null

$backend = Start-Process -PassThru -NoNewWindow -FilePath "python" `
    -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" `
    -WorkingDirectory $repo

Write-Host "  backend pid=$($backend.Id)  →  http://localhost:8000"

# ─────────── Frontend ───────────
Write-Host "[AI Manager] starting frontend …" -ForegroundColor Green

Push-Location (Join-Path $repo "frontend")
if (-not (Test-Path .\node_modules)) {
    Write-Host "  npm install (legacy peer deps) …"
    npm install --legacy-peer-deps --no-audit --no-fund | Out-Null
}

# Override the dev base so the frontend hits the local backend instead of
# the docker hostname baked into .env.example.
$env:NEXT_PUBLIC_API_BASE = "http://localhost:8000"
$env:NEXT_PUBLIC_WS_BASE  = "ws://localhost:8000"

$frontend = Start-Process -PassThru -NoNewWindow -FilePath "npm" `
    -ArgumentList "run","dev" -WorkingDirectory (Get-Location)

Pop-Location

Write-Host ""
Write-Host "──────────────────────────────────────────────────────────────"
Write-Host " AI Manager Platform — demo mode running" -ForegroundColor Cyan
Write-Host "──────────────────────────────────────────────────────────────"
Write-Host " Backend  : http://localhost:8000  (pid $($backend.Id))"
Write-Host " Frontend : http://localhost:3000  (pid $($frontend.Id))"
Write-Host " Dashboard: http://localhost:3000/dashboard"
Write-Host " Login    : username = admin   password = anything"
Write-Host ""
Write-Host " Ctrl+C to stop. Or close the PowerShell window."
Write-Host "──────────────────────────────────────────────────────────────"

# Block until either process exits so Ctrl+C cleanly takes them both down.
try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    Stop-Process -Id $backend.Id  -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue
}
