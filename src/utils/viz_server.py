from __future__ import annotations

import functools
import json
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from .helpers import PROJECT_ROOT
from . import logging as log_utils


class DashboardState:
    """In-memory snapshot of workflow progress for the web dashboard."""

    def __init__(self, static_dir: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "tasks": [],
            "gepa": {},
            "history": [],
            "tui": "",
            "rationale": "",
            "updated_at": time.time(),
        }
        self.static_dir = static_dir or (PROJECT_ROOT / "viz")
        self.logger = log_utils.get_logger(__name__)

    def set_state(self, payload: Dict[str, Any]) -> None:
        enriched = dict(payload)
        enriched.setdefault("tasks", [])
        enriched.setdefault("gepa", {})
        enriched.setdefault("history", [])
        enriched.setdefault("tui", "")
        enriched.setdefault("rationale", "")
        enriched["updated_at"] = time.time()
        with self._lock:
            self._state = enriched

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            # Round-trip through JSON to avoid leaking mutable references.
            return json.loads(json.dumps(self._state))


class _DashboardRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, state: DashboardState, **kwargs):
        self.state = state
        super().__init__(*args, **kwargs)

    def log_message(self, fmt: str, *args) -> None:  # pragma: no cover - dev ergonomics
        self.state.logger.debug(fmt, *args)

    def do_GET(self) -> None:  # pragma: no cover - exercised in manual runs
        if self.path.rstrip("/") == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            payload = self.state.snapshot()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()


def start_dashboard_server(state: DashboardState, port: int = 8765) -> ThreadingHTTPServer:
    """Serve static assets from viz/ and expose /api/state for live data."""
    handler = functools.partial(
        _DashboardRequestHandler,
        state=state,
        directory=str(state.static_dir),
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.logger.info("Dashboard available at http://127.0.0.1:%s", port)
    return server


def stop_dashboard_server(server: Optional[ThreadingHTTPServer]) -> None:
    if not server:
        return
    server.shutdown()
    server.server_close()


__all__ = ["DashboardState", "start_dashboard_server", "stop_dashboard_server"]
