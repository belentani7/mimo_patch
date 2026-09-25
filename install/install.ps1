# install/install.ps1 — Windows 11 (PowerShell)
# Instala el MIMO PATCH en Windows sin requerir admin.
$ErrorActionPreference = "Stop"

Write-Host "▶ System One Gate v3 (MIMO PATCH) — Windows 11 install" -ForegroundColor Cyan

# Verificar Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "❌ Python no encontrado. Instálalo desde https://python.org" -ForegroundColor Red
    exit 1
}

# Crear venv si no existe
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip wheel

# Dependencias mínimas
pip install pydantic instructor openai pyyaml python-dotenv rich

# MCP opcional
try {
    pip install "mcp>=0.9.0" 2>$null
    Write-Host "✓ MCP instalado (FastMCP real)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ mcp no instalable — modo stub activado (mcp_stub.py)" -ForegroundColor Yellow
}

# Opcionales
$optionals = @("fastapi>=0.111.0", "uvicorn[standard]>=0.30.0", "pytest>=8.2.0", "redis>=5.0.0")
foreach ($pkg in $optionals) {
    try {
        pip install $pkg 2>$null | Out-Null
    } catch {
        Write-Host "⚠️ $pkg no instalable — skip" -ForegroundColor Yellow
    }
}

# Crear estructura
New-Item -ItemType Directory -Force -Path logs, skills, prompts | Out-Null

# Copiar .env si no existe
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "✓ Creado .env (rellénalo con tus API keys)" -ForegroundColor Green
}

Write-Host ""
Write-Host "✓ Instalado." -ForegroundColor Green
Write-Host "  Activa el venv:  .\.venv\Scripts\Activate.ps1"
Write-Host "  Configura:       notepad .env"
Write-Host "  Prueba:          python mimo_patch.py self-test"
Write-Host "  Classify:        python mimo_patch.py classify --state 'usuario chargeback 502'"
Write-Host "  MCP server:      python mimo_patch.py serve-mcp"
