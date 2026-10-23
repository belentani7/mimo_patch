# -*- coding: utf-8 -*-
"""Stripe refund proposal. An API key alone never authorizes a refund."""
from __future__ import annotations
from typing import Any
from .base import SkillBase


class ApplyStripeRefundSkill(SkillBase):
    name = "apply_stripe_refund"
    description = "Propone un reembolso Stripe; no ejecuta transacciones."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": False,
            "error": "stripe_refund_not_configured: verified approval workflow required",
            "output": {"executed": False, "status": "requires_approval"},
        }
