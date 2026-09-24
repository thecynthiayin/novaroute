param([string]$Python = 'python', [switch]$SkipServices, [switch]$Demo)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (!(Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
if (!$SkipServices) {
    docker compose up -d --wait
    if ($LASTEXITCODE -ne 0) { throw 'Docker services did not start. Check Docker or use -SkipServices with native MySQL/Mailpit.' }
}
& $Python -c "import sys; assert sys.version_info[:2] == (3,12), 'Use Python 3.12 for the pinned stack'"
if ($LASTEXITCODE -ne 0) { throw 'Pass -Python with the path to a Python 3.12 executable.' }
if (!(Test-Path -LiteralPath 'backend/.venv')) { & $Python -m venv backend/.venv }
$projectPython = Join-Path $projectRoot 'backend/.venv/Scripts/python.exe'
& $projectPython -m pip install -r backend/requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Push-Location backend
& $projectPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed. Verify DATABASE_URL and MySQL availability.' }
Pop-Location
if ($Demo) { & $projectPython database/seed.py --demo --limit 25 --seed 42 }
Push-Location frontend
if (!(Test-Path -LiteralPath '.env.local')) { Copy-Item -LiteralPath '.env.example' -Destination '.env.local' }
npm ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
Pop-Location
Write-Host 'Setup complete. See README for the two native start commands and optional model warmup.'
