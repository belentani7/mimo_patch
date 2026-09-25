# -*- coding: utf-8 -*-
"""
skills package — acciones ejecutables por mimo_route.

Cada skill es un módulo Python con:
  - run(state: str, decision: dict) -> dict
  - SCHEMA (opcional): esquema de argumentos aceptados

Las skills son llamadas por el agente OpenCode externo cuando
mimo_route devuelve plan=EXECUTE_NOW y is_safe_to_execute=True.
"""
from .base import SkillBase, SkillResult
from .apply_refund import ApplyRefundSkill
from .apply_stripe_refund import ApplyStripeRefundSkill
from .escalate_support import EscalateSupportSkill
from .block_fraud import BlockFraudSkill
from .ignore_spam import IgnoreSpamSkill
from .send_email import SendEmailSkill

__all__ = [
    "SkillBase", "SkillResult",
    "ApplyRefundSkill", "ApplyStripeRefundSkill",
    "EscalateSupportSkill", "BlockFraudSkill",
    "IgnoreSpamSkill", "SendEmailSkill",
]

# Registry para lookup por nombre
SKILLS = {
    "apply_refund": ApplyRefundSkill(),
    "apply_stripe_refund": ApplyStripeRefundSkill(),
    "escalate_support": EscalateSupportSkill(),
    "block_fraud": BlockFraudSkill(),
    "ignore_spam": IgnoreSpamSkill(),
    "send_email": SendEmailSkill(),
}


def get_skill(name: str) -> SkillBase | None:
    return SKILLS.get(name)


def list_skills() -> list[str]:
    return list(SKILLS.keys())
