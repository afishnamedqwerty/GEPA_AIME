from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Optional

from ..utils import helpers
from ..utils import logging as log_utils
from ..utils.metrics import enhanced_decomp_metric
from .signatures import OptimizedDecomposition, TraceExample


class LightweightOnlineGEPA:
    """Simplified online GEPA loop capturing traces and mutating prompts."""

    def __init__(
        self,
        student: OptimizedDecomposition,
        metric=enhanced_decomp_metric,
        window_size: int = 20,
        trace_path: Optional[str] = None,
    ) -> None:
        self.student = student
        self.metric = metric
        self.examples: Deque[TraceExample] = deque(maxlen=window_size)
        self.best_prompt: Optional[str] = None
        self.logger = log_utils.get_logger(__name__)
        self.trace_path = self._prepare_trace_path(trace_path)
        if self.trace_path and self.trace_path.exists():
            self._load_existing_traces()

    def record(self, base_prompt: str, outcome: Dict[str, object]) -> Optional[str]:
        status = str(outcome.get("status", ""))
        score = 1.0 if status == "complete" else 0.0
        example = TraceExample(prompt=base_prompt, response=str(outcome.get("result", "")), score=score)
        self.examples.append(example)
        metric_payload = [{"status": "complete" if ex.score >= 0.9 else "failed"} for ex in self.examples]
        composite_score = self.metric(metric_payload)
        new_prompt: Optional[str] = None
        if composite_score < 0.5:
            observation = str(outcome.get("result", ""))
            new_prompt = self.student.improve_prompt(base_prompt, observation)
            self.best_prompt = new_prompt
            self.logger.debug("GEPA updated planner prompt", extra={"score": composite_score})
        if self.trace_path:
            self._persist_example(example, new_prompt)
        return new_prompt

    def current_prompt(self, fallback: str) -> str:
        return self.best_prompt or fallback

    def _prepare_trace_path(self, trace_path: Optional[str]) -> Optional[Path]:
        if not trace_path:
            return None
        candidate = Path(trace_path)
        if not candidate.is_absolute():
            candidate = helpers.PROJECT_ROOT / candidate
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def _persist_example(self, example: TraceExample, new_prompt: Optional[str]) -> None:
        if not self.trace_path:
            return
        record = {
            "prompt": example.prompt,
            "response": example.response,
            "score": example.score,
        }
        if new_prompt is not None:
            record["new_prompt"] = new_prompt
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_existing_traces(self) -> None:
        if not self.trace_path or not self.trace_path.exists():
            return
        best_prompt: Optional[str] = None
        best_score: float = -1.0
        updated_prompt: Optional[str] = None
        with self.trace_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                data = line.strip()
                if not data:
                    continue
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    self.logger.warning("Skipping malformed GEPA trace line", extra={"line": data[:60]})
                    continue
                prompt = str(payload.get("prompt", ""))
                response = str(payload.get("response", ""))
                score = float(payload.get("score", 0.0))
                example = TraceExample(prompt=prompt, response=response, score=score)
                self.examples.append(example)
                if payload.get("new_prompt"):
                    updated_prompt = str(payload["new_prompt"])
                elif score > best_score:
                    best_prompt = prompt
                    best_score = score
        if updated_prompt:
            self.best_prompt = updated_prompt
        elif best_prompt:
            self.best_prompt = best_prompt


__all__ = ["LightweightOnlineGEPA"]