from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ..tools.base_tool import BaseTool
from ..utils import helpers
from ..utils.schemas import ToolBundle, ToolSpec
from .dynamic_actor import DynamicActor
from .progress_manager import ProgressManager


class ActorFactory:
    def __init__(self, tool_registry: Dict[str, ToolBundle], progress_mgr: ProgressManager, default_llm) -> None:
        self.tool_registry = tool_registry
        self.progress_mgr = progress_mgr
        self.default_llm = default_llm

    def create_actor(
        self,
        actor_name: str,
        goal: str,
        bundles: Optional[Iterable[str]] = None,
        llm=None,
    ) -> DynamicActor:
        bundle_names = ["default"]
        if bundles:
            bundle_names.extend(list(bundles))
        tools = self._instantiate_tools(bundle_names)
        actor_llm = llm or self.default_llm
        return DynamicActor(actor_name, actor_llm, tools, self.progress_mgr)

    def _instantiate_tools(self, bundle_names: Iterable[str]) -> Dict[str, BaseTool]:
        tools: Dict[str, BaseTool] = {}
        for bundle_name in bundle_names:
            bundle = self.tool_registry.get(bundle_name)
            if not bundle:
                continue
            for spec in bundle.tools:
                instance = self._build_tool(spec)
                tools[spec.name] = instance
        return tools

    def _build_tool(self, spec: ToolSpec) -> BaseTool:
        tool_cls = helpers.import_from_string(spec.implementation)
        if spec.name == "update_progress":
            return tool_cls(self.progress_mgr, **spec.config)
        return tool_cls(**spec.config)


__all__ = ["ActorFactory"]
