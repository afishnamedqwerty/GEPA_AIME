import unittest

from src.main import build_workflow


class EndToEndTests(unittest.TestCase):
    def test_workflow_run_completes_goal(self) -> None:
        workflow = build_workflow()
        report = workflow.run("Document the repository structure and summarise the findings")

        self.assertTrue(report.completed)
        self.assertTrue(report.tasks)
        self.assertTrue(any(entry["status"] == "complete" for entry in report.history))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
