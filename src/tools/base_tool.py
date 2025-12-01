from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolError(Exception):
    """Raised when a tool execution fails in a controlled manner."""


@dataclass
class ToolContext:
    task: str
    goal: str
    progress_snapshot: str


class BaseTool:
    name: str = "base"
    description: str = ""

    def __init__(self, **config: Any) -> None:
        self.config = config

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:  # noqa: D401 - abstract
        raise NotImplementedError("Tool implementations must override run().")

    def __call__(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        return self.run(context, **kwargs)


__all__ = ["BaseTool", "ToolResult", "ToolError", "ToolContext"]
