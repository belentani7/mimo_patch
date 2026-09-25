# -*- coding: utf-8 -*-
"""
profile.py — Perfil del usuario (Pedro Belentani) y su proyecto.

Información derivada del chat 'Parche Unificador de IA Minimalista':
  - Perfil: Pedro Belentani
  - Proyecto: Belentani Judas Experience
  - Stack: Windows 11 + Termux/Huawei
  - Models locales: Ollama / LM Studio
  - Prioridades:
      * Privacidad/control local
      * Reducción de carga cognitiva
      * "Pereza de hablar" (post-procesamiento fatigue → gate como filtro)
  - Sensibilidad coste: prefiere $0 cuando sea posible
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserProfile:
    name: str
    project: str
    platform: str
    local_models: list[str] = field(default_factory=list)
    priorities: list[str] = field(default_factory=list)
    api_keys_to_use: list[str] = field(default_factory=list)
    timezone: Optional[str] = None


# Perfil hardcodeado del usuario (según el chat)
DEFAULT_USER = UserProfile(
    name="Pedro Belentani",
    project="Belentani Judas Experience",
    platform="Windows 11 + Termux/Huawei",
    local_models=["Ollama", "LM Studio"],
    priorities=[
        "privacy_local_first",
        "cognitive_load_reduction",
        "post_processing_fatigue",
        "cost_zero_when_possible",
    ],
    api_keys_to_use=[
        "TYPESAFE_API_KEY",       # Jev (preferido)
        "OPENROUTER_API_KEY",     # fallback multi-modelo
        "OPENAI_API_KEY",         # fallback generativo
        "ANTHROPIC_API_KEY",      # opcional
        "S1G_LOCAL_FIRST=1",     # Ollama local primero
    ],
    timezone="Europe/Madrid",
)


def get_profile() -> UserProfile:
    return DEFAULT_USER


def profile_summary() -> dict[str, object]:
    p = get_profile()
    return {
        "name": p.name,
        "project": p.project,
        "platform": p.platform,
        "local_models": p.local_models,
        "priorities": p.priorities,
        "timezone": p.timezone,
    }
