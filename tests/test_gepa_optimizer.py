import unittest

from pathlib import Path

from src.optimizer.gepa_optimizer import LightweightOnlineGEPA
from src.optimizer.signatures import OptimizedDecomposition


class DummyLLM:
    def generate(self, prompt: str) -> str:
        return prompt


class GEPAOptimizerTests(unittest.TestCase):
    def test_gepa_updates_prompt_on_low_score(self) -> None:
        student = OptimizedDecomposition(DummyLLM())
        trace_dir = Path("test_artifacts")
        trace_dir.mkdir(exist_ok=True)
        trace_path = trace_dir / "gepa_trace.jsonl"
        if trace_path.exists():
            trace_path.unlink()

        optimizer = LightweightOnlineGEPA(student, window_size=5, trace_path=str(trace_path))

        prompt = "Base prompt"
        update = optimizer.record(prompt, {"status": "failed", "result": "Outcome lacking detail"})
        self.assertIsNotNone(update)
        self.assertIn("Reminder", update)

        update_again = optimizer.record(prompt, {"status": "complete", "result": "All good"})
        if update_again is not None:
            self.assertIsInstance(update_again, str)

        self.assertTrue(trace_path.exists())
        contents = trace_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(contents), 2)

        # Rehydrate optimizer to ensure persisted prompt is reused.
        revived = LightweightOnlineGEPA(student, window_size=5, trace_path=str(trace_path))
        self.assertEqual(revived.current_prompt(prompt), update or prompt)

        if trace_path.exists():
            trace_path.unlink()
        try:
            if not any(trace_dir.iterdir()):
                trace_dir.rmdir()
        except FileNotFoundError:
            pass


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
