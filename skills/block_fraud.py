# -*- coding: utf-8 -*-
"""Fraud block proposal. No account/provider is modified by this stub."""
from __future__ import annotations
from typing import Any
from .base import SkillBase


class BlockFraudSkill(SkillBase):
    name = "block_fraud"
    description = "Propone revisar un bloqueo por fraude, sin aplicarlo."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": False,
            "error": "fraud_block_not_configured: human review and provider required",
            "output": {"executed": False, "status": "requires_approval"},
        }
