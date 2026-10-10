#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mimo_patch.py — Parche Unificado (Mimo Code) v3 final.

Entrypoint único que integra:
  - Fable 5.1 (XML structured prompt + Mental Reframing)
  - Pydantic strict typing
  - Jev AI / System One routing (con multi-provider fallback)
  - OpenCode MCP server (mimo_route + mimo_cache_stats)
  - Hard guardrail local NUNCA bypassable
  - Degraded mode + NOTIFY_HUMAN urgency=1.0

Subcomandos CLI:
  serve-mcp       Arranca servidor MCP stdio para OpenCode
  classify        Clasifica un estado (CLI equivalente a gate + route)
  stats           Muestra stats del cache
  self-test       Ejecuta la matriz extendida de pruebas
  dry-run         Simula routing sin llamar a ningún provider

Uso:
  python mimo_patch.py classify --state "usuario chargeback 502"
  python mimo_patch.py serve-mcp
  python mimo_patch.py self-test
  python mimo_patch.py stats

Env vars (todas opcionales, con defaults):
  MIMO_CONFIDENCE_THRESHOLD=0.85   Umbral de confianza para ejecutar
  MIMO_LOG_LEVEL=WARNING           DEBUG|INFO|WARNING|ERROR
  MIMO_CACHE_FILE=./logs/cache.jsonl
  MIMO_NOTIFY_FILE=./logs/notify.jsonl
  TYPESAFE_API_KEY=                 Si vacío → modo degradado (solo heurística)
  OPENROUTER_API_KEY=
  OPENAI_API_KEY=
  S1G_LOCAL_FIRST=0                1 = usar Ollama local antes que remoto
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

# Resolve sibling imports when se ejecuta como script
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from mcp_stub import get_mcp  # type: ignore

# ═════════════════════════════════════════════════════════════
# Umbrales EXACTOS del system-one-router.json
# ═════════════════════════════════════════════════════════════
CONFIDENCE_THRESHOLD = float(os.getenv("MIMO_CONFIDENCE_THRESHOLD", "0.85"))
URGENCY_AUTORUN_THRESHOLD = 0.70
LOG_LEVEL = os.getenv("MIMO_LOG_LEVEL", "WARNING").upper()


def _log(msg: str, level: str = "INFO") -> None:
    if {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}.get(level, 1) >= {
        "DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3
    }.get(LOG_LEVEL, 1):
        sys.stderr.write(f"[mimo:{level}] {msg}\n")
        sys.stderr.flush()


# ═════════════════════════════════════════════════════════════
# Plan de acción — reglas exactas del JSON de OpenCode
# ═════════════════════════════════════════════════════════════
def decide_action_plan(
    is_safe: bool,
    confidence: float,
    urgency: float,
) -> str:
    """
    Traduce la decisión a un plan según las 4 reglas del system-one-router.json:
      1. is_safe=False → BLOCKED
      2. confidence < 0.85 → ASK_CLARIFICATION
      3. is_safe=True AND confidence≥0.85 AND urgency≥0.7 → EXECUTE_NOW
      4. is_safe=True AND confidence≥0.85 AND urgency<0.7 → PROPOSE_AND_WAIT
    """
    if not is_safe:
        return "BLOCKED"
    if confidence < CONFIDENCE_THRESHOLD:
        return "ASK_CLARIFICATION"
    if urgency >= URGENCY_AUTORUN_THRESHOLD:
        return "EXECUTE_NOW"
    return "PROPOSE_AND_WAIT"


