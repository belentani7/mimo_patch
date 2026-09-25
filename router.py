# -*- coding: utf-8 -*-
"""
router.py — SystemOneRouter con multi-provider fallback.

Inspirado en Jev AI (TypeSafe AI) — modelo de Sistema 1 que NO genera prosa.
Cuando Jev no está disponible (no hay API key), degrada elegantemente a:
  1. OpenRouter (typesafe/jev-1.13 o modelo generativo con JSON mode)
  2. OpenAI / Anthropic / compatible
  3. Ollama local (S1G_LOCAL_FIRST=1)
  4. Heurística determinista (último recurso — siempre funciona)

El router SIEMPRE devuelve un dict tipado con la misma forma
(SystemOneDecision), sin importar qué provider respondió.
"""
from __future__ import annotations

import json
import os
import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError


# ═════════════════════════════════════════════════════════════
# Esquema Pydantic — la jaula anti-alucinación
# ═════════════════════════════════════════════════════════════
class ActionEnum(str, Enum):
    """Acciones permitidas — estricto, no se puede salir."""
    APPLY_REFUND = "apply_refund"
    APPLY_STRIPE_REFUND = "apply_stripe_refund"
    ESCALATE_SUPPORT = "escalate_support"
    BLOCK_FRAUD = "block_fraud"
    IGNORE_SPAM = "ignore_spam"
    SEND_EMAIL = "send_email"


class SystemOneDecision(BaseModel):
    """Decisión tipada — cualquier provider debe responder a este esquema."""
    logic_trace: str = Field(
        description="Vector lógico, máx 15 palabras.",
        max_length=200,
    )
    chosen_action: ActionEnum = Field(
        description="Mejor acción a ejecutar (de las permitidas)."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confianza matemática [0.0, 1.0]."
    )
    urgency_score: float = Field(
        ge=0.0, le=1.0,
        description="Urgencia [0.0, 1.0]."
    )
    is_safe_to_execute: bool = Field(
        description="Guardrail de seguridad binario."
    )
    suggested_skill_id: Optional[str] = Field(
        default=None,
        description="Skill ID sugerida (opcional, igual a chosen_action)."
    )


