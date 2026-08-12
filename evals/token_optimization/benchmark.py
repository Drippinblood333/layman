from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SERVICE_SRC = ROOT / "services" / "layman-router" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from evals.token_optimization.cases import CASES, BenchmarkCase  # noqa: E402
from evals.token_optimization.fixture import prepare_workspace, validate_workspace  # noqa: E402
from layman_router.config import load_config  # noqa: E402
from layman_router.plus_eval import (  # noqa: E402
    _safe_error,
    _usage_from_events,
    codex_login_status,
    event_metrics,
    find_codex,
    subscription_environment,
)
from layman_router.plus_run import run_plus_task  # noqa: E402


DEFAULT_OUTPUT = Path.home() / ".layman" / "token-benchmark.jsonl"
DEFAULT_WORK = ROOT / "build" / "token-benchmark-work"


def _execution_prompt(case: BenchmarkCase) -> str:
    if case.read_only:
        return case.prompt
    return (
        case.prompt
        + "\n\n你已经获得执行授权：必须在本轮直接修改当前工作区允许范围内的文件并运行最小验证；"
        "不要只分析、输出建议/步骤/代码片段，也不要询问是否继续。"
    )


def _completed_keys(output: Path) -> set[str]:
    if not output.exists():
        return set()
    keys: set[str] = set()
    for line in output.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if record.get("execution_status") == "completed":
                keys.add(str(record["key"]))
    return keys


def _failure_counts(output: Path) -> tuple[int, int]:
    if not output.exists():
        return 0, 0
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
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


def _direct_run(case: BenchmarkCase, workspace: Path, codex_path: str) -> dict[str, Any]:
    config = load_config()
    spec = config.tiers["deep"]
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
                check=False, env=environment, cwd=workspace,
            )
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error_category": "timeout", "latency_ms": 1_800_000, "answer": ""}
        answer = last_message.read_text(encoding="utf-8") if last_message.exists() else ""
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "error_category": None if result.returncode == 0 else _safe_error(result.stderr, result.returncode),
            "route_tier": "direct",
            "model": spec.model,
            "effort": "medium",
            "risk": "high" if case.read_only else "benchmark",
            "sandbox": "read-only" if case.read_only else "workspace-write",
            "fallback_used": False,
            "usage": _usage_from_events(result.stdout),
            "latency_ms": round((time.perf_counter() - started) * 1_000),
            "answer": answer,
            **event_metrics(result.stdout),
        }


def _public_record(case: BenchmarkCase, arm: str, result: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    answer = result.pop("answer", "")
    usage = result.get("usage") or {}
    return {
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
    }


def _ordered_arms(seed: int) -> list[tuple[BenchmarkCase, str]]:
    randomizer = random.Random(seed)
    pairs: list[tuple[BenchmarkCase, str]] = []
    for case in CASES:
        arms = ["direct", "layman"]
        randomizer.shuffle(arms)
        pairs.extend((case, arm) for arm in arms)
    return pairs


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    plan = _ordered_arms(args.seed)
    done = _completed_keys(args.output)
    pending = [(case, arm) for case, arm in plan if f"{case.id}:{arm}" not in done]
    if not args.run:
        return {
            "mode": "dry-run", "cases": len(CASES), "planned_calls": len(plan),
            "completed_calls": len(plan) - len(pending), "pending_calls": len(pending),
            "next": [{"key": f"{case.id}:{arm}", "category": case.category} for case, arm in pending[: args.max_calls]],
            "privacy": "Synthetic prompts only; result JSONL excludes answer text and generated code.",
        }
    if args.max_calls > 20 and not args.allow_more_calls:
        raise ValueError("More than 20 calls per batch requires --allow-more-calls")
    executable = find_codex(args.codex_path)
    login = codex_login_status(executable)
    if not login["available"] or not login["chatgpt_login"]:
        raise RuntimeError("Benchmark requires ChatGPT subscription login; API billing is disabled")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.work_root.mkdir(parents=True, exist_ok=True)
    baseline_total, baseline_failed = _failure_counts(args.output)
    completed_now = 0
    failed_now = 0
    with args.output.open("a", encoding="utf-8") as stream:
        for case, arm in pending[: args.max_calls]:
            workspace = args.work_root / f"{case.id}-{arm}-{uuid.uuid4().hex[:8]}"
            prepare_workspace(case, workspace)
            if arm == "direct":
                result = _direct_run(case, workspace, executable)
            else:
                result = run_plus_task(_execution_prompt(case), cwd=workspace, codex_path=executable)
            validation = validate_workspace(case, workspace, result.get("answer", ""))
            record = _public_record(case, arm, result, validation)
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            _remove_workspace(workspace, args.work_root)
            call_failed = record["execution_status"] != "completed" or not record["validation"]["passed"]
            if not call_failed:
                completed_now += 1
            else:
                failed_now += 1
            processed_now = completed_now + failed_now
            cumulative_total = baseline_total + processed_now
            cumulative_failed = baseline_failed + failed_now
            if record.get("error_category") in {"subscription_limit", "authentication"} or (
                cumulative_total >= 10 and cumulative_failed / cumulative_total > 0.10
            ):
                break
    return {
        "mode": "run", "output": str(args.output.resolve()), "completed_now": completed_now,
        "failed_now": failed_now, "remaining": max(0, len(pending) - completed_now - failed_now),
    }


def analyze(output: Path, seed: int = 20260716) -> dict[str, Any]:
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
    pairs: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        pairs.setdefault(record["case_id"], {})[record["arm"]] = record
    complete = [arms for arms in pairs.values() if {"direct", "layman"}.issubset(arms)]
    reductions = [
        (arms["direct"]["total_tokens"] - arms["layman"]["total_tokens"]) / arms["direct"]["total_tokens"]
        for arms in complete if arms["direct"]["total_tokens"] > 0
    ]
    output_reductions = [
        (arms["direct"]["usage"].get("output_tokens", 0) - arms["layman"]["usage"].get("output_tokens", 0))
        / arms["direct"]["usage"].get("output_tokens", 1)
        for arms in complete if arms["direct"]["usage"].get("output_tokens", 0) > 0
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
        "median_total_token_reduction_at_least_15_percent": median_reduction is not None and median_reduction >= 0.15,
        "bootstrap_95_percent_lower_bound_above_zero": ci_low is not None and ci_low > 0,
        "quality_not_lower": layman_success >= direct_success,
        "layman_success_at_least_90_percent": layman_success >= 27,
        "high_risk_safe": high_risk_ok,
        "median_output_reduction_at_least_20_percent": output_reduction is not None and output_reduction >= 0.20,
        "median_files_read_not_higher": layman_files is not None and direct_files is not None and layman_files <= direct_files,
    }
    return {
        "pairs": len(complete), "median_total_token_reduction": median_reduction,
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
