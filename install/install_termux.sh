#!/usr/bin/env bash
# install/install_termux.sh — Termux (Android/Huawei)
# Instala el MIMO PATCH en Termux sin requerir root.
set -euo pipefail

echo "▶ System One Gate v3 (MIMO PATCH) — Termux install"

# Update packages
pkg update -y
pkg install -y python git rust binutils libffi openssl

# Create venv (opcional pero recomendado)
if [ ! -d .venv ]; then
    python -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip wheel

# Dependencias mínimas (siempre)
pip install pydantic instructor openai pyyaml python-dotenv rich

# MCP opcional (modo stub si falla)
pip install "mcp>=0.9.0" 2>/dev/null || \
    echo "⚠️ mcp no instalable — modo stub activado (mcp_stub.py)"

# Opcionales (no fallan si no se pueden instalar)
pip install "fastapi>=0.111.0" "uvicorn[standard]>=0.30.0" 2>/dev/null || \
    echo "⚠️ fastapi no instalable — sin servidor HTTP (uso CLI normal)"
pip install "pytest>=8.2.0" 2>/dev/null || \
    echo "⚠️ pytest no instalable — sin tests"
pip install "redis>=5.0.0" 2>/dev/null || \
    echo "⚠️ redis no instalable — memoria en JSONL"
pip install "psycopg[binary]>=3.1.0" 2>/dev/null || \
    echo "⚠️ psycopg no instalable — memoria en JSONL"

# Crear estructura de logs
mkdir -p logs skills prompts

# Copiar .env si no existe
cp -n .env.example .env 2>/dev/null || true

echo ""
echo "✓ Instalado."
echo "  Activa el venv:  source .venv/bin/activate"
echo "  Configura:       nano .env  (rellena API keys si tienes)"
echo "  Prueba:          python mimo_patch.py self-test"
echo "  Classify:        python mimo_patch.py classify --state 'usuario chargeback 502'"
echo "  MCP server:      python mimo_patch.py serve-mcp"
