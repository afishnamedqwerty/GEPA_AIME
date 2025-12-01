from __future__ import annotations

import json
from typing import Any, Dict, Optional

from . import helpers
from .schemas import LLMConfig

try:  # pragma: no cover - optional dependency
    import requests
except ImportError:  # pragma: no cover - fallback when requests unavailable
    requests = None  # type: ignore[assignment]


class BaseLLMClient:
    """Minimal synchronous interface expected by the planner and actors."""

    def generate(self, prompt: str, **kwargs: Any) -> str:  # noqa: D401 - interface definition
        raise NotImplementedError

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        return self.generate(prompt, **kwargs)


class LocalLLM(BaseLLMClient):
    """Deterministic echo-style model useful for tests and offline runs."""

    def __init__(self, model: str, temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature

    def generate(self, prompt: str, **kwargs: Any) -> str:
        tail = prompt.strip().splitlines()[-1] if prompt.strip() else ""
        return f"{self.model}::{tail}"


class VLLMClient(BaseLLMClient):
    """Thin wrapper around a hosted vLLM HTTP endpoint."""

    def __init__(
        self,
        model: str,
        api_base: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        endpoint: str = "/generate",
        default_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        if requests is None:
            raise RuntimeError("requests is required for VLLMClient but is not installed")
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.endpoint = endpoint
        self.session = requests.Session()
        self.api_key = api_key
        self.default_params = default_params.copy() if default_params else {}

    def generate(self, prompt: str, **kwargs: Any) -> str:
        payload = {"model": self.model, "prompt": prompt}
        payload.update(self.default_params)
        payload.update(kwargs)
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.api_base}/{self.endpoint.lstrip('/')}"
        response = self.session.post(url, json=payload, timeout=self.timeout, headers=headers)
        response.raise_for_status()
        data = response.json()
        return self._extract_text(data)

    def _extract_text(self, data: Any) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            if "text" in data:
                return str(data["text"])
            if "generated_text" in data:
                return str(data["generated_text"])
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                if isinstance(choice, dict):
                    if "text" in choice:
                        return str(choice["text"])
                    message = choice.get("message")
                    if isinstance(message, dict) and "content" in message:
                        return str(message["content"])
        return json.dumps(data)

    def close(self) -> None:
        if requests is None:
            return
        self.session.close()

    def __del__(self) -> None:  # pragma: no cover - cleanup
        try:
            self.close()
        except Exception:
            pass


def create_llm_client(config: LLMConfig) -> BaseLLMClient:
    provider = (config.provider or "local").lower()
    if provider in {"vllm", "remote"}:
        if not config.api_base:
            raise ValueError("api_base must be configured for vLLM provider")
        api_key = None
        if config.api_key_env:
            api_key = helpers.safe_getenv(config.api_key_env)
        params = dict(config.extra_params)
        endpoint = params.pop("endpoint", "/generate")
        return VLLMClient(
            model=config.model,
            api_base=config.api_base,
            api_key=api_key,
            timeout=config.request_timeout,
            endpoint=endpoint,
            default_params=params,
        )
    return LocalLLM(config.model, temperature=config.temperature)


__all__ = ["BaseLLMClient", "LocalLLM", "VLLMClient", "create_llm_client"]
