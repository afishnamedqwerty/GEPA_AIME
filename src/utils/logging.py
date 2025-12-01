from __future__ import annotations

import json
import logging
from logging import Logger
from pathlib import Path
from typing import Any, Dict, Optional

from .helpers import PROJECT_ROOT

_DEFAULT_LOGGER_NAME = "gepa_aime"


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter used when trace_format=jsonl."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - inherited docstring
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in payload:
                continue
            if key in {"name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs", "relativeCreated", "thread", "threadName", "processName", "process"}:
                continue
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(level: str = "INFO", trace_format: str = "text", output_dir: Optional[str] = None, name: str = _DEFAULT_LOGGER_NAME) -> Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        # Logger already configured; only adjust level.
        logger.setLevel(level.upper())
        return logger

    logger.setLevel(level.upper())
    handler = logging.StreamHandler()
    if trace_format.lower() == "jsonl":
        handler.setFormatter(JsonFormatter())
    else:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
    logger.addHandler(handler)

    if output_dir:
        directory = Path(output_dir)
        if not directory.is_absolute():
            directory = PROJECT_ROOT / directory
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(directory / f"{name}.log", encoding="utf-8")
        if trace_format.lower() == "jsonl":
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(file_handler)
    return logger


def get_logger(name: Optional[str] = None) -> Logger:
    if name is None:
        name = _DEFAULT_LOGGER_NAME
    return logging.getLogger(name)


__all__ = ["setup_logger", "get_logger"]
