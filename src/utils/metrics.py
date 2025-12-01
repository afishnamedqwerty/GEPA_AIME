from __future__ import annotations

from typing import Iterable, Mapping


def enhanced_decomp_metric(history: Iterable[Mapping[str, object]]) -> float:
    """Return a lightweight score balancing success rate and recency."""
    events = list(history)
    if not events:
        return 0.0
    total = len(events)
    successes = sum(1 for event in events if str(event.get("status", "")) == "complete")
    completion_rate = successes / total
    recency_bonus = 0.0
    for idx, event in enumerate(reversed(events), start=1):
        if str(event.get("status", "")) == "complete":
            recency_bonus = 1 / idx
            break
    # Score in [0, 1]
    score = min(1.0, completion_rate * 0.7 + recency_bonus * 0.3)
    return round(score, 3)


__all__ = ["enhanced_decomp_metric"]
