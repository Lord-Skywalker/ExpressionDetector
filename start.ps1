# start.ps1 — ExpressionDetector Project Launcher
# Run this from the project root: .\start.ps1

$root = $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ExpressionDetector — Starting Services   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── Step 1: Ensure broker/out directory exists ───────────────────────────────
$brokerPath = Join-Path $root "broker\out"
if (-not (Test-Path $brokerPath)) {
    New-Item -ItemType Directory -Path $brokerPath -Force | Out-Null
    Write-Host "[+] Created broker/out directory" -ForegroundColor Green
} else {
    Write-Host "[✓] broker/out exists" -ForegroundColor Green
}

# ── Step 2: Run database migrations ─────────────────────────────────────────
Write-Host "[~] Running database migrations..." -ForegroundColor Yellow
& "$root\venv\Scripts\python.exe" "$root\manage.py" migrate
Write-Host "[✓] Migrations done" -ForegroundColor Green

# ── Step 3: Start Django API server (new window) ─────────────────────────────
Write-Host "[~] Starting Django API server on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'Django API Server' -ForegroundColor Cyan; cd '$root'; .\venv\Scripts\python.exe manage.py runserver"

# ── Step 4: Start Celery worker (new window) ─────────────────────────────────
Write-Host "[~] Starting Celery worker..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'Celery Worker' -ForegroundColor Magenta; cd '$root'; .\venv\Scripts\celery.exe -A core worker --loglevel=info --pool=solo"

# ── Step 5: Start React/Vite frontend (new window) ───────────────────────────
Write-Host "[~] Starting React frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'React Frontend' -ForegroundColor Green; cd '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All services launching in new windows!   " -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend : http://localhost:5173          " -ForegroundColor White
Write-Host "  API      : http://localhost:8000/api/     " -ForegroundColor White
Write-Host "  Admin    : http://localhost:8000/admin/   " -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
