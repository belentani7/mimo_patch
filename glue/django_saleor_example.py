# -*- coding: utf-8 -*-
"""
glue/django_saleor_example.py — Ejemplo de "pegamento" Python.

Ilustra cómo Python actúa como "pegamento" para descargar, ejecutar y unificar
piezas preexistentes (Django + Saleor + Stripe + email modules) — la idea
original de Pedro Belentani: "yo pensava que phyton era tipo en lugar del agent
escribir en codigo de una tienda online. el descargaba uno, ejecutava arhivo y
solo lo unficicaba".

Este script:
  1. Descarga (pip install) los módulos necesarios si faltan.
  2. Ejecuta la unificación con el MIMO PATCH como enrutador de System One.
  3. Devuelve la acción elegida y (si el plan es EXECUTE_NOW) ejecuta la skill.

Uso:
    python glue/django_saleor_example.py --state "usuario quiere reembolso"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Asegurar que el directorio raíz del mimo_patch está en sys.path
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def ensure_dependencies():
    """Instala dependencias si faltan (pegamento estilo Pedro)."""
    required = {
        "pydantic": "pydantic>=2.0.0",
        "instructor": "instructor>=1.0.0",
        "openai": "openai>=1.0.0",
    }
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(required[pkg])
    if missing:
        print(f"[glue] Instalando: {missing}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing]
        )


def glue_route(state: str, force_heavy: bool = False) -> dict:
    """
    Ejemplo de "pegamento":
      1. Invoca mimo_route (enrutador System One)
      2. Si plan=EXECUTE_NOW, ejecuta la skill
      3. Devuelve el resultado unificado
    """
    from mimo_patch import mimo_route  # type: ignore
    from skills import get_skill  # type: ignore

    decision = mimo_route(state, force_heavy=force_heavy)
    plan = decision.get("plan", "BLOCKED")
    skill_name = decision.get("chosen_action")

    result = {
        "decision": decision,
        "plan": plan,
        "skill_executed": None,
        "skill_result": None,
    }

    if plan == "EXECUTE_NOW" and skill_name:
        skill = get_skill(skill_name)
        if skill:
            skill_result = skill.safe_run(state, decision)
            result["skill_executed"] = skill_name
            result["skill_result"] = skill_result.model_dump()
        else:
            result["skill_executed"] = None
            result["skill_result"] = {"error": f"skill {skill_name} not found"}

    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="django_saleor_example",
        description="Ejemplo pegamento: Django/Saleor + MIMO PATCH",
    )
    ap.add_argument("--state", required=True,
                    help="Estado del usuario / ticket / log")
    ap.add_argument("--heavy", action="store_true",
                    help="Forzar prompt Fable 5.1")
    ap.add_argument("--install-deps", action="store_true",
                    help="Instalar deps faltantes antes de ejecutar")
    args = ap.parse_args(argv)

    if args.install_deps:
        ensure_dependencies()

    out = glue_route(args.state, force_heavy=args.heavy)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
