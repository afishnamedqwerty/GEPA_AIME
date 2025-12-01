from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from ..tools.base_tool import BaseTool, ToolContext
from ..utils import logging as log_utils
from .progress_manager import ProgressManager, TaskNode, TaskStatus


@dataclass
class ActorStep:
    thought: str
    action: str
    observation: str


@dataclass
class ActorOutput:
    task_id: int
    status: TaskStatus
    result: str
    steps: Iterable[ActorStep]


class DynamicActor:
    def __init__(self, name: str, llm, tools: Dict[str, BaseTool], progress_mgr: ProgressManager) -> None:
        self.name = name
        self.llm = llm
        self.tools = tools
        self.progress_mgr = progress_mgr
        self.logger = log_utils.get_logger(__name__)

    def execute(self, task: TaskNode, goal: str) -> ActorOutput:
        self.progress_mgr.mark_in_progress(task.task_id)
        steps: list[ActorStep] = []
        context = ToolContext(task=task.description, goal=goal, progress_snapshot=self.progress_mgr.to_markdown())

        tool_selection = self._pick_tool(task)
        summary = ""
        if tool_selection:
            tool, kwargs = tool_selection
            thought = f"Use {tool.name} tool to progress the task."
            try:
                result = tool(context, **kwargs)
                observation = result.content
                summary = observation
            except Exception as exc:  # pragma: no cover - defensive path
                observation = f"Tool {tool.name} failed: {exc}"
                summary = observation
                self.logger.warning("Tool execution failure", exc_info=exc)
            steps.append(ActorStep(thought=thought, action=tool.name, observation=observation))

        final_result = summary or f"Completed task '{task.description}' without external tools."
        steps.append(
            ActorStep(
                thought="Summarise the outcome and finalise the task.",
                action="finish",
                observation=final_result,
            )
        )
        self.progress_mgr.mark_complete(task.task_id, notes=final_result)
        return ActorOutput(task_id=task.task_id, status=TaskStatus.COMPLETE, result=final_result, steps=steps)

    def _pick_tool(self, task: TaskNode) -> Optional[Tuple[BaseTool, dict]]:
        description = task.description.lower()
        metadata = task.metadata
        if any(keyword in description for keyword in ["write", "draft", "document"]):
            if "path" in metadata and "content" in metadata:
                tool = self.tools.get("write_file")
                if tool:
                    return tool, {"path": metadata["path"], "content": metadata["content"]}
        if "read" in description and "path" in task.metadata:
            tool = self.tools.get("read_file")
            if tool:
                return tool, {"path": task.metadata["path"]}
        if any(keyword in description for keyword in ["list", "directory", "files"]):
            tool = self.tools.get("list_dir")
            if tool:
                return tool, {"path": task.metadata.get("path", ".")}
        tool = self.tools.get("web_search")
        if tool:
            return tool, {"query": task.description}
        return None


__all__ = ["DynamicActor", "ActorOutput", "ActorStep"]
