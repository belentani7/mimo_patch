# -*- coding: utf-8 -*-
"""
token_budget.py — Pruning de tokens y gestión de presupuesto.

Jev soporta 32k tokens de estado y 64k total. Antes de mandar
el estado al router, lo podamos para:
  - Quitar duplicados obvios
  - Resumir conversaciones largas (truncar el medio, conservar inicio y final)
  - Eliminar campos nulos o vacíos
  - Limitar a max_state_chars (default 8000)

También calcula el coste estimado por provider.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any


# Estimación rápida: 1 token ≈ 4 chars (inglés) o ≈ 2.5 chars (español)
_CHARS_PER_TOKEN_ES = 2.5
_CHARS_PER_TOKEN_EN = 4.0

MAX_STATE_CHARS = int(os.getenv("MIMO_MAX_STATE_CHARS", "8000"))
MAX_STATE_TOKENS = 32000  # límite de Jev


def estimate_tokens(text: str) -> int:
    """Estimación barata del número de tokens."""
    if not text:
        return 0
    # Detectar si es mayoritariamente español
    es_chars = len(re.findall(r"[áéíóúñü¡¿]", text))
    if es_chars > 5:  # tiene acentos españoles
        return int(len(text) / _CHARS_PER_TOKEN_ES)
    return int(len(text) / _CHARS_PER_TOKEN_EN)


def prune_history(messages: list[dict[str, str]],
                  max_tokens: int = 28000) -> list[dict[str, str]]:
    """
    Poda una conversación larga para que entre en max_tokens.
    Conserva: system prompt (siempre) + primeros 2 + últimos 5 mensajes.
    """
    if not messages:
        return []
    total = sum(estimate_tokens(m.get("content", "")) for m in messages)
    if total <= max_tokens:
        return messages

    # Conservar el system prompt si es el primero
    system = []
    rest = messages
    if messages and messages[0].get("role") == "system":
        system = [messages[0]]
        rest = messages[1:]

    # Si todavía entra, devolver todo
    if (sum(estimate_tokens(m.get("content", ""))
            for m in system + rest) <= max_tokens):
        return system + rest

    # Si no, conservar primero 2 y último 5
    head = rest[:2] if len(rest) > 7 else rest
    tail = rest[-5:] if len(rest) > 7 else []
    middle = (rest[2:-5] if len(rest) > 7 else [])

    # Sumarizar el middle en 1 mensaje
    if middle:
        summary = " [..pruned..] ".join(
            m.get("content", "")[:100] for m in middle
        )[:500]
        summary_msg = {
            "role": "system",
            "content": f"[context_pruned:{len(middle)}_msgs] {summary}",
        }
        return system + head + [summary_msg] + tail

    return system + head + tail


def prune_state(state: str, max_chars: int = MAX_STATE_CHARS) -> str:
    """Trunca el estado a max_chars. Conserva el inicio y el final."""
    if len(state) <= max_chars:
        return state
    half = max_chars // 2
    return state[:half] + f"\n[...pruned {len(state) - max_chars} chars...]\n" + state[-half:]


def estimate_cost(provider_name: str, input_tokens: int,
                    output_tokens: int = 0) -> dict[str, float]:
    """Coste estimado en USD para un provider dado."""
    # Evitar import circular: los providers son catálogo estático
    try:
        from providers import PROVIDERS
        p = PROVIDERS.get(provider_name)
        if not p:
            return {"input": 0.0, "output": 0.0, "total": 0.0}
        cost_in = (input_tokens / 1_000_000) * p.cost_per_million_input
        cost_out = (output_tokens / 1_000_000) * p.cost_per_million_output
        return {
            "input": round(cost_in, 6),
            "output": round(cost_out, 6),
            "total": round(cost_in + cost_out, 6),
        }
    except Exception:
        return {"input": 0.0, "output": 0.0, "total": 0.0}


def compact_state_for_jev(state: str, skills: list[str]) -> str:
    """
    Prepara el estado para enviarlo a Jev:
    - prune_state (limite de chars)
    - append skills list
    - wrap in XML tags
    """
    s = prune_state(state)
    skills_str = ", ".join(skills) if skills else "(no skills)"
    return f"<system_state>{s}</system_state>\n<available_skills>{skills_str}</available_skills>"
