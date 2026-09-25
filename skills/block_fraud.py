# -*- coding: utf-8 -*-
"""block_fraud.py — Skill de bloqueo por fraude."""
from __future__ import annotations
import time
from typing import Any
from .base import SkillBase


class BlockFraudSkill(SkillBase):
    name = "block_fraud"
    description = "Bloquea una cuenta/usuario/IP por fraude sospechado."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        # En la vida real: llamar a Stripe Radar, Sift, etc.
        return {
            "success": True,
            "output": {
                "blocked": True,
                "block_id": f"BLK-{int(time.time())}",
                "reason": decision.get("logic_trace", "fraud_pattern"),
                "ttl": 3600,  # 1h bloqueo temporal, luego revisa humano
                "notify_human": True,
            },
        }
