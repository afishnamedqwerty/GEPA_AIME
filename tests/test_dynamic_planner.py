import unittest

from src.core.dynamic_planner import DynamicPlanner
from src.core.progress_manager import ProgressManager, TaskStatus


class DummyLLM:
    def generate(self, prompt: str) -> str:
        return f"analysis::{prompt.splitlines()[-1]}"


class DynamicPlannerTests(unittest.TestCase):
    def test_planner_initializes_tasks(self) -> None:
        manager = ProgressManager()
        planner = DynamicPlanner(DummyLLM(), manager)

        result = planner.initialize("Research and summarise the project goals then prepare a recap.")
        self.assertIsNotNone(result.next_task)
        self.assertGreaterEqual(len(result.tasks), 2)

        task = result.next_task
        manager.mark_failed(task.task_id, notes="just testing failure")
        planner.evaluate_and_iterate({"status": TaskStatus.FAILED.value, "result": "missing info"})
        self.assertIn("Reminder", planner.prompt)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
