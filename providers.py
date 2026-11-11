# -*- coding: utf-8 -*-
"""
providers.py — Catálogo de providers de IA soportados por SystemOneRouter.

Lista estática de providers para que el código y la doc puedan referenciarla.
El orden de fallback en SystemOneRouter._providers() es:
  1. (si S1G_LOCAL_FIRST=1) Ollama local
  2. TypeSafe (Jev AI)        — si TYPESAFE_API_KEY
  3. OpenRouter               — si OPENROUTER_API_KEY
  4. OpenAI                   — si OPENAI_API_KEY
  5. Anthropic (Claude)       — si ANTHROPIC_API_KEY
  6. (si no S1G_LOCAL_FIRST) Ollama local
  7. Heurística determinista  — SIEMPRE (último recurso)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    default_model: str
    env_var: str
    cost_per_million_input: float
    cost_per_million_output: float
    supports_json_mode: bool
    supports_native_jev: bool
    notes: str = ""


# ─── Catálogo estático ────────────────────────────────────────
PROVIDERS: dict[str, Provider] = {
    "typesafe": Provider(
        name="TypeSafe (Jev)",
        base_url="https://api.typesafe.ai/v1",
        default_model="typesafe/jev-latest",
        env_var="TYPESAFE_API_KEY",
        cost_per_million_input=0.042,
        cost_per_million_output=0.0,
        supports_json_mode=True,
        supports_native_jev=True,
        notes="Modelo de Sistema 1 (no autorregresivo). $0 salida. "
              "70-500ms latencia. Zero alucinaciones.",
    ),
    "openrouter": Provider(
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="typesafe/jev-1.13",
        env_var="OPENROUTER_API_KEY",
        cost_per_million_input=0.042,
        cost_per_million_output=0.0,
        supports_json_mode=True,
        supports_native_jev=True,
        notes="Puede enrutar a Jev o a cualquier LLM generativo. "
              "Útil como fallback multi-modelo.",
    ),
    "openai": Provider(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        env_var="OPENAI_API_KEY",
        cost_per_million_input=0.150,
        cost_per_million_output=0.600,
        supports_json_mode=True,
        supports_native_jev=False,
        notes="JSON mode con response_format. Generativo (autorregresivo).",
    ),
    "anthropic": Provider(
        name="Anthropic (Claude)",
        base_url="https://api.anthropic.com",
        default_model="claude-3-5-haiku-20241022",
        env_var="ANTHROPIC_API_KEY",
        cost_per_million_input=0.800,
        cost_per_million_output=4.000,
        supports_json_mode=True,
        supports_native_jev=False,
        notes="Claude via instructor. Generativo. Fable 5.1 era el prompt interno.",
    ),
    "ollama": Provider(
        name="Ollama local",
        base_url="http://localhost:11434/v1",
        default_model="qwen2.5:7b-instruct",
        env_var="OLLAMA_BASE_URL",  # No requiere key
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        supports_json_mode=True,
        supports_native_jev=False,
        notes="Local. Coste $0. Privacidad total. Instalar aparte desde ollama.com.",
    ),
    "vercel_ai_gateway": Provider(
        name="Vercel AI Gateway",
        base_url="https://sdk.vercel.ai",
        default_model="typesafe-ai/jv",
        env_var="VERCEL_AI_GATEWAY_KEY",
        cost_per_million_input=0.042,
        cost_per_million_output=0.0,
        supports_json_mode=True,
        supports_native_jev=True,
        notes="Vía AI SDK de Vercel con experimental evaluate().",
    ),
    "cloudflare": Provider(
        name="Cloudflare Workers AI",
        base_url="https://api.cloudflare.com/client/v4",
        default_model="typesafe/ai.jeev",
        env_var="CLOUDFLARE_API_TOKEN",
        cost_per_million_input=0.042,
        cost_per_million_output=0.0,
        supports_json_mode=True,
        supports_native_jev=True,
        notes="Ejecuta en el borde. Baja latencia global.",
    ),
    "heuristic": Provider(
        name="Heurística determinista",
        base_url="(local)",
        default_model="regex+keywords",
        env_var="(none)",
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        supports_json_mode=True,
        supports_native_jev=False,
        notes="Último recurso. Siempre funciona. No requiere red.",
    ),
}


def list_providers() -> dict[str, dict]:
    """Lista todos los providers con sus metadatos."""
    return {
        key: {
            "name": p.name,
            "default_model": p.default_model,
            "cost_in": p.cost_per_million_input,
            "cost_out": p.cost_per_million_output,
            "native_jev": p.supports_native_jev,
            "notes": p.notes,
        }
        for key, p in PROVIDERS.items()
    }


def get_provider(name: str) -> Provider | None:
    return PROVIDERS.get(name)
