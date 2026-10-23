# -*- coding: utf-8 -*-
"""No unverified provider side effects or fabricated IDs from demo skills."""
import smtplib
import pytest

from skills import (
    ApplyRefundSkill, ApplyStripeRefundSkill, BlockFraudSkill,
    EscalateSupportSkill, SendEmailSkill, get_skill,
)

SENSITIVE = [
    ApplyRefundSkill, ApplyStripeRefundSkill, BlockFraudSkill,
    EscalateSupportSkill, SendEmailSkill,
]


@pytest.mark.parametrize("skill_type", SENSITIVE)
def test_sensitive_skill_fails_closed_even_when_keys_and_approval_are_claimed(
    skill_type, monkeypatch
):
    monkeypatch.setenv("SMTP_HOST", "smtp.invalid")
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_placeholder")
    monkeypatch.setattr(
        smtplib, "SMTP",
        lambda *args, **kwargs: pytest.fail("Unexpected SMTP connection"),
    )
    skill = skill_type()
    result = skill.run(
        "private case with contact details",
        {"approved": True, "human_approved": True, "confidence": 1.0,
         "urgency_score": 1.0, "amount": 100, "to": "person@example.invalid"},
    )
    assert result["success"] is False
    assert result["output"]["executed"] is False
    assert result["output"]["status"] == "requires_approval"
    assert "private case" not in str(result)
    assert not any(
        key in result["output"] for key in ("refund_id", "block_id", "ticket_id")
    )
    assert result["output"].get("sent") is not True


@pytest.mark.parametrize("skill_type", SENSITIVE)
def test_safe_run_does_not_turn_unconfigured_action_into_success(skill_type):
    result = skill_type().safe_run("private", {})
    assert result.success is False
    assert result.output["executed"] is False
    assert result.error is not None


def test_sensitive_skill_registry_points_to_fail_closed_implementations():
    for skill_type in SENSITIVE:
        registered = get_skill(skill_type.name)
        assert isinstance(registered, skill_type)
        assert registered.run("sensitive", {})["success"] is False


def test_spam_classification_does_not_claim_mailbox_action():
    from skills import IgnoreSpamSkill
    result = IgnoreSpamSkill().run("untrusted message", {"confidence": 0.97})
    assert result["success"] is True
    assert result["output"]["classification_only"] is True
    assert result["output"]["ignored"] is False
    assert result["output"]["no_action_taken"] is True