# ═════════════════════════════════════════════════════════════
# mimo_route — la herramienta principal expuesta a OpenCode
# ═════════════════════════════════════════════════════════════
def mimo_route(state: str, force_heavy: bool = False) -> dict[str, Any]:
    """
    Enruta un estado System One. Pipeline:
      1. cache.get(state) ← cache.py (LRU 512)
      2. gate_check(state) ← heurística pura, 0 tokens
      3. load_prompt(heavy) ← lazy: solo si el gate lo pide
      4. router.route() ← SystemOneRouter (Jev + fallback a OpenRouter/OpenAI/Ollama)
      5. decide_action_plan() ← reglas del JSON OpenCode
      6. cache.put(state, result)
      7. Si excepción → notification.notify_human(urgency=1.0) → degraded
    """
    # Imports perezosos para evitar dependencias circulares
    from gate import gate_check, execute, CONFIG
    from cache import get_cache
    from notification import notify_human

    if not state or not state.strip():
        return {
            "degraded": True,
            "error": "empty_state",
            "plan": "BLOCKED",
            "urgency_score": 0.0,
            "confidence": 0.0,
            "is_safe_to_execute": False,
        }

    cache = get_cache()

    # 1. Cache hit
    cached = cache.get(state)
    if cached and not force_heavy:
        cached["cache"] = "hit"
        _log(f"cache HIT para state len={len(state)}")
        return cached

    # 2. Gate heurístico (0 tokens)
    try:
        g = gate_check(state, force_heavy=force_heavy)
    except Exception as e:
        _log(f"gate exception: {e}", "ERROR")
        return {
            "degraded": True,
            "error": f"gate:{type(e).__name__}:{e}",
            "plan": "NOTIFY_HUMAN",
            "urgency_score": 1.0,
            "confidence": 0.0,
            "is_safe_to_execute": False,
        }

    # 3+4. Ejecutar router con skills permitidas y prompt pesado opcional
    try:
        result = execute(state, CONFIG["skills"]["allowed"], g.use_heavy_prompt)
    except Exception as e:
        # Modo degraded: NOTIFY_HUMAN con urgency=1.0
        notify_human(
            reason=f"router_exception:{type(e).__name__}",
            state_preview=state,
            urgency=1.0,
        )
        _log(f"router exception → NOTIFY_HUMAN: {e}", "ERROR")
        return {
            "degraded": True,
            "error": str(e),
            "plan": "NOTIFY_HUMAN",
            "urgency_score": 1.0,
            "confidence": 0.0,
            "is_safe_to_execute": False,
        }

    # 5. Plan de acción según reglas del JSON
    result["plan"] = decide_action_plan(
        is_safe=result.get("is_safe_to_execute", False),
        confidence=result.get("confidence", 0.0),
        urgency=result.get("urgency_score", 0.0),
    )
    result["gate"] = g.model_dump()
    result["cache"] = "miss"

    # 6. Persistir en cache
    cache.put(state, result)
    _log(f"route plan={result['plan']} conf={result.get('confidence'):.2f} "
         f"urg={result.get('urgency_score'):.2f}")

    return result


# ═════════════════════════════════════════════════════════════
# mimo_cache_stats — la segunda tool expuesta a OpenCode
# ═════════════════════════════════════════════════════════════
def mimo_cache_stats() -> dict[str, Any]:
    """Stats del cache de decisiones — útil para detectar patrones recurrentes."""
    from cache import get_cache
    return get_cache().stats()


# ═════════════════════════════════════════════════════════════
# Servidor MCP (real o stub)
# ═════════════════════════════════════════════════════════════
def _build_mcp_server():
    """
    Construye el servidor MCP exponiendo las tools mimo_route y mimo_cache_stats.
    Si el paquete `mcp` no está instalado, usa mcp_stub._StubMCP automáticamente.
    """
    mcp, is_stub = get_mcp("mimo-router")

    # Nombres explícitos: README y system-one-router.json prometen
    # `mimo_route` y `mimo_cache_stats`; fn.__name__ daria *_tool.
    @mcp.tool(name="mimo_route")
    def mimo_route_tool(state: str, force_heavy: bool = False) -> dict:
        """Enruta un estado System One. Devuelve decision tipada + plan."""
        return mimo_route(state, force_heavy=force_heavy)

    @mcp.tool(name="mimo_cache_stats")
    def mimo_cache_stats_tool() -> dict:
        """Stats del cache de decisiones."""
        return mimo_cache_stats()

    if is_stub:
        _log("MCP no instalado — modo STUB activado (JSON-RPC sobre stdio)", "WARNING")
    else:
        _log("MCP real cargado (FastMCP)", "INFO")

    return mcp


