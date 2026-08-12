from __future__ import annotations

import json
from typing import Any


class SSECapture:
    """Capture only the terminal Responses event without retaining prompt or deltas."""

    def __init__(self) -> None:
        self.buffer = b""
        self.completed_response: dict[str, Any] | None = None

    def feed(self, chunk: bytes) -> None:
        self.buffer += chunk
        while b"\n\n" in self.buffer:
            event, self.buffer = self.buffer.split(b"\n\n", 1)
            self._consume_event(event)
        if len(self.buffer) > 2_000_000:
            self.buffer = self.buffer[-65_536:]

    def _consume_event(self, event: bytes) -> None:
        for line in event.splitlines():
            if not line.startswith(b"data:"):
                continue
            try:
                payload = json.loads(line[5:].strip())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if payload.get("type") in {"response.completed", "response.incomplete", "response.failed"}:
                response = payload.get("response")
                if isinstance(response, dict):
                    self.completed_response = response
