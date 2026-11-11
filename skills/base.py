# -*- coding: utf-8 -*-
"""
base.py — Interfaz común para todas las skills.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class SkillResult(BaseModel):
    """Resultado estándar de toda skill."""
    skill: str = Field(description="Nombre de la skill ejecutada.")
    success: bool = Field(description="Si la skill se ejecutó correctamente.")
    output: dict[str, Any] = Field(
        default_factory=dict,
        description="Datos devueltos por la skill.",
    )
    error: str | None = Field(
        default=None,
        description="Mensaje de error si success=False.",
    )
    duration_ms: float = Field(
        default=0.0, description="Duración de la ejecución en ms."
    )


class SkillBase(ABC):
    """Clase base de las skills."""

    name: str = "abstract"
    description: str = "Skill abstract base."

    @abstractmethod
    def run(self, state: str, decision: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta la skill. Devuelve un dict con:
          - success: bool
          - output: dict
          - error: str | None
        """
        ...

    def safe_run(self, state: str, decision: dict[str, Any]) -> SkillResult:
        """Wrapper con timing y catch de excepciones."""
        t0 = time.time()
        try:
            result = self.run(state, decision)
            return SkillResult(
                skill=self.name,
                success=bool(result.get("success", True)),
                output=result.get("output", {}),
                error=result.get("error"),
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return SkillResult(
                skill=self.name,
                success=False,
                error=f"{type(e).__name__}: {e}",
                duration_ms=(time.time() - t0) * 1000,
            )
