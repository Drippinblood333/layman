#!/usr/bin/env python3
"""Probe Codex custom-provider request compatibility without using a real API key."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ProbeHandler(BaseHTTPRequestHandler):
    captured: list[dict] = []

    def log_message(self, _format: str, *_args) -> None:
        return

    def do_GET(self) -> None:
        body = json.dumps({"object": "list", "data": [{"id": "auto", "object": "model", "created": int(time.time()), "owned_by": "probe"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        request = json.loads(self.rfile.read(length) or b"{}")
        self.captured.append(request)
        response = {
            "id": "resp_layman_probe",
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "instructions": request.get("instructions"),
            "max_output_tokens": request.get("max_output_tokens"),
            "model": "gpt-5.6-luna",
            "output": [{"id": "msg_probe", "type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": "OK", "annotations": []}]}],
            "parallel_tool_calls": True,
            "previous_response_id": request.get("previous_response_id"),
            "reasoning": {"effort": "low", "summary": None},
            "store": False,
            "tools": request.get("tools", []),
            "usage": {"input_tokens": 1, "input_tokens_details": {"cached_tokens": 0}, "output_tokens": 1, "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 2},
        }
        event = json.dumps({"type": "response.completed", "response": response}, separators=(",", ":"))
        body = f"event: response.completed\ndata: {event}\n\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", 0), ProbeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="layman-codex-probe-") as temporary:
            home = Path(temporary)
            (home / "config.toml").write_text(
                'model = "auto"\nmodel_provider = "layman-probe"\n'
                '[model_providers.layman-probe]\n'
                'name = "Layman compatibility probe"\n'
                f'base_url = "http://127.0.0.1:{server.server_port}/v1"\n'
                'wire_api = "responses"\n'
                'env_key = "OPENAI_API_KEY"\n',
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["CODEX_HOME"] = str(home)
            env["OPENAI_API_KEY"] = "probe-only-not-a-real-key"
            completed = subprocess.run(
                [args.codex, "exec", "--skip-git-repo-check", "--sandbox", "read-only", "Return exactly OK."],
                env=env,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                check=False,
            )
        captured = ProbeHandler.captured[-1] if ProbeHandler.captured else {}
        report = {
            "codex_exit_code": completed.returncode,
            "request_captured": bool(captured),
            "model": captured.get("model"),
            "stream": captured.get("stream"),
            "has_tools": bool(captured.get("tools")),
            "has_instructions": bool(captured.get("instructions")),
            "previous_response_id_present": "previous_response_id" in captured,
            "stderr_tail": completed.stderr[-500:],
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if captured.get("model") == "auto" and captured.get("stream") is True else 1
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