# ═════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════
def _cli() -> int:
    ap = argparse.ArgumentParser(
        prog="mimo_patch",
        description="Parche Unificado Mimo Code — System One router",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # serve-mcp
    p_serve = sub.add_parser("serve-mcp", help="Arranca servidor MCP stdio para OpenCode")
    p_serve.add_argument("--log-level", default=None,
                         help="DEBUG|INFO|WARNING|ERROR")

    # classify
    p_cls = sub.add_parser("classify", help="Clasifica un estado")
    p_cls.add_argument("--state", required=False, default=None,
                       help="Estado a clasificar (si no se pasa, lee stdin)")
    p_cls.add_argument("--heavy", action="store_true",
                       help="Fuerza prompt pesado (Fable 5.1 completo)")

    # dry-run
    p_dry = sub.add_parser("dry-run", help="Simula routing sin llamar a ningún provider")
    p_dry.add_argument("--state", required=True)

    # stats
    sub.add_parser("stats", help="Muestra stats del cache de decisiones")

    # self-test
    p_self = sub.add_parser("self-test", help="Ejecuta matriz extendida de pruebas")
    p_self.add_argument("--state", default=None,
                        help="Estado base para la matriz (default: caso soporte)")

    args = ap.parse_args()

    # ── serve-mcp ─────────────────────────────────────────────
    if args.cmd == "serve-mcp":
        if args.log_level:
            os.environ["MIMO_LOG_LEVEL"] = args.log_level
        mcp = _build_mcp_server()
        mcp.run()
        return 0

    # ── classify ─────────────────────────────────────────────
    if args.cmd == "classify":
        state = args.state
        if not state:
            try:
                state = sys.stdin.read().strip()
            except Exception:
                state = ""
        if not state:
            print(json.dumps({"error": "empty state", "plan": "BLOCKED"}))
            return 1
        result = mimo_route(state, force_heavy=args.heavy)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0

    # ── dry-run (sin providers) ──────────────────────────────
    if args.cmd == "dry-run":
        from gate import gate_check, CONFIG
        g = gate_check(args.state, force_heavy=False)
        # Simula decision sin llamar a providers
        dry_decision = {
            "logic_trace": "dry_run_no_provider_call",
            "chosen_action": g.suggested_action or "ignore_spam",
            "confidence": 0.5 if g.use_heavy_prompt else 0.9,
            "urgency_score": g.urgency_score,
            "is_safe_to_execute": g.is_safe,
            "plan": decide_action_plan(
                g.is_safe,
                0.5 if g.use_heavy_prompt else 0.9,
                g.urgency_score,
            ),
            "gate": g.model_dump(),
            "dry_run": True,
            "degraded": False,
        }
        print(json.dumps(dry_decision, indent=2, ensure_ascii=False, default=str))
        return 0

    # ── stats ────────────────────────────────────────────────
    if args.cmd == "stats":
        print(json.dumps(mimo_cache_stats(), indent=2, ensure_ascii=False))
        return 0

    # ── self-test ────────────────────────────────────────────
    if args.cmd == "self-test":
        try:
            from gate import run_test_matrix_extended, CONFIG
            base = args.state or "usuario intentó chargeback por error 502"
            out = run_test_matrix_extended(base, CONFIG["skills"]["allowed"])
            print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
            # Exit code refleja cuántos planes son estables
            stable = sum(1 for r in out.get("results", [])
                         if r.get("plan") in ("EXECUTE_NOW", "PROPOSE_AND_WAIT",
                                              "ASK_CLARIFICATION", "BLOCKED"))
            total = len(out.get("results", []))
            print(f"\n[mimo] self-test: {stable}/{total} planes estables", file=sys.stderr)
            return 0 if stable == total else 2
        except Exception as e:
            print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
            return 2

    return 1


if __name__ == "__main__":
    sys.exit(_cli())
