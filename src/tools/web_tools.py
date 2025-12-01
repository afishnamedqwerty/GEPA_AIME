from __future__ import annotations

import textwrap
from typing import Any

from .base_tool import BaseTool, ToolContext, ToolResult


class WebSearchTool(BaseTool):
    """Small deterministic stub representing a web search action."""

    name = "web_search"
    description = "Lookup facts from a curated offline index."

    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query") or context.task
        snippet = textwrap.shorten(
            f"Synthesised search results for '{query}' in relation to goal '{context.goal}'.",
            width=180,
            placeholder="...",
        )
        return ToolResult(content=snippet, metadata={"tool": self.name, "query": query})


__all__ = ["WebSearchTool"]
