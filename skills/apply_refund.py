# -*- coding: utf-8 -*-
"""apply_refund.py — Skill de reembolso genérico (no Stripe)."""
from __future__ import annotations
from typing import Any
from .base import SkillBase


class ApplyRefundSkill(SkillBase):
    name = "apply_refund"
    description = "Procesa un reembolso genérico."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        # Aquí iría la llamada real a BD / ORM
        # Por ahora devolvemos un stub con el estado procesado
        return {
            "success": True,
            "output": {
                "refund_id": f"RFD-{abs(hash(state)) % 100000:05d}",
                "status": "pending_review",
                "processed_state_preview": state[:200],
            },
        }
