from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List

from .base_tool import BaseTool, ToolContext, ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the text contents of a file within the repository."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        if not path:
            raise ValueError("'path' argument is required for read_file tool")
        abs_path = Path(path)
        if not abs_path.is_absolute():
            abs_path = Path.cwd() / abs_path
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {abs_path}")
        if not abs_path.is_file():
            raise IsADirectoryError(f"Expected a file but got directory: {abs_path}")
        with abs_path.open("r", encoding="utf-8") as handle:
            content = handle.read()
        return ToolResult(content=content, metadata={"tool": self.name, "path": str(abs_path)})


class ListDirectoryTool(BaseTool):
    name = "list_dir"
    description = "List directory entries for a given path."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path") or os.curdir
        abs_path = Path(path)
        if not abs_path.is_absolute():
            abs_path = Path.cwd() / abs_path
        if not abs_path.exists():
            raise FileNotFoundError(f"Directory not found: {abs_path}")
        if not abs_path.is_dir():
            raise NotADirectoryError(f"Expected a directory but received: {abs_path}")
        entries: List[str] = sorted(entry.name for entry in abs_path.iterdir())
        listing = "\n".join(entries)
        return ToolResult(content=listing, metadata={"tool": self.name, "path": str(abs_path), "entries": entries})


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write text content to a file inside the current workspace."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        content = kwargs.get("content")
        if not path:
            raise ValueError("'path' argument is required for write_file tool")
        if content is None:
            raise ValueError("'content' argument is required for write_file tool")
        base_path = Path.cwd().resolve()
        target = Path(path)
        if not target.is_absolute():
            target = (base_path / target).resolve()
        else:
            target = target.resolve()
        if not str(target).startswith(str(base_path)):
            raise PermissionError("write_file tool may only operate within the workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else str(content)
        target.write_text(text, encoding="utf-8")
        return ToolResult(content=f"Wrote {len(text)} characters to {target}", metadata={"tool": self.name, "path": str(target)})


__all__ = ["ReadFileTool", "ListDirectoryTool", "WriteFileTool"]
