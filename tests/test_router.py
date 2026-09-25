# -*- coding: utf-8 -*-
"""
Tests del router SystemOneRouter.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router import SystemOneRouter, SystemOneDecision, ActionEnum
from gate import CONFIG


class TestSystemOneDecision:
    def test_valid_decision(self):
        d = SystemOneDecision(
            logic_trace="refund_request",
            chosen_action=ActionEnum.APPLY_REFUND,
            confidence=0.95,
            urgency_score=0.4,
            is_safe_to_execute=True,
            suggested_skill_id="apply_refund",
        )
        assert d.chosen_action == ActionEnum.APPLY_REFUND
        assert d.confidence == 0.95

    def test_confidence_out_of_range(self):
        with pytest.raises(Exception):
            SystemOneDecision(
                logic_trace="x",
                chosen_action=ActionEnum.APPLY_REFUND,
                confidence=1.5,  # out of range
                urgency_score=0.0,
                is_safe_to_execute=True,
            )

    def test_invalid_action(self):
        with pytest.raises(Exception):
            SystemOneDecision(
                logic_trace="x",
                chosen_action="invalid_action",  # type: ignore
                confidence=0.5,
                urgency_score=0.0,
                is_safe_to_execute=True,
            )


class TestRouterHeuristic:
    """Test del provider heuristic (siempre disponible)."""

    def test_heuristic_fraud(self):
        # Sin API keys, el router cae al heuristic
        # (limpiar env temporalmente)
        keys_to_clear = [
            "TYPESAFE_API_KEY", "OPENROUTER_API_KEY",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        ]
        original = {k: os.getenv(k, "") for k in keys_to_clear}
        for k in keys_to_clear:
            os.environ.pop(k, None)
        os.environ["S1G_LOCAL_FIRST"] = "0"
        # Ollama también debería fallar porque no hay servidor
        os.environ["OLLAMA_BASE_URL"] = "http://invalid:1234/v1"

        try:
            r = SystemOneRouter(
                system_prompt="test",
                skills=CONFIG["skills"]["allowed"],
            )
            out = r.route("usuario solicita reembolso")
            # Debe caer a heuristic
            assert out["provider"] in ("heuristic", "ollama")
            assert out["chosen_action"] == "apply_refund"
            assert out["is_safe_to_execute"] is True
            assert 0.0 <= out["confidence"] <= 1.0
        finally:
            for k, v in original.items():
                if v:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

    def test_heuristic_fraud_blocked(self):
        r = SystemOneRouter(
            system_prompt="test",
            skills=CONFIG["skills"]["allowed"],
        )
        out = r.route("4111 1111 1111 1111 my card")
        assert out["is_safe_to_execute"] is False
        assert out["chosen_action"] == "block_fraud"

    def test_heuristic_spam(self):
        r = SystemOneRouter(
            system_prompt="test",
            skills=CONFIG["skills"]["allowed"],
        )
        out = r.route("GANADOR reclama tu premio ahora")
        assert out["chosen_action"] == "ignore_spam"
