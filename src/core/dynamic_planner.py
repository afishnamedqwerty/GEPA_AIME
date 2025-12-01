from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..utils import helpers, logging as log_utils
from .progress_manager import ProgressManager, TaskNode, TaskStatus


@dataclass
class PlannerResult:
    tasks: List[TaskNode]
    next_task: Optional[TaskNode]
    rationale: str


class DynamicPlanner:
    """Deterministic yet configurable planner relying on lightweight heuristics."""

    def __init__(
        self,
        llm: Callable[[str], str] | Any,
        progress_mgr: ProgressManager,
        initial_prompt: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.progress_mgr = progress_mgr
        self.prompt = initial_prompt or helpers.load_initial_planner_prompt()
        self.goal: Optional[str] = None
        self.logger = log_utils.get_logger(__name__)

    def initialize(self, goal: str) -> PlannerResult:
        self.goal = goal
        tasks = helpers.split_goal_into_tasks(goal)
        if not tasks:
            tasks = [goal]
        nodes = self.progress_mgr.update_task_order(tasks)
        rationale = self._llm_generate({"goal": goal, "tasks": tasks})
        next_task = self.progress_mgr.get_next_open_task()
        return PlannerResult(tasks=nodes, next_task=next_task, rationale=rationale)

    def refresh_plan(self) -> PlannerResult:
        if not self.goal:
            raise ValueError("Planner must be initialized with a goal before refresh.")
        tasks = [node.description for node in self.progress_mgr.iter_tasks()]
        rationale = self._llm_generate({"goal": self.goal, "tasks": tasks})
        next_task = self.progress_mgr.get_next_open_task()
        nodes = [self.progress_mgr.find_task(text) for text in tasks]
        filtered_nodes = [node for node in nodes if node]
        return PlannerResult(tasks=filtered_nodes, next_task=next_task, rationale=rationale)

    def record_feedback(self, task_id: int, status: TaskStatus, notes: str = "") -> None:
        payload = {
            "task_id": task_id,
            "status": status.value,
            "notes": notes,
        }
        self.logger.debug("Planner feedback: %s", payload)

    def evaluate_and_iterate(self, outcome: Dict[str, Any]) -> None:
        if not self.goal:
            return
        status = outcome.get("status")
        if status == TaskStatus.FAILED.value:
            self.prompt = (
                self.prompt
                + "\n" "Reminder: emphasise feasibility and request clarification when required."
            )

    def _llm_generate(self, payload: Dict[str, Any]) -> str:
        message = f"Goal: {payload['goal']}. Tasks: {', '.join(payload['tasks'])}."
        generator = getattr(self.llm, "generate", None)
        if callable(generator):
            raw = generator(self.prompt + "\n" + message)
            return self._as_text(raw)
        if callable(self.llm):
            raw = self.llm(self.prompt + "\n" + message)
            return self._as_text(raw)
        return self._as_text(message)

    def _as_text(self, raw: Any) -> str:
        if isinstance(raw, str):
            return raw
        if isinstance(raw, (list, tuple)):
            return self._as_text(raw[0]) if raw else ""
        text = getattr(raw, "text", None)
        if text is not None:
            return str(text)
        outputs = getattr(raw, "outputs", None)
        if outputs:
            first = outputs[0]
            inner_text = getattr(first, "text", None)
            if inner_text is not None:
                return str(inner_text)
        return str(raw)


__all__ = ["DynamicPlanner", "PlannerResult"]
