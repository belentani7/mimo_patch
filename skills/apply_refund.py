# -*- coding: utf-8 -*-
"""Generic refund proposal. No provider is wired; never invent a refund ID."""
from __future__ import annotations
from typing import Any
from .base import SkillBase


class ApplyRefundSkill(SkillBase):
    name = "apply_refund"
    description = "Propone un reembolso; requiere aprobación e integración verificable."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": False,
            "error": "refund_not_configured: approval and verified provider required",
            "output": {"executed": False, "status": "requires_approval"},
        }
