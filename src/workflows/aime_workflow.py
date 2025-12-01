from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ..core.actor_factory import ActorFactory
from ..core.dynamic_planner import DynamicPlanner
from ..core.progress_manager import ProgressManager
from ..optimizer.gepa_optimizer import LightweightOnlineGEPA
from ..utils import logging as log_utils


@dataclass
class WorkflowReport:
    goal: str
    completed: bool
    tasks: List[Dict[str, object]]
    history: List[Dict[str, object]]
    rationale: str


class AIMEWorkflow:
    def __init__(
        self,
        planner: DynamicPlanner,
        factory: ActorFactory,
        progress_mgr: ProgressManager,
        gepa_optimizer: LightweightOnlineGEPA,
        max_iterations: int = 25,
        on_update: Optional[Callable[[Dict[str, object]], None]] = None,
    ) -> None:
        self.planner = planner
        self.factory = factory
        self.progress_mgr = progress_mgr
        self.gepa_optimizer = gepa_optimizer
        self.max_iterations = max_iterations
        self.logger = log_utils.get_logger(__name__)
        self.on_update = on_update
        self._last_rationale: str = ""

    def run(self, goal: str) -> WorkflowReport:
        self.planner.prompt = self.gepa_optimizer.current_prompt(self.planner.prompt)
        plan = self.planner.initialize(goal)
        self._last_rationale = plan.rationale
        self._publish_state()
        iterations = 0

        while iterations < self.max_iterations and plan.next_task:
            task = plan.next_task
            actor = self.factory.create_actor(actor_name=f"actor-{task.task_id}", goal=goal)
            outcome = actor.execute(task, goal, on_update=lambda: self._publish_state())
            self.planner.record_feedback(outcome.task_id, outcome.status, outcome.result)
            gepa_update = self.gepa_optimizer.record(self.planner.prompt, {
                "task_id": outcome.task_id,
                "status": outcome.status.value,
                "result": outcome.result,
            })
            if gepa_update:
                self.planner.prompt = gepa_update
                self.logger.debug("Planner prompt updated via GEPA.")
            plan = self.planner.refresh_plan()
            self._last_rationale = plan.rationale
            self._publish_state()
            iterations += 1

        completed = self.progress_mgr.is_goal_complete()
        report = WorkflowReport(
            goal=goal,
            completed=completed,
            tasks=self.progress_mgr.describe(),
            history=self.progress_mgr.history,
            rationale=self._last_rationale,
        )
        self._publish_state()
        return report

    def _publish_state(self, rationale: Optional[str] = None) -> None:
        if not self.on_update:
            return
        rationale_text = rationale if rationale is not None else self._last_rationale
        snapshot = {
            "tasks": self.progress_mgr.describe(),
            "history": self.progress_mgr.history,
            "gepa": self.gepa_optimizer.metrics(),
            "tui": self.progress_mgr.to_markdown(),
            "rationale": rationale_text,
        }
        try:
            self.on_update(snapshot)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.warning("Unable to push dashboard update: %s", exc)


__all__ = ["AIMEWorkflow", "WorkflowReport"]
