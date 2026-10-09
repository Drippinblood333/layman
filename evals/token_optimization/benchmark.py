from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import random
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SERVICE_SRC = ROOT / "services" / "layman-router" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

# ruff: disable[E402] Local benchmark imports require the path bootstrap above.
from layman_router.config import load_config
from layman_router.plus_eval import (
    _safe_error,
    _usage_from_events,
    codex_login_status,
    event_metrics,
    find_codex,
    subscription_environment,
)
from layman_router.plus_run import (
    COMPACT_PROMPT,
    POLICIES,
    _execution_contract,
    _usage_available,
    run_plus_task,
)

from evals.token_optimization.cases import CASES, BenchmarkCase
from evals.token_optimization.fixture import (
    prepare_workspace,
    validate_workspace,
)

# ruff: enable[E402]

DEFAULT_OUTPUT = Path.home() / ".layman" / "token-benchmark.jsonl"
DEFAULT_WORK = ROOT / "build" / "token-benchmark-work"
BENCHMARK_SCHEMA_VERSION = 4


def _execution_prompt(case: BenchmarkCase) -> str:
    if case.read_only:
        return case.prompt
    return (
        case.prompt
        + "\n\n你已经获得执行授权：必须在本轮直接修改当前工作区允许范围内的文件并运行最小验证；"
        "不要只分析、输出建议/步骤/代码片段，也不要询问是否继续。"
    )


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _experiment_manifest(seed: int, selected: list[BenchmarkCase] | None = None) -> dict[str, Any]:
    config = load_config()
    cases = [asdict(case) for case in (selected if selected is not None else CASES)]
    policies = {tier.value: asdict(policy) for tier, policy in POLICIES.items()}
    components = {
        "randomization_seed": seed,
        "direct_baseline": "configured_balanced_medium",
        "max_model_attempts_per_arm": 1,
        "usage_protocol_sha256": hashlib.sha256(
            b"".join(
                (SERVICE_SRC / "layman_router" / name).read_bytes()
                for name in ("execution_control.py", "plus_eval.py", "plus_run.py")
            )
        ).hexdigest(),
        "cases_sha256": _stable_digest(cases),
        "routing_config_sha256": _stable_digest(config.model_dump(mode="json")),
        "execution_policies_sha256": _stable_digest(policies),
        "execution_contract_sha256": hashlib.sha256(
            inspect.getsource(_execution_contract).encode("utf-8")
        ).hexdigest(),
        "compact_prompt_sha256": hashlib.sha256(COMPACT_PROMPT.encode("utf-8")).hexdigest(),
        "benchmark_protocol_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
            + (Path(__file__).with_name("fixture.py")).read_bytes()
        ).hexdigest(),
    }
    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        **components,
        "experiment_digest": _stable_digest(
            {"schema_version": BENCHMARK_SCHEMA_VERSION, **components}
        ),
    }


def _completed_keys(output: Path, experiment_digest: str) -> set[str]:
    if not output.exists():
        return set()
    keys: set[str] = set()
    for line in output.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if (
                record.get("experiment_digest") == experiment_digest
                and record.get("execution_status") == "completed"
            ):
                keys.add(str(record["key"]))
    return keys


def _failure_counts(output: Path, experiment_digest: str) -> tuple[int, int]:
    if not output.exists():
        return 0, 0
    records = [
        record
        for line in output.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for record in [json.loads(line)]
        if record.get("experiment_digest") == experiment_digest
    ]
    failures = sum(
        record.get("execution_status") != "completed" or not record.get("validation", {}).get("passed", False)
        for record in records
    )
    return len(records), failures


def _remove_workspace(workspace: Path, work_root: Path) -> None:
    resolved = workspace.resolve()
    root = work_root.resolve()
    resolved.relative_to(root)
    if resolved == root:
        raise RuntimeError(f"Refusing to remove benchmark root: {root}")

    def remove_readonly(function: Any, path: str, _exc: Any) -> None:
        Path(path).chmod(stat.S_IWRITE)
        function(path)

    shutil.rmtree(resolved, onerror=remove_readonly)


def _execution_error(stdout: str, stderr: str, returncode: int) -> str:
    """Classify diagnostics in memory; never retain their potentially private text."""
    messages = [stderr]
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") not in {"error", "turn.failed"}:
            continue
        error = event.get("error", event)
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            messages.append(error["message"])
    for message in messages:
        category = _safe_error(message, returncode)
        if category != f"codex_exit_{returncode}":
            return category
    diagnostic = "\n".join(messages).lower()
    if any(marker in diagnostic for marker in ("error loading config", "invalid configuration", "failed to parse", "toml parse")):
        return "cli_configuration"
    if any(marker in diagnostic for marker in ("unexpected argument", "invalid value", "required arguments")):
        return "cli_arguments"
    return f"codex_exit_{returncode}"


