# -*- coding: utf-8 -*-
"""send_email.py — Skill de envío de email."""
from __future__ import annotations
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any
from .base import SkillBase


class SendEmailSkill(SkillBase):
    name = "send_email"
    description = "Envía un email (bienvenida, notificación, soporte)."

    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        # Si no hay SMTP configurado, devolvemos stub
        smtp_host = os.getenv("SMTP_HOST", "")
        if not smtp_host:
            return {
                "success": True,
                "output": {
                    "sent": False,
                    "stub": True,
                    "to": decision.get("to", "unknown@example.com"),
                    "subject": decision.get("subject", "(no subject)"),
                    "reason": "SMTP not configured — dry-run only",
                },
            }

        try:
            to = decision.get("to", "")
            subject = decision.get("subject", "Notificación")
            body = decision.get("body", state[:500])

            msg = MIMEMultipart()
            msg["From"] = os.getenv("SMTP_FROM", "noreply@example.com")
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(
                smtp_host, int(os.getenv("SMTP_PORT", "587"))
            ) as server:
                if os.getenv("SMTP_USER", ""):
                    server.starttls()
                    server.login(
                        os.getenv("SMTP_USER", ""),
                        os.getenv("SMTP_PASSWORD", ""),
                    )
                server.send_message(msg)

            return {
                "success": True,
                "output": {"sent": True, "to": to, "subject": subject},
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"smtp:{type(e).__name__}: {e}",
            }
