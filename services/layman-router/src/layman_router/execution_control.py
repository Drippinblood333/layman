from __future__ import annotations

import json
import os
import queue
import re
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, IO, Sequence


USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")
_USAGE_ALIASES = {
    "input_tokens": "input_tokens",
    "cached_input_tokens": "cached_input_tokens",
    "cached_tokens": "cached_input_tokens",
    "output_tokens": "output_tokens",
    "reasoning_tokens": "reasoning_tokens",
}
_TOOL_TYPES = {"command_execution", "mcp_tool_call", "file_read", "tool_call"}
_PATH_EXTENSIONS = (
    r"(?:py|pyi|js|mjs|cjs|ts|tsx|jsx|go|rs|java|kt|kts|scala|c|h|cc|cpp|cxx|hpp|"
    r"cs|fs|fsx|vb|php|rb|swift|dart|lua|r|jl|ex|exs|erl|hrl|hs|lhs|clj|cljs|"
    r"vue|svelte|html?|css|scss|sass|less|md|mdx|txt|rst|csv|tsv|xml|json|jsonl|"
    r"ya?ml|toml|ini|cfg|conf|properties|env|sql|graphql|gql|proto|sh|bash|zsh|fish|"
    r"ps1|psm1|bat|cmd|dockerfile|lock)"
)
_QUOTED_PATH_PATTERN = re.compile(rf"(?i)(?:\"([^\"\r\n]+\.{_PATH_EXTENSIONS})\"|'([^'\r\n]+\.{_PATH_EXTENSIONS})')")
_TOKEN_PATH_PATTERN = re.compile(
    rf"(?i)(?<![\w.-])((?:(?:[A-Z]:)?[\\/])?(?:[\w.-]+[\\/])+[\w.-]+\.{_PATH_EXTENSIONS}|"
    rf"[\w.-]+\.{_PATH_EXTENSIONS})(?![\w.-])"
)
_STDERR_LIMIT = 16_384


