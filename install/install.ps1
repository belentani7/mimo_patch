# MIMO PATCH — Windows installer. Preview by default; no admin required.
param(
    [switch]$Execute,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'

if ($Execute -and $DryRun) {
    throw 'Usa -Execute o -DryRun, no ambos.'
}
$ProjectDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir 'mimo_patch.py') -PathType Leaf)) {
    throw 'No se encontró mimo_patch.py junto al instalador.'
}
if (-not $Execute) {
    Write-Host 'MIMO PATCH - vista previa (sin cambios).'
    Write-Host "Directorio del proyecto: $ProjectDir"
    Write-Host 'Con -Execute: crear .venv, instalar dependencias Python y crear logs.'
    Write-Host 'No se ejecutarán servicios, modelos remotos ni skills sensibles.'
    return
}

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw 'Python no encontrado en PATH. No se ha instalado nada.'
}

Push-Location -LiteralPath $ProjectDir
try {
    if (-not (Test-Path -LiteralPath '.venv' -PathType Container)) {
        & $PythonCommand.Source -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear .venv.' }
    }
    $VenvPython = Join-Path $ProjectDir '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        throw 'El entorno virtual no contiene python.exe.'
    }
    # Usar siempre Python del entorno virtual, sin cambiar ExecutionPolicy ni PATH.
    & $VenvPython -m pip install pydantic instructor openai pyyaml python-dotenv rich
    if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de dependencias mínimas.' }

    $OptionalPackages = @(
        'mcp>=0.9.0',
        'fastapi>=0.111.0',
        'uvicorn[standard]>=0.30.0',
        'pytest>=8.2.0',
        'redis>=5.0.0'
    )
    foreach ($Package in $OptionalPackages) {
        & $VenvPython -m pip install $Package
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Dependencia opcional no disponible: $Package"
        }
    }
    New-Item -ItemType Directory -Force -Path 'logs' | Out-Null
    Write-Host "Instalación terminada. Python local: $VenvPython"
    Write-Host 'Configura variables de API solo si autorizas llamadas externas.'
    Write-Host ('Prueba local: "' + $VenvPython + '" mimo_patch.py self-test')
}
finally {
    Pop-Location
}
