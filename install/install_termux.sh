#!/usr/bin/env bash
# MIMO PATCH — Termux installer. Preview by default; no root required.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ ! -f "$PROJECT_DIR/mimo_patch.py" ]]; then
    printf 'Error: no se encontró mimo_patch.py junto al instalador.\n' >&2
    exit 2
fi

if [[ $# -gt 1 ]]; then
    printf 'Uso: bash install/install_termux.sh [--dry-run|--execute]\n' >&2
    exit 2
fi
case "${1:---dry-run}" in
    --dry-run)
        printf 'MIMO PATCH — vista previa (sin cambios).\n'
        printf 'Directorio del proyecto: %s\n' "$PROJECT_DIR"
        printf 'Con --execute: pkg update/install, crear .venv, instalar dependencias y crear logs.\n'
        printf 'No se ejecutarán servicios, modelos remotos ni skills sensibles.\n'
        exit 0
        ;;
    --execute) ;;
    *)
        printf 'Uso: bash install/install_termux.sh [--dry-run|--execute]\n' >&2
        exit 2
        ;;
esac

if ! command -v pkg >/dev/null 2>&1; then
    printf 'Error: --execute requiere Termux y su comando pkg; no se ha instalado nada.\n' >&2
    exit 2
fi
cd -- "$PROJECT_DIR"
printf 'MIMO PATCH — instalación explícita en %s\n' "$PROJECT_DIR"
pkg update -y
pkg install -y python git rust binutils libffi openssl

if [[ ! -d .venv ]]; then
    python -m venv .venv
fi
VENV_PY="$PROJECT_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    printf 'Error: el entorno virtual no contiene un Python ejecutable.\n' >&2
    exit 1
fi

# Instalar siempre dentro del venv; nunca usar el pip global ni actualizarlo.
"$VENV_PY" -m pip install pydantic instructor openai pyyaml python-dotenv rich
"$VENV_PY" -m pip install 'mcp>=0.9.0' || printf 'Aviso: MCP no disponible; modo stub.\n' >&2
"$VENV_PY" -m pip install 'fastapi>=0.111.0' 'uvicorn[standard]>=0.30.0' || printf 'Aviso: servidor HTTP opcional no disponible.\n' >&2
"$VENV_PY" -m pip install 'pytest>=8.2.0' || printf 'Aviso: pytest opcional no disponible.\n' >&2
"$VENV_PY" -m pip install 'redis>=5.0.0' || printf 'Aviso: Redis opcional no disponible.\n' >&2
"$VENV_PY" -m pip install 'psycopg[binary]>=3.1.0' || printf 'Aviso: PostgreSQL opcional no disponible.\n' >&2
mkdir -p -- logs
printf 'Instalación terminada. Activa: source "%s/.venv/bin/activate"\n' "$PROJECT_DIR"
printf 'Variables de API: configúralas en el entorno solo si autorizas llamadas externas.\n'
printf 'Prueba local: "%s" mimo_patch.py self-test\n' "$VENV_PY"
