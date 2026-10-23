# -*- coding: utf-8 -*-
"""Email delivery proposal. SMTP settings do not prove human authorization."""
from __future__ import annotations
from typing import Any
from .base import SkillBase


class SendEmailSkill(SkillBase):
    name = "send_email"
    description = "Propone un correo; requiere aprobación verificable y envío auditado."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        # Deliberately no SMTP connection. The current router does not issue
        # cryptographically verifiable, single-use approval grants.
        return {
            "success": False,
            "error": "email_not_configured: verifiable human approval required",
            "output": {"executed": False, "sent": False, "status": "requires_approval"},
        }
