# -*- coding: utf-8 -*-
"""
Tests del contrato de tools MCP expuestas por serve-mcp.

README.md (lineas 27 y 230) y opencode/system-one-router.json prometen
que el servidor expone las tools `mimo_route` y `mimo_cache_stats`.
OpenCode las invoca por esos nombres via JSON-RPC sobre stdio.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DOCUMENTED_TOOLS = ("mimo_route", "mimo_cache_stats")


def _rpc_session(requests: list[dict]) -> list[dict]:
    """Arranca serve-mcp, manda las peticiones JSON-RPC y recoge respuestas."""
    payload = "".join(json.dumps(r) + "\n" for r in requests)
    result = subprocess.run(
        [sys.executable, os.path.join(_HERE, "mimo_patch.py"), "serve-mcp"],
        input=payload, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": _HERE},
    )
    responses = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return responses


class TestMcpToolContract:
    def test_tools_list_exposes_documented_names(self):
        """tools/list debe devolver mimo_route y mimo_cache_stats (README)."""
        responses = _rpc_session([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ])
        tools_resp = next(r for r in responses if r.get("id") == 2)
        names = {t["name"] for t in tools_resp["result"]["tools"]}
        for documented in _DOCUMENTED_TOOLS:
            assert documented in names, (
                f"tool '{documented}' documentada en README/system-one-router.json "
                f"no esta expuesta; tools reales: {sorted(names)}"
            )

    def test_tools_call_mimo_route(self):
        """tools/call name=mimo_route debe funcionar (OpenCode lo invoca asi)."""
        responses = _rpc_session([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "mimo_route",
                        "arguments": {"state": "usuario pregunta horario"}}},
        ])
        call_resp = next(r for r in responses if r.get("id") == 2)
        assert "error" not in call_resp, (
            f"tools/call mimo_route fallo: {call_resp.get('error')}"
        )
        text = call_resp["result"]["content"][0]["text"]
        decision = json.loads(text)
        assert "plan" in decision

    def test_tools_call_mimo_cache_stats(self):
        """tools/call name=mimo_cache_stats debe funcionar."""
        responses = _rpc_session([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "mimo_cache_stats", "arguments": {}}},
        ])
        call_resp = next(r for r in responses if r.get("id") == 2)
        assert "error" not in call_resp, (
            f"tools/call mimo_cache_stats fallo: {call_resp.get('error')}"
        )
        text = call_resp["result"]["content"][0]["text"]
        stats = json.loads(text)
        assert "entries" in stats
