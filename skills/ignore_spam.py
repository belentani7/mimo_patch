# -*- coding: utf-8 -*-
"""ignore_spam.py — Skill de ignore de spam."""
from __future__ import annotations
from typing import Any
from .base import SkillBase


class IgnoreSpamSkill(SkillBase):
    name = "ignore_spam"
    description = "Ignora el mensaje (detectado como spam)."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        # No action — solo log
        return {
            "success": True,
            "output": {
                "ignored": True,
                "spam_score": decision.get("confidence", 0.99),
                "no_action_taken": True,
            },
        }
