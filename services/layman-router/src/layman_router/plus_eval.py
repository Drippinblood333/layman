from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .classify import classify_task
from .config import load_config
from .models import RouteTier
from .routing import decide_route


DEFAULT_CASES_PATH = Path(__file__).with_name("plus_release_cases.jsonl")
EXTENDED_CASES_PATH = Path(__file__).with_name("plus_cases.jsonl")
SAFE_DEFAULT_CALL_LIMIT = 12
API_BILLING_ENV_VARS = {
    "OPENAI_API_KEY", "CODEX_API_KEY", "AZURE_OPENAI_API_KEY",
    "OPENAI_BASE_URL", "OPENAI_API_BASE", "AZURE_OPENAI_ENDPOINT",
    "CODEX_THREAD_ID", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "CODEX_PERMISSION_PROFILE", "K_CODEX",
}
DIRECT_ANSWER_PREFIX = (
    "This is an isolated quality evaluation. Answer the task directly without calling tools, "
    "reading files, or changing the computer. Be correct and concise.\n\nTASK:\n"
)
EVAL_PROTOCOL_VERSION = 2


@dataclass(frozen=True)
class PlusEvalArm:
    case_id: str
    category: str
    label: str
    model: str
    effort: str
    route_tier: str
    route_reason: list[str]
    prompt: str

    @property
    def key(self) -> str:
        return f"{self.case_id}:{self.label}"


def subscription_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in API_BILLING_ENV_VARS:
        environment.pop(name, None)
    return environment


def _windows_codex_candidates() -> list[str]:
    candidates: list[str] = []
    path_native = shutil.which("codex.exe")
    if path_native:
        candidates.append(path_native)

    appdata = os.getenv("APPDATA")
    if appdata:
        npm_root = Path(appdata) / "npm"
        candidates.extend(
            str(path.resolve())
            for path in sorted(
                npm_root.glob(
                    "node_modules/@openai/codex/node_modules/@openai/codex-win32-*/"
                    "vendor/*-pc-windows-msvc/bin/codex.exe"
                )
            )
            if path.is_file()
        )

    editor_roots = (Path.home() / ".vscode" / "extensions", Path.home() / ".cursor" / "extensions")
    editor_candidates = [
        path
        for root in editor_roots
        if root.is_dir()
        for path in root.glob("openai.chatgpt-*/bin/windows-*/codex.exe")
        if path.is_file()
    ]
    editor_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    candidates.extend(str(path.resolve()) for path in editor_candidates)

    for name in ("codex.cmd", "codex"):
        located = shutil.which(name)
        if located:
            candidates.append(located)
    if appdata:
        npm_wrapper = Path(appdata) / "npm" / "codex.cmd"
        if npm_wrapper.is_file():
            candidates.append(str(npm_wrapper.resolve()))
    return candidates


