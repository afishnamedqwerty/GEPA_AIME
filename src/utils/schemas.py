from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

from . import helpers


@dataclass
class LLMConfig:
    model: str
    provider: str = "local"
    temperature: float = 0.2
    max_tokens: int = 512
    api_key_env: Optional[str] = None
    api_base: Optional[str] = None
    request_timeout: float = 30.0
    extra_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> "LLMConfig":
        data = helpers.ensure_dict(values)
        known_keys = {"model", "provider", "temperature", "max_tokens", "api_key_env", "api_base", "request_timeout"}
        extras = {k: v for k, v in data.items() if k not in known_keys}
        extra_params = helpers.ensure_dict(data.get("extra_params"))
        # Merge top-level unknown keys into extra_params to support shorthand config entries.
        for key, value in extras.items():
            if key == "extra_params":
                continue
            extra_params.setdefault(key, value)
        return cls(
            model=str(data.get("model", "mock-llm")),
            provider=str(data.get("provider", "local")),
            temperature=float(data.get("temperature", 0.2)),
            max_tokens=int(data.get("max_tokens", 512)),
            api_key_env=data.get("api_key_env"),
            api_base=data.get("api_base"),
            request_timeout=float(data.get("request_timeout", 30.0)),
            extra_params=extra_params,
        )


@dataclass
class GEPAConfig:
    num_candidates: int = 3
    max_rollouts: int = 5
    reflection_model: str = "mock-reflection"
    reflection_minibatch_size: int = 2
    use_merge: bool = True
    num_threads: int = 2
    skip_perfect_score: bool = True
    trace_path: Optional[str] = None

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> "GEPAConfig":
        data = helpers.ensure_dict(values)
        return cls(
            num_candidates=int(data.get("num_candidates", 3)),
            max_rollouts=int(data.get("max_rollouts", 5)),
            reflection_model=str(data.get("reflection_model", "mock-reflection")),
            reflection_minibatch_size=int(data.get("reflection_minibatch_size", 2)),
            use_merge=bool(data.get("use_merge", True)),
            num_threads=int(data.get("num_threads", 2)),
            skip_perfect_score=bool(data.get("skip_perfect_score", True)),
            trace_path=data.get("trace_path"),
        )


@dataclass
class ToolSpec:
    name: str
    description: str
    implementation: str
    config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> "ToolSpec":
        data = helpers.ensure_dict(values)
        return cls(
            name=str(data.get("name")),
            description=str(data.get("description", "")),
            implementation=str(data.get("implementation")),
            config={k: v for k, v in data.items() if k not in {"name", "description", "implementation"}},
        )


@dataclass
class ToolBundle:
    name: str
    tools: List[ToolSpec]

    @classmethod
    def from_mapping(cls, name: str, entries: Iterable[Mapping[str, Any]]) -> "ToolBundle":
        return cls(name=name, tools=[ToolSpec.from_dict(entry) for entry in entries])


def load_llm_config(path: str = "config/llm_config.yaml") -> LLMConfig:
    defaults = {
        "model": "mock-llm",
        "provider": "local",
        "temperature": 0.2,
        "max_tokens": 512,
        "request_timeout": 30.0,
    }
    data = helpers.load_yaml_config(path, defaults=defaults)
    return LLMConfig.from_dict(data)


def load_gepa_config(path: str = "config/gepa_config.yaml") -> GEPAConfig:
    data = helpers.load_yaml_config(path, defaults=GEPAConfig().__dict__)
    return GEPAConfig.from_dict(data)


def load_tool_bundles(path: str = "config/tool_bundles.json") -> Dict[str, ToolBundle]:
    raw = helpers.load_json_config(path, defaults={})
    bundles: Dict[str, ToolBundle] = {}
    for bundle_name, entries in raw.items():
        bundles[bundle_name] = ToolBundle.from_mapping(bundle_name, entries)
    return bundles


__all__ = [
    "LLMConfig",
    "GEPAConfig",
    "ToolSpec",
    "ToolBundle",
    "load_llm_config",
    "load_gepa_config",
    "load_tool_bundles",
]
