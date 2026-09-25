# -*- coding: utf-8 -*-
"""
primitives.py — Las 3 primitivas de Jev AI (Choice, Score, Boolean/Noul).

Jev no tiene ventana de chat. Solo responde a 3 tipos de preguntas exactas:
  - Choice (Elección): Selecciona una opción de una lista cerrada.
  - Score (Puntuación): Clasifica en una escala ordenada.
  - Noul / Boolean (Juicio): Responde sí/no con probabilidad [0,1].

Estas primitivas se implementan aquí como esquemas Pydantic — tu código
puede heredarlas para definir preguntas tipadas para Jev.

Ejemplo:
    class DepartmentChoice(Choice):
        options: list[str] = ["billing", "technical", "sales"]

    class UrgencyScore(Score):
        levels: list[str] = ["low", "medium", "high"]

    class SafetyBoolean(Noul):
        ...

El router usará estos esquemas cuando invoque a TypeSafe/Jev.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Choice(BaseModel):
    """Primitiva Choice — elige una opción de una lista cerrada."""
    choice: str = Field(description="Opción elegida.")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confianza en la elección [0,1]."
    )
    probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Distribución de probabilidad sobre todas las opciones."
    )


class Score(BaseModel):
    """Primitiva Score — clasifica en una escala ordenada de 2 a 10 niveles."""
    level: int = Field(ge=0, description="Nivel elegido.")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confianza en el nivel elegido [0,1]."
    )
    score: Optional[float] = Field(
        default=None,
        description="Valor continuo interpolado [0, max_level]."
    )


class Noul(BaseModel):
    """
    Primitiva Noul — probabilidad booleana.
    Responde una afirmación con un valor [0.0, 1.0].
    """
    value: float = Field(
        ge=0.0, le=1.0,
        description="Probabilidad de que la afirmación sea cierta [0,1]."
    )


# ─── Helpers para componer esquemas tipados ───────────────────
def typed_choice(options: list[str]) -> type[BaseModel]:
    """Genera un esquema Pydantic con Literal['a','b','c'] para Choice."""
    from typing import Literal
    if not options:
        raise ValueError("typed_choice requiere al menos 1 opción")
    literal = Literal[tuple(options)] if len(options) > 1 else options[0]  # type: ignore

    class _TypedChoice(Choice):
        choice: literal = Field(description="Opción elegida de la lista.")  # type: ignore

    _TypedChoice.__name__ = f"Choice_{'_'.join(o[:8] for o in options[:3])}"
    return _TypedChoice


def typed_score(levels: list[str]) -> type[BaseModel]:
    """Genera un esquema Score con max_level = len(levels)-1."""
    max_level = max(0, len(levels) - 1)

    class _TypedScore(Score):
        level: int = Field(ge=0, le=max_level,
                            description=f"Nivel [0..{max_level}]")
        # json_schema_extra para pasar los labels a Jev
        model_config = {
            "json_schema_extra": {"levels": levels},
        }

    _TypedScore.__name__ = f"Score_{len(levels)}levels"
    return _TypedScore


def typed_boolean(statement: str) -> type[BaseModel]:
    """Genera un esquema Noul para una afirmación específica."""
    class _TypedNoul(Noul):
        model_config = {
            "json_schema_extra": {"statement": statement},
        }

    _TypedNoul.__name__ = "Noul_custom"
    return _TypedNoul


__all__ = [
    "Choice", "Score", "Noul",
    "typed_choice", "typed_score", "typed_boolean",
]