def _codex_candidates() -> list[str]:
    candidates = _windows_codex_candidates() if os.name == "nt" else [shutil.which("codex") or ""]
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = os.path.normcase(os.path.abspath(candidate))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _codex_starts(
    candidate: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> bool:
    try:
        result = runner(
            [candidate, "--version"], capture_output=True, text=True, timeout=10, check=False,
            env=subscription_environment(),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def find_codex(
    explicit: str | None = None,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            return str(candidate.resolve())
        located = shutil.which(explicit)
        if located:
            return located
        raise FileNotFoundError(f"Codex executable not found: {explicit}")
    candidates = _codex_candidates()
    for candidate in candidates:
        if _codex_starts(candidate, runner=runner):
            return candidate
    if candidates:
        attempted = ", ".join(candidates)
        raise FileNotFoundError(
            f"Codex CLI candidates were found but none could start. Tried: {attempted}. "
            "Repair Codex CLI or pass --codex-path."
        )
    raise FileNotFoundError("Codex CLI was not found. Install Codex CLI or pass --codex-path.")


def codex_login_status(codex_path: str, *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> dict[str, Any]:
    result = runner(
        [codex_path, "login", "status"], capture_output=True, text=True, timeout=15, check=False,
        env=subscription_environment(),
    )
    message = " ".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    lower = message.lower()
    return {
        "available": result.returncode == 0,
        "chatgpt_login": result.returncode == 0 and ("chatgpt" in lower or "chatgpt" in message),
        "status": message or f"Codex login status exited with {result.returncode}",
    }


def load_cases(path: str | Path | None = None) -> list[dict[str, Any]]:
    case_path = Path(path or DEFAULT_CASES_PATH).expanduser().resolve()
    cases = [json.loads(line) for line in case_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not cases:
        raise ValueError(f"No evaluation cases found: {case_path}")
    for case in cases:
        if not all(case.get(key) for key in ("id", "category", "input")):
            raise ValueError(f"Each case requires id, category, and input: {case_path}")
    return cases


def build_plan(cases: list[dict[str, Any]], *, config: Any | None = None) -> list[PlusEvalArm]:
    config = config or load_config()
    plan: list[PlusEvalArm] = []
    deep = config.tiers[RouteTier.DEEP]
    for case in cases:
        payload = case.get("request") or {"model": "auto", "input": case["input"]}
        features = classify_task(payload, config)
        decision = decide_route(features, config, payload.get("metadata"))
        plan.append(PlusEvalArm(
            case_id=case["id"], category=case["category"], label="auto",
            model=decision.selected_model, effort=decision.reasoning_effort,
            route_tier=decision.route_tier.value, route_reason=decision.route_reason,
            prompt=case["input"],
        ))
        if case.get("deep_baseline", True):
            plan.append(PlusEvalArm(
                case_id=case["id"], category=case["category"], label="always_deep",
                model=deep.model, effort=deep.reasoning_effort,
                route_tier=RouteTier.DEEP.value, route_reason=["always-deep comparison baseline"],
                prompt=case["input"],
            ))
    return plan


def experiment_fingerprint(
    cases: list[dict[str, Any]], plan: list[PlusEvalArm], *, codex_version: str
) -> str:
    payload = {
        "protocol_version": EVAL_PROTOCOL_VERSION,
        "cases": cases,
        "routes": [
            {
                "key": arm.key,
                "model": arm.model,
                "effort": arm.effort,
                "tier": arm.route_tier,
                "reason": arm.route_reason,
            }
            for arm in plan
        ],
        "prompt_contract": DIRECT_ANSWER_PREFIX,
        "codex_version": codex_version,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def completed_keys(output: Path, fingerprint: str) -> set[str]:
    if not output.exists():
        return set()
    keys: set[str] = set()
    for line in output.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if (
            item.get("status") == "completed"
            and item.get("key")
            and item.get("experiment_fingerprint") == fingerprint
        ):
            keys.add(str(item["key"]))
    return keys


def public_plan(
    plan: list[PlusEvalArm], done: set[str], *, fingerprint: str
) -> dict[str, Any]:
    pending = [arm for arm in plan if arm.key not in done]
    return {
        "mode": "dry-run",
        "billing": "ChatGPT subscription through Codex login; no OpenAI API key is used",
        "cases": len({arm.case_id for arm in plan}),
        "planned_calls": len(plan),
        "completed_calls": len(plan) - len(pending),
        "pending_calls": len(pending),
        "experiment_fingerprint": fingerprint,
        "privacy": "prompts are sent through stdin; prompt and answer text are not written to the result log",
        "routes": [
            {"key": arm.key, "category": arm.category, "model": arm.model, "effort": arm.effort, "tier": arm.route_tier}
            for arm in pending
        ],
    }


def _usage_from_events(stdout: str) -> dict[str, int]:
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    aliases = {
        "input_tokens": "input_tokens", "cached_input_tokens": "cached_input_tokens",
        "cached_tokens": "cached_input_tokens", "output_tokens": "output_tokens",
        "reasoning_tokens": "reasoning_tokens",
    }

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in aliases and isinstance(child, int):
                    usage[aliases[key]] = max(usage[aliases[key]], child)
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for line in stdout.splitlines():
        try:
            visit(json.loads(line))
        except json.JSONDecodeError:
            continue
    return usage


def event_metrics(stdout: str) -> dict[str, Any]:
    tool_calls = 0
    compactions = 0
    files: set[str] = set()
    path_pattern = re.compile(r"(?i)(?:[A-Z]:)?[\\/\w. -]+\.(?:py|js|ts|tsx|jsx|md|json|ya?ml|toml|sql|sh|ps1)")

    def visit(value: Any) -> None:
        nonlocal tool_calls, compactions
        if isinstance(value, dict):
            item_type = str(value.get("type") or "").lower()
            if item_type in {"command_execution", "mcp_tool_call", "file_read", "tool_call"}:
                tool_calls += 1
            if "compact" in item_type:
                compactions += 1
            for key, child in value.items():
                if key in {"command", "cmd", "path", "file"} and isinstance(child, str):
                    for match in path_pattern.findall(child):
                        files.add(match.strip(" '\""))
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for line in stdout.splitlines():
        try:
            visit(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"tool_calls": tool_calls, "unique_files_read": len(files), "compactions": compactions}


def _safe_error(stderr: str, returncode: int) -> str:
    lower = stderr.lower()
    if "rate limit" in lower or "usage limit" in lower or "quota" in lower:
        return "subscription_limit"
    if "model" in lower and ("not found" in lower or "unsupported" in lower):
        return "model_unavailable"
    if "login" in lower or "auth" in lower or "unauthorized" in lower:
        return "authentication"
    if "timed out" in lower or "timeout" in lower:
        return "timeout"
    return f"codex_exit_{returncode}"


def run_arm(
    arm: PlusEvalArm,
    *,
    codex_path: str,
    workspace: Path,
    store_outputs: bool = False,
    experiment_fingerprint_value: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="layman-plus-") as directory:
        last_message = Path(directory) / "last-message.txt"
        command = [
            codex_path, "exec", "--json", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never", "-C", str(workspace),
            "-m", arm.model, "-c", f'model_reasoning_effort="{arm.effort}"',
            "--output-last-message", str(last_message), "-",
        ]
        started = time.perf_counter()
        try:
            result = runner(
                command, input=DIRECT_ANSWER_PREFIX + arm.prompt, capture_output=True, text=True,
                timeout=300, check=False, env=subscription_environment(),
            )
            latency_ms = round((time.perf_counter() - started) * 1000)
        except subprocess.TimeoutExpired:
            return {
                "key": arm.key, "case_id": arm.case_id, "category": arm.category, "label": arm.label,
                "model": arm.model, "effort": arm.effort, "route_tier": arm.route_tier,
                "status": "failed", "error_category": "timeout", "latency_ms": 300_000,
            }
        answer = last_message.read_text(encoding="utf-8") if last_message.exists() else ""
        record: dict[str, Any] = {
            "key": arm.key, "case_id": arm.case_id, "category": arm.category, "label": arm.label,
            "model": arm.model, "effort": arm.effort, "route_tier": arm.route_tier,
            "route_reason": arm.route_reason, "status": "completed" if result.returncode == 0 else "failed",
            "latency_ms": latency_ms, "usage": _usage_from_events(result.stdout),
            "prompt_sha256": hashlib.sha256(arm.prompt.encode("utf-8")).hexdigest(),
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else None,
            "answer_chars": len(answer), "human_score": None,
            "experiment_fingerprint": experiment_fingerprint_value,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if result.returncode != 0:
            record["error_category"] = _safe_error(result.stderr, result.returncode)
        if store_outputs and answer:
            record["answer_text"] = answer
        return record


def run_plus_eval(
    *,
    cases_path: str | Path | None,
    output: Path,
    workspace: Path,
    codex_path: str | None,
    execute: bool,
    max_calls: int = SAFE_DEFAULT_CALL_LIMIT,
    allow_more_calls: bool = False,
    store_outputs: bool = False,
) -> dict[str, Any]:
    if max_calls < 1:
        raise ValueError("max_calls must be positive")
    if max_calls > SAFE_DEFAULT_CALL_LIMIT and not allow_more_calls:
        raise ValueError(f"max_calls above {SAFE_DEFAULT_CALL_LIMIT} requires --allow-more-calls")
    cases = load_cases(cases_path)
    plan = build_plan(cases)
    executable = find_codex(codex_path) if execute else None
    codex_version = "unresolved-dry-run"
    if executable is not None:
        version_result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=subscription_environment(),
        )
        if version_result.returncode != 0 or not version_result.stdout.strip():
            raise RuntimeError("Codex version could not be verified for this calibration")
        codex_version = version_result.stdout.strip()
    fingerprint = experiment_fingerprint(cases, plan, codex_version=codex_version)
    done = completed_keys(output, fingerprint)
    preview = public_plan(plan, done, fingerprint=fingerprint)
    if not execute:
        preview["resume_status"] = (
            "conservative preview; completed records are matched only after --run verifies the Codex version"
        )
        return preview
    assert executable is not None
    login = codex_login_status(executable)
    if not login["available"]:
        raise RuntimeError(login["status"])
    if not login["chatgpt_login"]:
        raise RuntimeError("Codex is not logged in with ChatGPT. Refusing to risk API-key billing.")
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = [arm for arm in plan if arm.key not in done][:max_calls]
    completed_now = 0
    failed = 0
    with output.open("a", encoding="utf-8") as stream:
        for arm in pending:
            record = run_arm(
                arm,
                codex_path=executable,
                workspace=workspace,
                store_outputs=store_outputs,
                experiment_fingerprint_value=fingerprint,
            )
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            if record["status"] == "completed":
                completed_now += 1
            else:
                failed += 1
                if record.get("error_category") in {"subscription_limit", "authentication", "model_unavailable"}:
                    break
    return {
        "mode": "run", "output": str(output.resolve()), "requested_call_cap": max_calls,
        "completed_now": completed_now, "failed_now": failed,
        "remaining_after_run": max(0, preview["pending_calls"] - completed_now - failed),
        "stores_output_text": store_outputs,
        "experiment_fingerprint": fingerprint,
        "codex_version": codex_version,
        "billing_note": "Uses ChatGPT subscription login. API-dollar values are not measured in this mode.",
    }
