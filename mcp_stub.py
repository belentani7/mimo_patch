# -*- coding: utf-8 -*-
"""
mcp_stub.py — Stub compatible con FastMCP cuando el paquete `mcp>=0.9.0`
no está instalado.

Permite que `mimo_patch.py serve-mcp` funcione en entornos mínimos
(Termux sin pip mcp, Windows sin admin, etc.) sin romper.

El stub implementa:
  - Decorador @mcp.tool() que registra la fn en un dict interno.
  - mcp.run() con un bucle JSON-RPC mínimo sobre stdio, suficiente
    para que OpenCode (o cualquier cliente MCP) consuma las tools.

Si quieres MCP real con transporte avanzado (SSE, WebSocket, etc.),
instala `pip install mcp>=0.9.0` y FastMCP se cargará automáticamente.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable


class _StubMCP:
    """Reimplementación mínima de FastMCP para entornos sin paquete mcp."""

    def __init__(self, name: str):
        self.name = name
        self._tools: dict[str, Callable[..., Any]] = {}

    def tool(self):
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[fn.__name__] = fn
            # Conservamos nombre y docstring para tools/list
            return fn
        return decorator

    def run(self) -> None:
        """
        Bucle JSON-RPC mínimo sobre stdio.
        Soporta: initialize, tools/list, tools/call.
        """
        # Handshake inicial silencioso (initialize se espera antes de tools/list)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue

            method = req.get("method")
            req_id = req.get("id")

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": self.name, "version": "3.0.0-stub"},
                        "capabilities": {"tools": {}},
                    },
                }

            elif method == "tools/list":
                tools = []
                for name, fn in self._tools.items():
                    tools.append({
                        "name": name,
                        "description": (fn.__doc__ or "").strip(),
                        "inputSchema": _infer_schema(fn),
                    })
                resp = {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"tools": tools},
                }

            elif method == "tools/call":
                params = req.get("params", {}) or {}
                tool = params.get("name")
                args = params.get("arguments", {}) or {}
                if tool in self._tools:
                    try:
                        result = self._tools[tool](**args)
                        resp = {
                            "jsonrpc": "2.0", "id": req_id,
                            "result": {
                                "content": [
                                    {"type": "text",
                                     "text": json.dumps(result, ensure_ascii=False,
                                                        default=str)}
                                ]
                            },
                        }
                    except Exception as e:
                        resp = {
                            "jsonrpc": "2.0", "id": req_id,
                            "error": {"code": -32000,
                                      "message": f"{type(e).__name__}: {e}"},
                        }
                else:
                    resp = {
                        "jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32601,
                                  "message": f"tool '{tool}' not found"},
                    }

            elif method == "notifications/initialized":
                # notificación silenciosa
                continue

            elif method == "ping":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            else:
                resp = {
                    "jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601,
                              "message": f"method '{method}' not implemented (stub)"},
                }

            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def _infer_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Infiere un inputSchema JSON Schema simple de las anotaciones de la fn."""
    import inspect
    sig = inspect.signature(fn)
    props = {}
    required = []
    for name, p in sig.parameters.items():
        ann = p.annotation
        if ann is inspect.Parameter.empty or ann is str:
            jtype = "string"
        elif ann is bool:
            jtype = "boolean"
        elif ann is int:
            jtype = "integer"
        elif ann is float:
            jtype = "number"
        elif hasattr(ann, "__origin__"):
            jtype = "array"
        else:
            jtype = "object"
        props[name] = {"type": jtype}
        if p.default is inspect.Parameter.empty:
            required.append(name)
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def get_mcp(name: str):
    """
    Devuelve (FastMCP real, False) si mcp>=1.0.0 está disponible.
    Si no, devuelve (_StubMCP, True).
    """
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
        return FastMCP(name), False
    except Exception:
        return _StubMCP(name), True
