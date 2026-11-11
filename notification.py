# -*- coding: utf-8 -*-
"""
notification.py — Alertas humanas cuando el router entra en degraded mode.

Implementa el fallback_strategy del system-one-router.json:
  "on_degraded": "NOTIFY_HUMAN with urgency=1.0"

Canales soportados:
  - log     → append JSONL a logs/notify.jsonl (default)
  - stdout  → print directo a stdout (para tests)
  - webhook → POST a URL definida en MIMO_NOTIFY_WEBHOOK (futuro)

El payload SIEMPRE incluye:
  - ts (epoch)
  - kind="NOTIFY_HUMAN"
  - reason
  - state_preview (máx 200 chars — nunca exponer datos sensibles)
  - urgency (float [0,1])
  - channel
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def notify_human(
    *,
    reason: str,
    state_preview: str,
    urgency: float = 1.0,
    channel: str = "log",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Registra una alerta humana.

    Args:
        reason: identificador corto del motivo (ej: router_exception)
        state_preview: texto del estado (se trunca a 200 chars)
        urgency: float [0,1] — normalmente 1.0 en degraded
        channel: "log" | "stdout" | "webhook"
        extra: dict opcional con campos adicionales

    Returns:
        El payload enviado (útil para tests y para que el caller lo loguee).
    """
    # Sanitizar preview — nunca banking data, SQL, etc.
    preview = _sanitize_preview(state_preview)

    payload: dict[str, Any] = {
        "ts": time.time(),
        "kind": "NOTIFY_HUMAN",
        "reason": reason[:120],
        "state_preview": preview,
        "urgency": round(float(urgency), 4),
        "channel": channel,
    }
    if extra:
        payload["extra"] = {k: str(v)[:200] for k, v in extra.items()}

    if channel == "log":
        path = Path(os.getenv("MIMO_NOTIFY_FILE", "./logs/notify.jsonl"))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError:
            # Último recurso: stdout
            print(json.dumps(payload, ensure_ascii=False))

    elif channel == "stdout":
        print(json.dumps(payload, ensure_ascii=False))

    elif channel == "webhook":
        url = os.getenv("MIMO_NOTIFY_WEBHOOK", "")
        if url:
            try:
                import urllib.request
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=3).read()
            except Exception as e:
                # Webhook fallo → log fallback
                payload["webhook_error"] = str(e)[:200]
                path = Path(os.getenv("MIMO_NOTIFY_FILE", "./logs/notify.jsonl"))
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        else:
            # Sin URL configurada → log fallback
            path = Path(os.getenv("MIMO_NOTIFY_FILE", "./logs/notify.jsonl"))
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return payload


def _sanitize_preview(s: str) -> str:
    """Enmascara datos sensibles comunes antes de persistir."""
    if not s:
        return ""
    import re
    # Card numbers (16 dígitos seguidos o con espacios/guiones)
    s = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[CARD]", s)
    # IBAN (2 letras + 14-34 dígitos)
    s = re.sub(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,32}\b", "[IBAN]", s)
    # Email
    s = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]", s)
    # SQL injection básico
    s = re.sub(r"(?i)\b(or|and)\b\s+\d+\s*=\s*\d+", "[SQLI]", s)
    s = re.sub(r"(?i)\bunion\s+select\b", "[SQLI]", s)
    s = re.sub(r"(?i)\bdrop\s+table\b", "[SQLI]", s)
    return s[:200]
