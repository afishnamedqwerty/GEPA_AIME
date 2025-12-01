from __future__ import annotations

import importlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(path: os.PathLike[str] | str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def load_yaml_config(path: os.PathLike[str] | str, defaults: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    full_path = _resolve_path(path)
    if not full_path.exists():
        if defaults is None:
            raise ValueError(f"Missing configuration file: {full_path}")
        return dict(defaults)
    with full_path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if defaults:
        merged: Dict[str, Any] = dict(defaults)
        merged.update(data)
        return merged
    return dict(data)


def load_json_config(path: os.PathLike[str] | str, defaults: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    full_path = _resolve_path(path)
    if not full_path.exists():
        if defaults is None:
            raise ValueError(f"Missing configuration file: {full_path}")
        return dict(defaults)
    with full_path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if defaults:
        merged: Dict[str, Any] = dict(defaults)
        merged.update(data)
        return merged
    return dict(data)


def load_initial_planner_prompt() -> str:
    return (
        "You are the dynamic planner for an adaptive multi-agent system. "
        "Break goals into concrete, trackable tasks ordered by execution priority. "
        "Return concise task descriptions suitable for progress tracking."
    )


def split_goal_into_tasks(goal: str, max_tasks: int = 6) -> List[str]:
    """Return a deterministic list of coarse tasks derived from the goal."""
    normalized = re.sub(r"\s+", " ", goal).strip()
    if not normalized:
        return []
    segments: List[str] = []
    for fragment in re.split(r"[.?!]\s*", normalized):
        frag = fragment.strip()
        if frag:
            segments.append(frag)
    if not segments:
        segments.append(normalized)
    # Further split long segments by conjunctions for higher granularity.
    tasks: List[str] = []
    for segment in segments:
        parts = re.split(r"\band\b|\bthen\b|,", segment, flags=re.IGNORECASE)
        for part in parts:
            candidate = part.strip()
            if candidate:
                tasks.append(candidate)
    # Remove duplicates while preserving order.
    seen: set[str] = set()
    unique_tasks: List[str] = []
    for task in tasks:
        canonical = task.lower()
        if canonical in seen:
            continue
        seen.add(canonical)
        unique_tasks.append(task)
    return unique_tasks[:max_tasks]


def ensure_dict(value: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if value is None:
        return {}
    return dict(value)


def ensure_list(value: Optional[Iterable[str]]) -> List[str]:
    if value is None:
        return []
    return [item for item in value]


def safe_getenv(key: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(key, default)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def import_from_string(path: str) -> Any:
    if ":" in path:
        module_name, attribute = path.split(":", 1)
    elif "#" in path:
        module_name, attribute = path.split("#", 1)
    else:
        module_name, attribute = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    try:
        return getattr(module, attribute)
    except AttributeError as exc:
        raise ImportError(f"{attribute!r} not found in module {module_name!r}") from exc


__all__ = [
    "PROJECT_ROOT",
    "load_yaml_config",
    "load_json_config",
    "load_initial_planner_prompt",
    "split_goal_into_tasks",
    "ensure_dict",
    "ensure_list",
    "safe_getenv",
    "import_from_string",
]
