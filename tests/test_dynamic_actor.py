import tempfile
import unittest
from pathlib import Path

from src.core.dynamic_actor import DynamicActor
from src.core.progress_manager import ProgressManager, TaskStatus
from src.tools.file_tools import ListDirectoryTool, ReadFileTool, WriteFileTool
from src.tools.web_tools import WebSearchTool


class DummyLLM:
    def generate(self, prompt: str) -> str:
        return prompt


class DynamicActorTests(unittest.TestCase):
    def test_dynamic_actor_completes_task(self) -> None:
        manager = ProgressManager()
        manager.create_task("Research the repository")
        actor = DynamicActor("researcher", DummyLLM(), {"web_search": WebSearchTool()}, manager)

        task = manager.get_next_open_task()
        outcome = actor.execute(task, "Understand the repository structure")
        self.assertIs(outcome.status, TaskStatus.COMPLETE)
        self.assertEqual(outcome.steps[-1].action, "finish")
        self.assertTrue(manager.is_goal_complete())

    def test_dynamic_actor_uses_file_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "notes.txt"
            file_path.write_text("agent notes", encoding="utf-8")

            manager = ProgressManager()
            node = manager.create_task("Read project notes from disk")
            node.metadata["path"] = str(file_path)

            tools = {
                "read_file": ReadFileTool(),
                "list_dir": ListDirectoryTool(),
                "web_search": WebSearchTool(),
            }
            actor = DynamicActor("analyst", DummyLLM(), tools, manager)

            outcome = actor.execute(node, "Understand notes")
            self.assertIn("agent notes", outcome.result)
            self.assertIs(outcome.status, TaskStatus.COMPLETE)

    def test_dynamic_actor_writes_file(self) -> None:
        manager = ProgressManager()
        node = manager.create_task("Write project summary to disk")
        target_dir = Path("test_artifacts")
        target_dir.mkdir(exist_ok=True)
        target_file = target_dir / "summary.txt"
        if target_file.exists():
            target_file.unlink()

        node.metadata["path"] = str(target_file)
        node.metadata["content"] = "Automated summary"

        tools = {
            "write_file": WriteFileTool(),
            "web_search": WebSearchTool(),
        }
        actor = DynamicActor("scribe", DummyLLM(), tools, manager)

        outcome = actor.execute(node, "Summarise progress")
        self.assertIs(outcome.status, TaskStatus.COMPLETE)
        self.assertTrue(target_file.exists())
        self.assertIn("Automated summary", target_file.read_text(encoding="utf-8"))

        if target_file.exists():
            target_file.unlink()
        try:
            if not any(target_dir.iterdir()):
                target_dir.rmdir()
        except FileNotFoundError:
            pass


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
