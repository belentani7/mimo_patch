.PHONY: install test self-test serve-mcp classify stats dry-run clean

install:
	@echo "▶ Instalando MIMO PATCH..."
	pip install -r requirements.txt
	@mkdir -p logs
	@cp -n .env.example .env 2>/dev/null || true
	@echo "✓ Instalado. Edita .env con tus API keys."

install-termux:
	@bash install/install_termux.sh

install-windows:
	@powershell -ExecutionPolicy Bypass -File install/install.ps1

test:
	@pytest -q tests/

self-test:
	@python mimo_patch.py self-test

serve-mcp:
	@python mimo_patch.py serve-mcp

classify:
	@python mimo_patch.py classify --state "$(STATE)"

dry-run:
	@python mimo_patch.py dry-run --state "$(STATE)"

stats:
	@python mimo_patch.py stats

compile-check:
	@python -m compileall -q . && echo "✅ compile OK"

clean:
	@rm -rf __pycache__ */__pycache__ */*/__pycache__ logs/*.jsonl
	@echo "✓ Limpio"
