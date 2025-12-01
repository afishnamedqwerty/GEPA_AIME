from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TraceExample:
    prompt: str
    response: str
    score: float


class OptimizedDecomposition:
    """Minimal stand-in for a DSPy signature used by the optimizer."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    def improve_prompt(self, base_prompt: str, observation: str) -> str:
        suffix = f"\nReminder: incorporate feedback -> {observation[:80]}"
        return base_prompt + suffix


__all__ = ["TraceExample", "OptimizedDecomposition"]
