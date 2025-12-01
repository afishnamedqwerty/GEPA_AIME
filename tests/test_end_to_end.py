import unittest

from src.main import build_workflow
from src.utils.llm import LocalLLM


class EndToEndTests(unittest.TestCase):
    def test_workflow_run_completes_goal(self) -> None:
        # Use a lightweight local stub to avoid heavy vLLM engine startup in tests.
        llm = LocalLLM(model="test-llm", temperature=0.0)
        workflow = build_workflow(llm)
        report = workflow.run("Document the repository structure and summarise the findings")

        self.assertTrue(report.completed)
        self.assertTrue(report.tasks)
        self.assertTrue(any(entry["status"] == "complete" for entry in report.history))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
