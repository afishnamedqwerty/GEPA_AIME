from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..core.actor_factory import ActorFactory
from ..core.dynamic_planner import DynamicPlanner
from ..core.progress_manager import ProgressManager, TaskStatus
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
    ) -> None:
        self.planner = planner
        self.factory = factory
        self.progress_mgr = progress_mgr
        self.gepa_optimizer = gepa_optimizer
        self.max_iterations = max_iterations
        self.logger = log_utils.get_logger(__name__)

    def run(self, goal: str) -> WorkflowReport:
        self.planner.prompt = self.gepa_optimizer.current_prompt(self.planner.prompt)
        plan = self.planner.initialize(goal)
        rationale = plan.rationale
        iterations = 0

        while iterations < self.max_iterations and plan.next_task:
            task = plan.next_task
            actor = self.factory.create_actor(actor_name=f"actor-{task.task_id}", goal=goal)
            outcome = actor.execute(task, goal)
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
            rationale = plan.rationale
            iterations += 1

        completed = self.progress_mgr.is_goal_complete()
        report = WorkflowReport(
            goal=goal,
            completed=completed,
            tasks=self.progress_mgr.describe(),
            history=self.progress_mgr.history,
            rationale=rationale,
        )
        return report


__all__ = ["AIMEWorkflow", "WorkflowReport"]
