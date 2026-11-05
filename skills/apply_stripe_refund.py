"""Stripe refunds require an explicitly authorized, validated payment operation."""
from __future__ import annotations

from typing import Any

from .base import SkillBase


class ApplyStripeRefundSkill(SkillBase):
    name = "apply_stripe_refund"
    description = "Refund request guard: authorization required; no automatic charges."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        # A classifier's confidence score is not payment authorization.
        # Never generate fake refund IDs or report success without Stripe.
        return {
            "success": False,
            "error": "refund_requires_explicit_authorization",
            "output": {
                "processed": False,
                "reason": "Reembolsos deshabilitados hasta implementar verificación de titularidad, autorización explícita, importe y clave de idempotencia."
            },
        }