def _startup_diagnostics(stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
    """Record lifecycle counters only, never event payloads or diagnostics text."""
    counts = dict.fromkeys(("thread.started", "turn.started", "turn.completed", "turn.failed", "error"), 0)
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("type"), str) and event["type"] in counts:
            counts[event["type"]] += 1
    return {"exit_code": returncode, "stderr_present": bool(stderr), "lifecycle_counts": counts}


def _direct_run(case: BenchmarkCase, workspace: Path, codex_path: str) -> dict[str, Any]:
    config = load_config()
    spec = config.tiers["balanced"]
    with tempfile.TemporaryDirectory(prefix="layman-direct-") as directory:
        last_message = Path(directory) / "last-message.txt"
        command = [
            codex_path, "exec", "--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "read-only" if case.read_only else "workspace-write", "--color", "never",
            "-C", str(workspace), "-m", spec.model, "-c", 'model_provider="openai"',
            "-c", 'model_reasoning_effort="medium"',
            "-c", 'approval_policy="never"',
            "-c", f'default_permissions={json.dumps(":read-only" if case.read_only else ":workspace")}',
            "--output-last-message", str(last_message), "-",
        ]
        started = time.perf_counter()
        environment = subscription_environment()
        environment["CODEX_PERMISSION_PROFILE"] = ":read-only" if case.read_only else ":workspace"
        try:
            result = subprocess.run(
                command, input=_execution_prompt(case), capture_output=True, text=True, timeout=1_800,
                encoding="utf-8", errors="replace", check=False, env=environment, cwd=workspace,
            )
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error_category": "timeout", "latency_ms": 1_800_000, "answer": ""}
        answer = last_message.read_text(encoding="utf-8") if last_message.exists() else ""
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "error_category": None if result.returncode == 0 else _execution_error(result.stdout, result.stderr, result.returncode),
            "route_tier": "direct",
            "model": spec.model,
            "effort": "medium",
            "risk": "high" if case.read_only else "benchmark",
            "sandbox": "read-only" if case.read_only else "workspace-write",
            "fallback_used": False,
            "usage": _usage_from_events(result.stdout),
            "usage_incomplete": not _usage_available(result.stdout),
            "startup_diagnostics": _startup_diagnostics(result.stdout, result.stderr, result.returncode),
            "latency_ms": round((time.perf_counter() - started) * 1_000),
            "answer": answer,
            **event_metrics(result.stdout),
        }