# ═════════════════════════════════════════════════════════════
# SystemOneRouter — el orquestador
# ═════════════════════════════════════════════════════════════
class SystemOneRouter:
    """
    Router de Sistema 1. Intenta providers en orden hasta que uno responde.
    Si todos fallan → heurística determinista + NOTIFY_HUMAN upstream.
    """

    def __init__(
        self,
        system_prompt: str,
        skills: list[str],
        model: Optional[str] = None,
    ):
        self.system_prompt = system_prompt
        # Filtrar skills para que coincidan con el enum
        self.skills = [s for s in skills if s in {a.value for a in ActionEnum}]
        self.model = model
        # Provider chain
        self.typesafe_key = os.getenv("TYPESAFE_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.local_first = os.getenv("S1G_LOCAL_FIRST", "0") == "1"
        self.ollama_url = os.getenv("OLLAMA_BASE_URL",
                                    "http://localhost:11434/v1")
        # Cache del instructor client (lo crea lazy)
        self._instructor_client = None

    # ─── Provider chain ──────────────────────────────────────
    def _providers(self) -> list[tuple[str, callable]]:
        """Devuelve la lista de (nombre, fn_route) en orden de preferencia."""
        chain: list[tuple[str, callable]] = []
        if self.local_first:
            chain.append(("ollama", self._route_ollama))
        if self.typesafe_key:
            chain.append(("typesafe", self._route_typesafe))
        if self.openrouter_key:
            chain.append(("openrouter", self._route_openrouter))
        if self.openai_key:
            chain.append(("openai", self._route_openai))
        if self.anthropic_key:
            chain.append(("anthropic", self._route_anthropic))
        if not self.local_first:
            chain.append(("ollama", self._route_ollama))
        # Siempre último: heurística (siempre funciona)
        chain.append(("heuristic", self._route_heuristic))
        return chain

    # ─── Método principal ────────────────────────────────────
    def route(self, state: str) -> dict[str, Any]:
        """Enruta el estado — prueba providers en orden hasta uno responde."""
        errors: list[dict[str, str]] = []
        for name, fn in self._providers():
            try:
                t0 = time.time()
                decision = fn(state)
                latency_ms = (time.time() - t0) * 1000
                if decision is not None:
                    # Validar contra el esquema Pydantic
                    try:
                        if isinstance(decision, SystemOneDecision):
                            validated = decision
                        else:
                            validated = SystemOneDecision.model_validate(decision)
                        return {
                            "logic_trace": validated.logic_trace,
                            "chosen_action": validated.chosen_action.value,
                            "confidence": validated.confidence,
                            "urgency_score": validated.urgency_score,
                            "is_safe_to_execute": validated.is_safe_to_execute,
                            "suggested_skill_id": validated.suggested_skill_id
                                                  or validated.chosen_action.value,
                            "provider": name,
                            "latency_ms": round(latency_ms, 2),
                            # Heuristic es un provider válido, NO degraded.
                            # Degraded solo cuando todos fallan (ver más abajo).
                            "degraded": False,
                        }
                    except ValidationError as ve:
                        errors.append({
                            "provider": name,
                            "error": f"validation:{ve.errors()[:1]}",
                        })
                        continue
            except Exception as e:
                errors.append({
                    "provider": name,
                    "error": f"{type(e).__name__}:{e}",
                })
                continue

        # Si llegamos aquí, todos los providers fallaron — shouldn't happen
        # porque heuristic siempre funciona, pero defendemos igual.
        return {
            "logic_trace": "all_providers_failed",
            "chosen_action": "escalate_support",
            "confidence": 0.0,
            "urgency_score": 1.0,
            "is_safe_to_execute": False,
            "suggested_skill_id": "escalate_support",
            "provider": "none",
            "degraded": True,
            "errors": errors,
        }

    # ─── Provider: TypeSafe (Jev) ───────────────────────────
    def _route_typesafe(self, state: str) -> Optional[dict[str, Any]]:
        """Llama a Jev AI a través de TypeSafe."""
        if not self.typesafe_key:
            return None
        try:
            import instructor
            from openai import OpenAI
            client = instructor.from_openai(
                OpenAI(
                    base_url="https://api.typesafe.ai/v1",
                    api_key=self.typesafe_key,
                ),
                mode=instructor.Mode.JSON,
            )
            resp = client.chat.completions.create(
                model=self.model or "typesafe/jev-latest",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",
                     "content": f"<system_state>{state}</system_state>"},
                ],
                response_model=SystemOneDecision,
                max_tokens=500,
                temperature=0.0,
            )
            # instructor devuelve el objeto ya validado
            return resp.model_dump() if isinstance(resp, SystemOneDecision) else resp
        except ImportError:
            return None
        except Exception as e:
            raise RuntimeError(f"typesafe:{e}")

    # ─── Provider: OpenRouter ────────────────────────────────
    def _route_openrouter(self, state: str) -> Optional[dict[str, Any]]:
        """Llama vía OpenRouter (puede enrutar a Jev o a un modelo generativo)."""
        if not self.openrouter_key:
            return None
        try:
            import instructor
            from openai import OpenAI
            client = instructor.from_openai(
                OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.openrouter_key,
                ),
                mode=instructor.Mode.JSON,
            )
            model = self.model or "typesafe/jev-1.13"
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",
                     "content": f"<system_state>{state}</system_state>"},
                ],
                response_model=SystemOneDecision,
                max_tokens=500,
                temperature=0.0,
            )
            return resp.model_dump() if isinstance(resp, SystemOneDecision) else resp
        except ImportError:
            return None
        except Exception as e:
            raise RuntimeError(f"openrouter:{e}")

    # ─── Provider: OpenAI ───────────────────────────────────
    def _route_openai(self, state: str) -> Optional[dict[str, Any]]:
        """Llama a OpenAI con JSON mode."""
        if not self.openai_key:
            return None
        try:
            import instructor
            from openai import OpenAI
            client = instructor.from_openai(
                OpenAI(api_key=self.openai_key),
                mode=instructor.Mode.JSON,
            )
            resp = client.chat.completions.create(
                model=self.model or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",
                     "content": f"<system_state>{state}</system_state>"},
                ],
                response_model=SystemOneDecision,
                max_tokens=500,
                temperature=0.0,
            )
            return resp.model_dump() if isinstance(resp, SystemOneDecision) else resp
        except ImportError:
            return None
        except Exception as e:
            raise RuntimeError(f"openai:{e}")

    # ─── Provider: Anthropic ─────────────────────────────────
    def _route_anthropic(self, state: str) -> Optional[dict[str, Any]]:
        """Llama a Anthropic (Claude) — vía Anthropic SDK si está."""
        if not self.anthropic_key:
            return None
        try:
            import instructor
            from anthropic import Anthropic
            client = instructor.from_anthropic(
                Anthropic(api_key=self.anthropic_key),
            )
            resp = client.messages.create(
                model=self.model or "claude-3-5-haiku-20241022",
                max_tokens=500,
                system=self.system_prompt,
                messages=[{"role": "user",
                            "content": f"<system_state>{state}</system_state>"}],
                response_model=SystemOneDecision,
            )
            return resp.model_dump() if isinstance(resp, SystemOneDecision) else resp
        except ImportError:
            return None
        except Exception as e:
            raise RuntimeError(f"anthropic:{e}")

    # ─── Provider: Ollama local ─────────────────────────────
    def _route_ollama(self, state: str) -> Optional[dict[str, Any]]:
        """Llama a Ollama local (OpenAI-compatible endpoint)."""
        try:
            import instructor
            from openai import OpenAI
            client = instructor.from_openai(
                OpenAI(base_url=self.ollama_url, api_key="ollama"),
                mode=instructor.Mode.JSON,
            )
            resp = client.chat.completions.create(
                model=self.model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",
                     "content": f"<system_state>{state}</system_state>"},
                ],
                response_model=SystemOneDecision,
                max_tokens=500,
                temperature=0.0,
            )
            return resp.model_dump() if isinstance(resp, SystemOneDecision) else resp
        except ImportError:
            return None
        except Exception as e:
            raise RuntimeError(f"ollama:{e}")

    # ─── Provider: Heurística (SIEMPRE funciona) ─────────────
    def _route_heuristic(self, state: str) -> dict[str, Any]:
        """
        Último recurso — heurística determinista basada en keywords.
        NUNCA lanza excepción.

        Confianza escalada según cuántos triggers matcheen:
          - hard_block          → confidence=0.0 (unsafe), urgency=1.0
          - 3+ keyword triggers → confidence=0.95 (alta seguridad)
          - 2 keyword triggers  → confidence=0.85 (justo en threshold)
          - 1 keyword trigger   → confidence=0.75
          - 0 triggers (default) → confidence=0.5 (escalate_support)
        """
        from gate import _keyword_action, _estimate_urgency, _HARD_BLOCK_PATTERNS, _REFRAMING_PATTERNS

        # Mental reframing → block explícito
        for pat in _REFRAMING_PATTERNS:
            if pat.search(state):
                return {
                    "logic_trace": "heuristic:reframing_detected",
                    "chosen_action": "escalate_support",
                    "confidence": 0.0,
                    "urgency_score": 1.0,
                    "is_safe_to_execute": False,
                    "suggested_skill_id": None,
                }

        # Hard block → unsafe + block_fraud
        is_safe = True
        hard_blocked = False
        for pat in _HARD_BLOCK_PATTERNS:
            if pat.search(state):
                is_safe = False
                hard_blocked = True
                break

        if hard_blocked:
            return {
                "logic_trace": "heuristic:hard_block_pattern",
                "chosen_action": "block_fraud",
                "confidence": 0.0,
                "urgency_score": 1.0,
                "is_safe_to_execute": False,
                "suggested_skill_id": None,
            }

        action_str = _keyword_action(state) or "escalate_support"
        if action_str not in {a.value for a in ActionEnum}:
            action_str = "escalate_support"

        # Contar triggers para escalar confianza
        s = state.lower()
        trigger_count = 0
        # Urgency keywords
        if any(w in s for w in ("urgente", "urgent", "asap", "ahora")):
            trigger_count += 1
        # Fraud keywords
        if any(w in s for w in ("fraude", "fraud", "stolen", "robada", "robado",
                                  "sospech", "intrusi")):
            trigger_count += 1
        # Error HTTP
        if any(w in s for w in ("502", "500", "503", "403")):
            trigger_count += 1
        # Multiple attempts
        if any(w in s for w in ("5 intentos", "10 intentos", "multiple intentos",
                                  "intentos fallidos", "ip sospech")):
            trigger_count += 1
        # Action keyword match
        if action_str != "escalate_support":
            trigger_count += 1

        # Escalar confianza
        if trigger_count >= 3:
            confidence = 0.95
        elif trigger_count == 2:
            confidence = 0.85
        elif trigger_count == 1:
            confidence = 0.75
        else:
            confidence = 0.5

        urgency = _estimate_urgency(state)

        return {
            "logic_trace": f"heuristic:keyword_match:{action_str}:triggers={trigger_count}",
            "chosen_action": action_str,
            "confidence": confidence,
            "urgency_score": urgency,
            "is_safe_to_execute": is_safe,
            "suggested_skill_id": action_str,
        }
