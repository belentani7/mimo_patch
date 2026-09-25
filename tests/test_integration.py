# -*- coding: utf-8 -*-
"""
Tests del CLI mimo_patch y de notification.
"""
import os
import sys
import json
import subprocess
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mimo_patch import decide_action_plan
from notification import notify_human, _sanitize_preview


class TestDecideActionPlan:
    def test_blocked_when_unsafe(self):
        assert decide_action_plan(False, 0.99, 0.99) == "BLOCKED"

    def test_ask_clarification_when_low_confidence(self):
        assert decide_action_plan(True, 0.5, 0.99) == "ASK_CLARIFICATION"

    def test_execute_now_when_urgent(self):
        assert decide_action_plan(True, 0.9, 0.8) == "EXECUTE_NOW"

    def test_propose_when_low_urgency(self):
        assert decide_action_plan(True, 0.9, 0.5) == "PROPOSE_AND_WAIT"


class TestNotification:
    def test_sanitize_card(self):
        out = _sanitize_preview("mi tarjeta es 4111 1111 1111 1111")
        assert "[CARD]" in out
        assert "4111" not in out

    def test_sanitize_iban(self):
        out = _sanitize_preview("mi IBAN es ES9121000418450200051332")
        assert "[IBAN]" in out

    def test_sanitize_email(self):
        out = _sanitize_preview("contacto pedro@example.com")
        assert "[EMAIL]" in out

    def test_notify_to_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["MIMO_NOTIFY_FILE"] = os.path.join(tmp, "n.jsonl")
            payload = notify_human(
                reason="test_reason",
                state_preview="state preview text",
                urgency=1.0,
            )
            assert payload["kind"] == "NOTIFY_HUMAN"
            assert payload["urgency"] == 1.0
            # Verificar que se escribió a disco
            with open(os.environ["MIMO_NOTIFY_FILE"]) as f:
                line = f.readline()
                d = json.loads(line)
                assert d["reason"] == "test_reason"


class TestMimoRoute:
    def test_empty_state(self):
        from mimo_patch import mimo_route
        out = mimo_route("")
        assert out["degraded"] is True
        assert out["plan"] == "BLOCKED"
        assert out["is_safe_to_execute"] is False

    def test_safe_state_no_keys(self):
        """Sin API keys → heuristic provider."""
        keys_to_clear = [
            "TYPESAFE_API_KEY", "OPENROUTER_API_KEY",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        ]
        original = {k: os.getenv(k, "") for k in keys_to_clear}
        for k in keys_to_clear:
            os.environ.pop(k, None)
        os.environ["S1G_LOCAL_FIRST"] = "0"
        os.environ["OLLAMA_BASE_URL"] = "http://invalid:1234/v1"

        try:
            from mimo_patch import mimo_route
            out = mimo_route("usuario pregunta sobre horario")
            assert out["degraded"] is False
            assert out["plan"] in (
                "EXECUTE_NOW", "PROPOSE_AND_WAIT",
                "ASK_CLARIFICATION", "BLOCKED",
            )
        finally:
            for k, v in original.items():
                if v:
                    os.environ[k] = v


class TestCLI:
    def test_self_test(self):
        """Ejecutar self-test del CLI y verificar que no crashea."""
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, os.path.join(here, "mimo_patch.py"), "self-test"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONPATH": here},
        )
        # El self-test puede devolver 0 o 2 (planes inestables)
        # pero NUNCA 1 (error de sintaxis)
        assert result.returncode in (0, 2)
        # Output debe ser JSON parseable
        out_json = json.loads(result.stdout)
        assert "results" in out_json
        assert len(out_json["results"]) >= 10

    def test_stats(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, os.path.join(here, "mimo_patch.py"), "stats"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONPATH": here},
        )
        assert result.returncode == 0
        out = json.loads(result.stdout)
        assert "entries" in out
        assert "hits" in out
        assert "misses" in out

    def test_dry_run(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, os.path.join(here, "mimo_patch.py"), "dry-run",
             "--state", "usuario pregunta horario"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONPATH": here},
        )
        assert result.returncode == 0
        out = json.loads(result.stdout)
        assert out["dry_run"] is True
        assert out["plan"] in ("EXECUTE_NOW", "PROPOSE_AND_WAIT",
                                "ASK_CLARIFICATION", "BLOCKED")