def _public_record(
    case: BenchmarkCase,
    arm: str,
    result: dict[str, Any],
    validation: dict[str, Any],
    *,
    experiment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    answer = result.pop("answer", "")
    usage = result.get("usage") or {}
    record = {
        "key": f"{case.id}:{arm}",
        "case_id": case.id,
        "category": case.category,
        "arm": arm,
        "execution_status": result.pop("status", "failed"),
        **result,
        "usage": usage,
        "total_tokens": int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
        "prompt_sha256": hashlib.sha256(_execution_prompt(case).encode("utf-8")).hexdigest(),
        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else None,
        "answer_chars": len(answer),
        "validation": validation,
        "stores_answer_text": False,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    if experiment is not None:
        record.update(experiment)
    return record


def _selected_cases(pilot: bool) -> list[BenchmarkCase]:
    if not pilot:
        return CASES
    seen: set[str] = set()
    selected: list[BenchmarkCase] = []
    for case in CASES:
        if case.category not in seen:
            selected.append(case)
            seen.add(case.category)
    return selected


def _ordered_arms(seed: int, selected: list[BenchmarkCase] | None = None) -> list[tuple[BenchmarkCase, str]]:
    randomizer = random.Random(seed)
    pairs: list[tuple[BenchmarkCase, str]] = []
    for case in (selected if selected is not None else CASES):
        arms = ["direct", "layman"]
        randomizer.shuffle(arms)
        pairs.extend((case, arm) for arm in arms)
    return pairs


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    if isinstance(args.max_calls, bool) or not isinstance(args.max_calls, int) or args.max_calls < 1:
        raise ValueError("max_calls must be a positive integer")
    total_call_cap = getattr(args, "total_call_cap", None)
    if total_call_cap is not None and (isinstance(total_call_cap, bool) or not isinstance(total_call_cap, int) or total_call_cap < 1):
        raise ValueError("total_call_cap must be a positive integer")
    selected = _selected_cases(getattr(args, "pilot", False))
    experiment = _experiment_manifest(args.seed, selected)
    experiment_digest = experiment["experiment_digest"]
    plan = _ordered_arms(args.seed, selected)
    done = _completed_keys(args.output, experiment_digest)
    pending = [(case, arm) for case, arm in plan if f"{case.id}:{arm}" not in done]
    if not args.run:
        return {
            "mode": "dry-run", "cases": len(selected), "planned_calls": len(plan),
            "completed_calls": len(plan) - len(pending), "pending_calls": len(pending),
            "experiment_digest": experiment_digest,
            "next": [{"key": f"{case.id}:{arm}", "category": case.category} for case, arm in pending[: args.max_calls]],
            "privacy": "Synthetic prompts only; result JSONL excludes answer text and generated code.",
        }
    if args.max_calls > 20 and not args.allow_more_calls:
        raise ValueError("More than 20 calls per batch requires --allow-more-calls")
    executable = find_codex(args.codex_path)
    login = codex_login_status(executable)
    if not login["available"] or not login["chatgpt_login"]:
        raise RuntimeError("Benchmark requires ChatGPT subscription login; API billing is disabled")
    version_result = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=subscription_environment(),
    )
    codex_version = version_result.stdout.strip() if version_result.returncode == 0 else "unavailable"
    experiment = {
        **{key: value for key, value in experiment.items() if key != "experiment_digest"},
        "codex_version": codex_version,
    }
    experiment["experiment_digest"] = _stable_digest(experiment)
    experiment_digest = experiment["experiment_digest"]
    done = _completed_keys(args.output, experiment_digest)
    pending = [(case, arm) for case, arm in plan if f"{case.id}:{arm}" not in done]
    journal = args.output.with_name(args.output.name + ".attempts.jsonl")
    reservations = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()] if journal.exists() else []
    public_keys = {
        record["key"] for line in args.output.read_text(encoding="utf-8").splitlines() if line.strip()
        for record in [json.loads(line)] if record.get("experiment_digest") == experiment_digest
    } if args.output.exists() else set()
    relevant = [record for record in reservations if record.get("experiment_digest") == experiment_digest]
    if any(record["key"] not in public_keys for record in relevant):
        raise RuntimeError("An interrupted reserved attempt needs review; refusing automatic replay")
    remaining_budget = max(0, total_call_cap - len(reservations)) if total_call_cap is not None else args.max_calls
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.work_root.mkdir(parents=True, exist_ok=True)
    baseline_total, baseline_failed = _failure_counts(args.output, experiment_digest)
    completed_now = 0
    failed_now = 0
    with args.output.open("a", encoding="utf-8") as stream:
        for case, arm in pending[: min(args.max_calls, remaining_budget)]:
            workspace = args.work_root / f"{case.id}-{arm}-{uuid.uuid4().hex[:8]}"
            prepare_workspace(case, workspace)
            # Reserve one entire Codex execution before launch. A failed or
            # interrupted execution still consumes the authorization ceiling.
            with journal.open("a", encoding="utf-8") as budget_stream:
                budget_stream.write(json.dumps({
                    "key": f"{case.id}:{arm}", "experiment_digest": experiment_digest,
                    "reserved_at": datetime.now(UTC).isoformat(),
                }) + "\n")
                budget_stream.flush()
                os.fsync(budget_stream.fileno())
            if arm == "direct":
                result = _direct_run(case, workspace, executable)
            else:
                result = run_plus_task(_execution_prompt(case), cwd=workspace, codex_path=executable, max_model_attempts=1)
            validation = validate_workspace(case, workspace, result.get("answer", ""))
            record = _public_record(case, arm, result, validation, experiment=experiment)
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            _remove_workspace(workspace, args.work_root)
            call_failed = record["execution_status"] != "completed" or not record["validation"]["passed"]
            if not call_failed:
                completed_now += 1
            else:
                failed_now += 1
            processed_now = completed_now + failed_now
            cumulative_total = baseline_total + processed_now
            cumulative_failed = baseline_failed + failed_now
            if (getattr(args, "pilot", False) and record["execution_status"] != "completed") or record.get("error_category") in {"subscription_limit", "authentication", "model_unavailable"} or (
                cumulative_total >= 10 and cumulative_failed / cumulative_total > 0.10
            ):
                break
    return {
        "mode": "run", "output": str(args.output.resolve()), "completed_now": completed_now,
        "failed_now": failed_now, "remaining": max(0, len(pending) - completed_now - failed_now),
        "experiment_digest": experiment_digest,
        "reserved_attempts_total": len(reservations) + completed_now + failed_now,
        "total_call_cap": total_call_cap,
    }


