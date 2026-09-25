# -*- coding: utf-8 -*-
"""
evaluation.py — Hooks de evaluación para Braintrust y LangSmith.

Si están instalados y configurados (env vars), registra cada decision
del router para evaluar la calidad de las decisiones en producción.

Si no están configurados, los hooks son no-op — no rompe el flujo.
"""
from __future__ import annotations

import os
import time
import json
from pathlib import Path
from typing import Any, Optional


def _enabled(name: str) -> bool:
    """True si la env var del provider existe y no está vacía."""
    val = os.getenv(name, "")
    return bool(val) and val.lower() not in ("0", "false", "none", "")


def log_decision(
    *,
    state: str,
    decision: dict[str, Any],
    latency_ms: float,
    provider: str,
    error: Optional[str] = None,
) -> dict[str, Any]:
    """
    Registra una decisión para evaluación posterior.
    Si Braintrust está configurado → log a Braintrust.
    Si LangSmith está configurado → log a LangSmith.
    Siempre: append a logs/decisions.jsonl (audit local).
    """
    entry = {
        "ts": time.time(),
        "state_preview": state[:200],
        "decision": decision,
        "latency_ms": latency_ms,
        "provider": provider,
        "error": error,
    }

    # Audit local siempre
    try:
        path = Path(os.getenv("MIMO_DECISIONS_FILE", "./logs/decisions.jsonl"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass

    # Braintrust (opcional)
    if _enabled("BRAINTRUST_API_KEY"):
        try:
            _log_to_braintrust(entry)
        except Exception:
            pass

    # LangSmith (opcional)
    if _enabled("LANGSMITH_API_KEY"):
        try:
            _log_to_langsmith(entry)
        except Exception:
            pass

    return entry


def _log_to_braintrust(entry: dict[str, Any]) -> None:
    """Log a Braintrust via autoamtch SDK."""
    try:
        from braintrust import Eval  # type: ignore
        # Eval es pesado — para decisiones individuales, usamos Logger
        from braintrust import Logger  # type: ignore
        logger = Logger(project="mimo_patch")
        logger.log(
            input=entry["state_preview"],
            output=entry["decision"],
            metadata={
                "latency_ms": entry["latency_ms"],
                "provider": entry["provider"],
                "error": entry["error"],
            },
        )
    except ImportError:
        pass


def _log_to_langsmith(entry: dict[str, Any]) -> None:
    """Log a LangSmith via LangChain callback."""
    try:
        from langsmith import Client  # type: ignore
        client = Client()
        client.create_run(
            name="mimo_route",
            inputs={"state": entry["state_preview"]},
            outputs={"decision": entry["decision"]},
            metadata={
                "latency_ms": entry["latency_ms"],
                "provider": entry["provider"],
            },
        )
    except ImportError:
        pass
    except Exception:
        pass


def get_stats() -> dict[str, Any]:
    """Lee stats del log local (sin Braintrust/LangSmith)."""
    path = Path(os.getenv("MIMO_DECISIONS_FILE", "./logs/decisions.jsonl"))
    if not path.exists():
        return {"total": 0}
    count = 0
    providers: dict[str, int] = {}
    plans: dict[str, int] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                count += 1
                p = e.get("provider", "unknown")
                providers[p] = providers.get(p, 0) + 1
                plan = (e.get("decision") or {}).get("plan", "unknown")
                plans[plan] = plans.get(plan, 0) + 1
            except json.JSONDecodeError:
                continue
    return {
        "total": count,
        "providers": providers,
        "plans": plans,
    }
