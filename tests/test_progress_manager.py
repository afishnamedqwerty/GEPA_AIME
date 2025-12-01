import unittest

from src.core.progress_manager import ProgressManager, TaskStatus


class ProgressManagerTests(unittest.TestCase):
    def test_progress_manager_tracks_completion(self) -> None:
        manager = ProgressManager()
        tasks = manager.update_task_order(["Collect requirements", "Draft summary"])
        self.assertEqual(len(tasks), 2)

        next_task = manager.get_next_open_task()
        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.description, "Collect requirements")

        manager.mark_complete(next_task.task_id, notes="requirements captured")
        self.assertEqual(manager.history[-1]["status"], TaskStatus.COMPLETE.value)
        self.assertFalse(manager.is_goal_complete())

        remaining = manager.get_next_open_task()
        self.assertIsNotNone(remaining)
        manager.mark_complete(remaining.task_id)

        self.assertTrue(manager.is_goal_complete())
        markdown = manager.to_markdown()
        self.assertIn("- [x] Collect requirements", markdown)
        self.assertIn("- [x] Draft summary", markdown)

    def test_markdown_roundtrip(self) -> None:
        original = """- [ ] Parent task\n    - [x] Completed child\n    - [ ] Pending child\n"""
        manager = ProgressManager(initial_markdown=original)
        self.assertEqual(len(list(manager.iter_tasks())), 3)
        next_task = manager.get_next_open_task()
        self.assertIsNotNone(next_task)
        manager.mark_complete(next_task.task_id)
        self.assertGreaterEqual(manager.to_markdown().count("[x]"), 2)


if __name__ == "__main__":  # pragma: no cover - direct test execution
    unittest.main()