class CancellationToken:
    """A process-local cancellation signal that never stores request content."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        with self._lock:
            if self._event.is_set():
                return
            self._event.set()
            process = self._process
        if process is not None and process.poll() is None:
            threading.Thread(target=_terminate_process_tree, args=(process,), daemon=True).start()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def bind(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._process = process
            cancelled = self._event.is_set()
        if cancelled and process.poll() is None:
            _terminate_process_tree(process)

    def unbind(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            if self._process is process:
                self._process = None


@dataclass(frozen=True)
class StreamedProcessResult:
    returncode: int
    stderr: str
    usage: dict[str, int]
    usage_available: bool
    tool_calls: int
    unique_files_read: int
    compactions: int
    stop_reason: str | None = None


class EventBudgetTracker:
    """Keep numeric Codex event metadata without retaining event or message text."""

    def __init__(self) -> None:
        self.usage = {key: 0 for key in USAGE_KEYS}
        self.usage_available = False
        self.tool_calls = 0
        self.compactions = 0
        self._files: set[str] = set()
        self._tool_ids: set[str] = set()
        self._compaction_ids: set[str] = set()

    @property
    def unique_files_read(self) -> int:
        return len(self._files)

    def consume(self, line: str) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return
        self._visit_usage(event)
        self._visit_paths(event)
        self._visit_operations(event, envelope=event if isinstance(event, dict) else {})

    def _visit_usage(self, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                alias = _USAGE_ALIASES.get(key)
                if alias is not None and isinstance(child, int):
                    self.usage_available = True
                    self.usage[alias] = max(self.usage[alias], child)
                else:
                    self._visit_usage(child)
        elif isinstance(value, list):
            for child in value:
                self._visit_usage(child)

    def _visit_paths(self, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"path", "file"} and isinstance(child, str):
                    self._add_path(child)
                elif key in {"command", "cmd"} and isinstance(child, str):
                    command = child
                    for match in _QUOTED_PATH_PATTERN.finditer(child):
                        self._add_path(match.group(1) or match.group(2))
                        command = command.replace(match.group(0), " ")
                    for match in _TOKEN_PATH_PATTERN.finditer(command):
                        self._add_path(match.group(1))
                elif key not in {"output", "aggregated_output", "stdout", "stderr", "message", "text"}:
                    self._visit_paths(child)
        elif isinstance(value, list):
            for child in value:
                self._visit_paths(child)

    def _add_path(self, value: str) -> None:
        path = value.strip(" '\"")
        if re.search(rf"(?i)\.{_PATH_EXTENSIONS}$", path):
            self._files.add(os.path.normcase(path.replace("\\", "/")))

    def _visit_operations(self, value: Any, *, envelope: dict[str, Any]) -> None:
        if isinstance(value, dict):
            item_type = str(value.get("type") or "").lower()
            identifier = value.get("id") or value.get("call_id")
            if item_type in _TOOL_TYPES:
                if identifier is not None:
                    key = f"{item_type}:{identifier}"
                    if key not in self._tool_ids:
                        self._tool_ids.add(key)
                        self.tool_calls += 1
                elif not str(envelope.get("type") or "").lower().endswith(".started"):
                    self.tool_calls += 1
            if "compact" in item_type:
                key = f"{item_type}:{identifier}" if identifier is not None else f"compact:{self.compactions}"
                if key not in self._compaction_ids:
                    self._compaction_ids.add(key)
                    self.compactions += 1
            for child in value.values():
                self._visit_operations(child, envelope=envelope)
        elif isinstance(value, list):
            for child in value:
                self._visit_operations(child, envelope=envelope)


def _reader(stream: IO[str], channel: str, output: queue.Queue[tuple[str, str | None]]) -> None:
    try:
        for line in iter(stream.readline, ""):
            output.put((channel, line))
    finally:
        output.put((channel, None))


def _terminate_process_tree(process: subprocess.Popen[str], *, force: bool = False) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
                timeout=5,
                creationflags=flags,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill() if force else process.terminate()
        except OSError:
            pass


def _consume_bound_process(
    process: subprocess.Popen[str],
    *,
    input_text: str,
    token: CancellationToken,
    timeout_seconds: int,
    file_limit: int,
    tool_call_limit: int,
) -> StreamedProcessResult:
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    try:
        process.stdin.write(input_text)
        process.stdin.close()
    except (BrokenPipeError, OSError):
        pass

    output: queue.Queue[tuple[str, str | None]] = queue.Queue()
    stdout_reader = threading.Thread(target=_reader, args=(process.stdout, "stdout", output), daemon=True)
    stderr_reader = threading.Thread(target=_reader, args=(process.stderr, "stderr", output), daemon=True)
    stdout_reader.start()
    stderr_reader.start()
    tracker = EventBudgetTracker()
    stderr_tail: deque[str] = deque()
    stderr_size = 0
    closed_channels: set[str] = set()
    started = time.monotonic()
    stop_started: float | None = None
    stop_reason: str | None = None

    while len(closed_channels) < 2 or process.poll() is None:
        now = time.monotonic()
        if stop_reason is None and token.cancelled:
            stop_reason = "cancelled"
        elif stop_reason is None and now - started > timeout_seconds:
            stop_reason = "timeout"
        if stop_reason is not None and stop_started is None:
            stop_started = now
            _terminate_process_tree(process)
        elif stop_started is not None and process.poll() is None and now - stop_started > 1:
            _terminate_process_tree(process, force=True)

        try:
            channel, line = output.get(timeout=0.05)
        except queue.Empty:
            if process.poll() is not None and not stdout_reader.is_alive() and not stderr_reader.is_alive():
                break
            continue
        if line is None:
            closed_channels.add(channel)
            continue
        if channel == "stdout":
            tracker.consume(line)
            if stop_reason is None and (
                tracker.unique_files_read > file_limit or tracker.tool_calls > tool_call_limit
            ):
                stop_reason = "budget_exceeded"
        else:
            stderr_tail.append(line)
            stderr_size += len(line)
            while stderr_size > _STDERR_LIMIT and stderr_tail:
                stderr_size -= len(stderr_tail.popleft())

    if process.poll() is None:
        _terminate_process_tree(process, force=True)
    try:
        returncode = process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process, force=True)
        try:
            returncode = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            returncode = process.poll() if process.poll() is not None else -9
    return StreamedProcessResult(
        returncode=returncode,
        stderr="".join(stderr_tail),
        usage=tracker.usage,
        usage_available=tracker.usage_available,
        tool_calls=tracker.tool_calls,
        unique_files_read=tracker.unique_files_read,
        compactions=tracker.compactions,
        stop_reason=stop_reason,
    )


def run_streaming_process(
    command: Sequence[str],
    *,
    input_text: str,
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: int,
    file_limit: int,
    tool_call_limit: int,
    cancel_token: CancellationToken | None = None,
) -> StreamedProcessResult:
    """Run Codex with bounded streaming metadata and no retained JSONL transcript."""

    token = cancel_token or CancellationToken()
    if token.cancelled:
        return StreamedProcessResult(
            returncode=-1,
            stderr="",
            usage={key: 0 for key in USAGE_KEYS},
            usage_available=False,
            tool_calls=0,
            unique_files_read=0,
            compactions=0,
            stop_reason="cancelled",
        )

    popen_options: dict[str, Any] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
        "cwd": cwd,
        "env": env,
    }
    if os.name == "nt":
        popen_options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_options["start_new_session"] = True
    process = subprocess.Popen(list(command), **popen_options)
    token.bind(process)
    try:
        return _consume_bound_process(
            process,
            input_text=input_text,
            token=token,
            timeout_seconds=timeout_seconds,
            file_limit=file_limit,
            tool_call_limit=tool_call_limit,
        )
    finally:
        if process.poll() is None:
            _terminate_process_tree(process, force=True)
        token.unbind(process)
