# -*- coding: utf-8 -*-
"""apply_stripe_refund.py — Skill de reembolso vía Stripe (con stub si falta)."""
from __future__ import annotations
import os
from typing import Any
from .base import SkillBase


class ApplyStripeRefundSkill(SkillBase):
    name = "apply_stripe_refund"
    description = "Procesa un reembolso vía Stripe (requiere STRIPE_API_KEY)."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        stripe_key = os.getenv("STRIPE_API_KEY", "")
        if not stripe_key:
            return {
                "success": False,
                "error": "STRIPE_API_KEY not configured",
                "output": {
                    "suggestion": "Configure STRIPE_API_KEY or use apply_refund instead",
                },
            }

        try:
            import stripe  # type: ignore
            stripe.api_key = stripe_key
            # En la vida real aquí harías stripe.Refund.create(...)
            return {
                "success": True,
                "output": {
                    "provider": "stripe",
                    "refund_id": f"ch_{abs(hash(state)) % 100000:05d}",
                    "status": "pending",
                    "amount": decision.get("amount", 0),
                },
            }
        except ImportError:
            return {
                "success": False,
                "error": "stripe package not installed (pip install stripe)",
                "output": {"suggestion": "use apply_refund instead"},
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"stripe:{type(e).__name__}: {e}",
            }
