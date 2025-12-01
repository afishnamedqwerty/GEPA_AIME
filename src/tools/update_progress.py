from __future__ import annotations

from typing import Any

from .base_tool import BaseTool, ToolContext, ToolResult


class UpdateProgressTool(BaseTool):
    name = "update_progress"
    description = "Persist a structured progress update via the progress manager."

    def __init__(self, progress_manager, **config: Any) -> None:  # type: ignore[override]
        super().__init__(**config)
        self.progress_manager = progress_manager

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        status = kwargs.get("status", "complete")
        notes = kwargs.get("notes", context.task)
        payload = {
            "task": context.task,
            "status": status,
            "notes": notes,
        }
        self.progress_manager.record_history(payload)
        return ToolResult(content=f"Recorded status={status} for task", metadata=payload)


__all__ = ["UpdateProgressTool"]
