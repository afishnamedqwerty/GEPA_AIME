from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Iterator, List, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class TaskNode:
    task_id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[int] = None
    children: List[int] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {
            "id": self.task_id,
            "description": self.description,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "children": list(self.children),
            "metadata": dict(self.metadata),
        }


class ProgressManager:
    def __init__(self, initial_markdown: Optional[str] = None) -> None:
        self._tasks: Dict[int, TaskNode] = {}
        self._order: List[int] = []
        self._next_id = 1
        self._history: List[Dict[str, object]] = []
        if initial_markdown:
            self._load_from_markdown(initial_markdown)

    @property
    def history(self) -> List[Dict[str, object]]:
        return list(self._history)

    def record_history(self, event: Dict[str, object]) -> None:
        payload = dict(event)
        self._history.append(payload)

    def create_task(self, description: str, parent_id: Optional[int] = None, status: TaskStatus = TaskStatus.PENDING) -> TaskNode:
        existing = self.find_task(description, parent_id)
        if existing:
            # Keep the description up to date but do not reset status.
            existing.description = description
            return existing
        task_id = self._next_id
        self._next_id += 1
        node = TaskNode(task_id=task_id, description=description, status=status, parent_id=parent_id)
        self._tasks[task_id] = node
        if parent_id is None:
            self._order.append(task_id)
        else:
            self._tasks[parent_id].children.append(task_id)
        return node

    def find_task(self, description: str, parent_id: Optional[int] = None) -> Optional[TaskNode]:
        for node in self._tasks.values():
            if node.parent_id == parent_id and node.description.lower() == description.lower():
                return node
        return None

    def iter_tasks(self) -> Iterator[TaskNode]:
        for task_id in self._order:
            yield from self._iterate_branch(task_id)

    def _iterate_branch(self, task_id: int) -> Iterator[TaskNode]:
        node = self._tasks[task_id]
        yield node
        for child_id in node.children:
            yield from self._iterate_branch(child_id)

    def update_task_order(self, descriptions: Iterable[str]) -> List[TaskNode]:
        ordered_nodes: List[TaskNode] = []
        new_order: List[int] = []
        for description in descriptions:
            node = self.create_task(description, parent_id=None)
            ordered_nodes.append(node)
            new_order.append(node.task_id)
        if new_order:
            self._order = new_order
        return ordered_nodes

    def get_next_open_task(self) -> Optional[TaskNode]:
        for node in self.iter_tasks():
            if node.status in {TaskStatus.PENDING, TaskStatus.FAILED}:
                return node
        return None

    def set_status(self, task_id: int, status: TaskStatus) -> None:
        node = self._tasks[task_id]
        node.status = status

    def mark_in_progress(self, task_id: int) -> None:
        self.set_status(task_id, TaskStatus.IN_PROGRESS)

    def mark_complete(self, task_id: int, notes: Optional[str] = None) -> None:
        node = self._tasks[task_id]
        node.status = TaskStatus.COMPLETE
        if notes:
            node.metadata["notes"] = notes
        self.record_history({"task_id": task_id, "status": TaskStatus.COMPLETE.value, "notes": notes or ""})

    def mark_failed(self, task_id: int, notes: Optional[str] = None) -> None:
        node = self._tasks[task_id]
        node.status = TaskStatus.FAILED
        if notes:
            node.metadata["failure"] = notes
        self.record_history({"task_id": task_id, "status": TaskStatus.FAILED.value, "notes": notes or ""})

    def is_goal_complete(self) -> bool:
        return all(node.status == TaskStatus.COMPLETE for node in self._tasks.values()) and bool(self._tasks)

    def to_markdown(self) -> str:
        lines: List[str] = []
        for task_id in self._order:
            self._dump_branch(task_id, lines, indent=0)
        return "\n".join(lines)

    def _dump_branch(self, task_id: int, lines: List[str], indent: int) -> None:
        node = self._tasks[task_id]
        checkbox = {
            TaskStatus.PENDING: "[ ]",
            TaskStatus.IN_PROGRESS: "[-]",
            TaskStatus.COMPLETE: "[x]",
            TaskStatus.FAILED: "[!]",
        }[node.status]
        prefix = "    " * indent
        lines.append(f"{prefix}- {checkbox} {node.description}")
        for child_id in node.children:
            self._dump_branch(child_id, lines, indent + 1)

    def _load_from_markdown(self, markdown: str) -> None:
        pattern = re.compile(r"^(?P<indent>\s*)- \[(?P<marker>.|\s)\] (?P<description>.+)$")
        parent_stack: List[int] = []
        for line in markdown.splitlines():
            match = pattern.match(line)
            if not match:
                continue
            indent_level = len(match.group("indent")) // 4
            marker = match.group("marker")
            description = match.group("description").strip()
            status = {
                "x": TaskStatus.COMPLETE,
                "X": TaskStatus.COMPLETE,
                "-": TaskStatus.IN_PROGRESS,
                "!": TaskStatus.FAILED,
            }.get(marker, TaskStatus.PENDING)
            while len(parent_stack) > indent_level:
                parent_stack.pop()
            parent_id = parent_stack[-1] if parent_stack else None
            node = self.create_task(description, parent_id=parent_id, status=status)
            if indent_level >= len(parent_stack):
                parent_stack.append(node.task_id)
            else:
                parent_stack[indent_level] = node.task_id

    def describe(self) -> List[Dict[str, object]]:
        return [node.as_dict() for node in self.iter_tasks()]


__all__ = ["ProgressManager", "TaskNode", "TaskStatus"]