def analyze(output: Path, seed: int = 20260716) -> dict[str, Any]:
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest_digest = records[-1].get("experiment_digest") if records else None
    records = [
        record for record in records
        if record.get("experiment_digest") == latest_digest
    ]
    pairs: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        pairs.setdefault(record["case_id"], {})[record["arm"]] = record
    complete = [arms for arms in pairs.values() if {"direct", "layman"}.issubset(arms)]
    eligible = [arms for arms in complete if all(
        arm.get("execution_status") == "completed" and not arm.get("usage_incomplete", False)
        and not arm.get("fallback_used", False) and arm.get("total_tokens", 0) > 0
        for arm in arms.values()
    )]
    reductions = [
        (arms["direct"]["total_tokens"] - arms["layman"]["total_tokens"]) / arms["direct"]["total_tokens"]
        for arms in eligible
    ]
    output_reductions = [
        (arms["direct"]["usage"].get("output_tokens", 0) - arms["layman"]["usage"].get("output_tokens", 0))
        / arms["direct"]["usage"].get("output_tokens", 1)
        for arms in eligible if arms["direct"]["usage"].get("output_tokens", 0) > 0
    ]
    bootstrap: list[float] = []
    if reductions:
        randomizer = random.Random(seed)
        for _ in range(10_000):
            sample = [randomizer.choice(reductions) for _ in reductions]
            bootstrap.append(statistics.median(sample))
        bootstrap.sort()
    direct_success = sum(arms["direct"]["validation"]["passed"] for arms in complete)
    layman_success = sum(arms["layman"]["validation"]["passed"] for arms in complete)
    high_risk_ok = all(
        arms["layman"].get("route_tier") == "deep" and arms["layman"]["validation"]["passed"]
        for case_id, arms in pairs.items() if case_id.startswith("risk-") and {"direct", "layman"}.issubset(arms)
    )
    median_reduction = statistics.median(reductions) if reductions else None
    output_reduction = statistics.median(output_reductions) if output_reductions else None
    ci_low = bootstrap[int(len(bootstrap) * 0.025)] if bootstrap else None
    direct_files = statistics.median(arms["direct"].get("unique_files_read", 0) for arms in complete) if complete else None
    layman_files = statistics.median(arms["layman"].get("unique_files_read", 0) for arms in complete) if complete else None
    gates = {
        "all_30_pairs_complete": len(complete) == 30,
        "all_30_pairs_usage_eligible": len(eligible) == 30,
        "trusted_usage_protocol": bool(complete) and all(
            record.get("schema_version") == BENCHMARK_SCHEMA_VERSION
            and bool(record.get("usage_protocol_sha256"))
            for arms in complete for record in arms.values()
        ),
        "median_total_token_reduction_at_least_15_percent": median_reduction is not None and median_reduction >= 0.15,
        "bootstrap_95_percent_lower_bound_above_zero": ci_low is not None and ci_low > 0,
        "quality_not_lower": layman_success >= direct_success,
        "layman_success_at_least_90_percent": layman_success >= 27,
        "high_risk_safe": high_risk_ok,
        "median_output_reduction_at_least_20_percent": output_reduction is not None and output_reduction >= 0.20,
        "median_files_read_not_higher": layman_files is not None and direct_files is not None and layman_files <= direct_files,
    }
    return {
        "experiment_digest": latest_digest,
        "pairs": len(complete), "median_total_token_reduction": median_reduction,
        "usage_eligible_pairs": len(eligible),
        "bootstrap_95_percent_ci": [ci_low, bootstrap[int(len(bootstrap) * 0.975)] if bootstrap else None],
        "median_output_token_reduction": output_reduction,
        "direct_success": direct_success, "layman_success": layman_success,
        "median_files_read": {"direct": direct_files, "layman": layman_files},
        "gates": gates, "claim_token_savings": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--codex-path")
    parser.add_argument("--max-calls", type=int, default=20)
    parser.add_argument("--allow-more-calls", action="store_true")
    parser.add_argument("--pilot", action="store_true", help="Preselect the first task in each of the six categories")
    parser.add_argument("--total-call-cap", type=int, help="Persistent execution-attempt cap, including failures and across restarts")
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if args.analyze:
        print(json.dumps(analyze(args.output, args.seed), indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(run_benchmark(args), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
