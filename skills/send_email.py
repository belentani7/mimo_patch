# -*- coding: utf-8 -*-
"""Outgoing email skill. A routing decision is never permission to send."""
from __future__ import annotations

from typing import Any

from .base import SkillBase


class SendEmailSkill(SkillBase):
    name = "send_email"
    description = "Email preparation only until a verified consent flow is installed."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        # No simulated success and no automated external delivery.
        return {
            "success": False,
            "error": "email_requires_explicit_authorization",
            "output": {
                "sent": False,
                "to": decision.get("to"),
                "subject": decision.get("subject"),
                "reason": "Envío bloqueado: requiere autorización específica del usuario y validación del destinatario.",
            },
        }
