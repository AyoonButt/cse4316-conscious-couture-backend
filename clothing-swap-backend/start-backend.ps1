param(
    [switch]$InstallDeps,
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host 'Creating virtual environment (.venv)...'
    py -3.12 -m venv .venv
}

if (-not (Test-Path $venvPython)) {
    Write-Error 'Virtual environment python was not found at .venv\Scripts\python.exe'
}

function Install-BackendDependencies {
    Write-Host 'Installing dependencies from requirements.txt...'
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Warning 'requirements.txt has a known resolver conflict. Installing compatible core dependencies plus shipengine fallback...'
    & $venvPython -m pip install fastapi==0.109.0 "uvicorn[standard]==0.27.0" python-multipart==0.0.6 sqlalchemy==2.0.25 alembic==1.13.1 pydantic==2.5.3 pydantic-settings==2.1.0 email-validator==2.1.0 "python-jose[cryptography]==3.3.0" "passlib[bcrypt]==1.7.4" httpx==0.26.0 aiohttp==3.9.1 python-dotenv==1.0.1 pytz==2023.3 stripe==14.3.0 shipstation==0.1.3 google-auth
    if ($LASTEXITCODE -ne 0) {
        Write-Error 'Failed to install fallback dependency set. Resolve pip errors and retry.'
    }

    & $venvPython -m pip install shipengine==2.0.5 --no-deps
    if ($LASTEXITCODE -ne 0) {
        Write-Error 'Failed to install shipengine fallback dependency. Resolve pip errors and retry.'
    }
}

$needsDeps = $InstallDeps
if (-not $needsDeps) {
    try {
        & $venvPython -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('fastapi') and importlib.util.find_spec('uvicorn') else 1)" | Out-Null
    }
    catch {
        $needsDeps = $true
    }

    if ($LASTEXITCODE -ne 0) {
        $needsDeps = $true
        Write-Host 'FastAPI/Uvicorn not found in .venv. Installing dependencies once before startup...'
    }
}

if ($needsDeps) {
    Install-BackendDependencies
}

$envPath = Join-Path $projectRoot '.env'
if (-not (Test-Path $envPath)) {
    Write-Error '.env file not found. Create clothing-swap-backend/.env before starting the backend.'
}

$requiredEnvKeys = @(
    'STRIPE_SECRET_KEY',
    'STRIPE_PUBLISHABLE_KEY',
    'STRIPE_WEBHOOK_SECRET',
    'SHIPSTATION_API_KEY',
    'SHIPSTATION_API_SECRET',
    'SHIPENGINE_API_KEY',
    'vite_supabase_url',
    'vite_supabase_anon_key'
)

$envFromFile = @{}
Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq '' -or $line.StartsWith('#') -or -not $line.Contains('=')) {
        return
    }

    $parts = $line -split '=', 2
    $key = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    if ($key -ne '') {
        $envFromFile[$key] = $value
    }
}

$missingKeys = @()
foreach ($key in $requiredEnvKeys) {
    $inProcessEnv = [string]::IsNullOrWhiteSpace((Get-Item -Path "Env:$key" -ErrorAction SilentlyContinue).Value) -eq $false
    $inDotEnv = $envFromFile.ContainsKey($key) -and -not [string]::IsNullOrWhiteSpace($envFromFile[$key])
    if (-not $inProcessEnv -and -not $inDotEnv) {
        $missingKeys += $key
    }
}

if ($missingKeys.Count -gt 0) {
    Write-Error ("Missing required keys in .env or process environment: " + ($missingKeys -join ', '))
}

if (-not (Get-Item -Path 'Env:DATABASE_URL' -ErrorAction SilentlyContinue) -and -not $envFromFile.ContainsKey('DATABASE_URL')) {
    $defaultDatabasePath = (Join-Path $projectRoot 'clothing_swap.db') -replace '\\', '/'
    $env:DATABASE_URL = "sqlite:///$defaultDatabasePath"
    Write-Host "DATABASE_URL not set. Using default: $($env:DATABASE_URL)"
}

function Ensure-DevSampleUsers {
    $seedCheckScript = @'
from app.database import init_db, get_database_session
from app.models.user import User

init_db()
session = get_database_session()
try:
    print(session.query(User).count())
finally:
    session.close()
'@

    $existingUserCount = & $venvPython -c $seedCheckScript
    if ($LASTEXITCODE -ne 0) {
        Write-Error 'Failed to inspect the users table before backend startup.'
    }

    $userCount = 0
    if (-not [int]::TryParse(($existingUserCount | Select-Object -Last 1), [ref]$userCount)) {
        Write-Error 'Could not parse the current users count before backend startup.'
    }

    if ($userCount -gt 0) {
        return
    }

    Write-Host 'No local users found. Seeding sample users for dev sign-in...'
    & $venvPython scripts\create_sample_users.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error 'Failed to seed sample users. Resolve the seed script errors and retry.'
    }
}

Ensure-DevSampleUsers

Write-Host "Starting backend on port $Port..."
& $venvPython -m uvicorn app.main:app --app-dir $projectRoot --reload --host 0.0.0.0 --port $Port
