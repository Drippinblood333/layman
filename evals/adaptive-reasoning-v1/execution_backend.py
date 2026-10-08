from __future__ import annotations

import abc
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence


API_BILLING_ENV_VARS = {
    "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID",
}

EXEC_CONTRACT_VERSION = "codex-cli-exec-contract-v1"
EXEC_REQUIRED_FLAGS = (
    "--json", "--ephemeral", "--ignore-user-config", "--ignore-rules",
    "--skip-git-repo-check", "--sandbox", "--output-last-message",
)


@dataclass(frozen=True)
class LauncherCandidate:
    path: str
    kind: str
    source: str
    directly_spawnable: bool


@dataclass(frozen=True)
class ExecutableIdentity:
    codex_cli_version: str
    codex_executable_sha256: str
    codex_distribution_source: str
    vscode_extension_version: str | None

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PreflightResult:
    passed: bool
    model_calls_started: int = 0
    selected: LauncherCandidate | None = None
    version: str | None = None
    cwd: str | None = None
    stdout_capture_ok: bool = False
    stderr_capture_ok: bool = False
    timeout_cancel_ok: bool = False
    login_ok: bool = False
    model_supported: bool = False
    effort_supported: bool = False
    executable_identity: ExecutableIdentity | None = None
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["selected"] = asdict(self.selected) if self.selected else None
        value["executable_identity"] = (
            self.executable_identity.public_dict() if self.executable_identity else None
        )
        return value


@dataclass(frozen=True)
class CommandContract:
    executable: str
    args: tuple[str, ...]
    cwd: str
    prompt_transport: str = "stdin"
    stdin_policy: str = "pipe_prompt_then_close"
    shell: bool = False

    @property
    def command(self) -> list[str]:
        return [self.executable, *self.args]

    def public_dict(self) -> dict[str, Any]:
        return {
            "executable": self.executable,
            "args": list(self.args),
            "cwd": self.cwd,
            "prompt_transport": self.prompt_transport,
            "stdin_policy": self.stdin_policy,
            "shell": self.shell,
            "prompt_in_argv": False,
        }


@dataclass
class ExecContractPreflightResult:
    passed: bool
    model_calls_started: int = 0
    contract_sha256: str | None = None
    command: dict[str, Any] | None = None
    fixture_workspace: str | None = None
    workspace_contains_git: bool = False
    git_inside_work_tree: bool | None = None
    git_toplevel: str | None = None
    controlled_workspace: bool = False
    cli_flag_support: dict[str, bool] = field(default_factory=dict)
    exact_command_parse_ok: bool = False
    user_config_isolated: bool = False
    auth_uses_codex_home: bool = False
    output_parent_exists: bool = False
    executable_identity: dict[str, Any] | None = None
    agents_files_found: list[str] = field(default_factory=list)
    project_codex_configs_found: list[str] = field(default_factory=list)
    repo_instruction_contamination: bool = False
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CodexExecutionRequest:
    workspace: Path
    prompt: str
    model: str
    reasoning_effort: str
    max_output_tokens: int
    timeout_seconds: int
    read_only: bool
    output_path: Path


@dataclass
class BackendExecutionResult:
    returncode: int
    stop_reason: str | None
    infrastructure_error: str | None
    diagnostic: str | None
    usage: dict[str, int]
    usage_available: bool
    latency_ms: float
    tool_calls: int
    unique_files_read: int
    event_types: list[str]
    effective_model: str | None
    effective_reasoning_effort: str | None
    command_executable: str
    command_args: list[str]
    cwd: str
    command_contract_sha256: str
    stdout_sha256: str
    stdout_chars: int
    stderr_sha256: str
    stderr_chars: int
    non_json_stdout_lines: int
    executable_identity: dict[str, Any]
    process_spawned: bool
    codex_process_started: bool
    turn_started_seen: bool
    turn_completed_seen: bool
    usage_seen: bool
    candidate_seen: bool
    output_file_seen: bool
    failure_category: str | None


class ExecutionBackend(abc.ABC):
    @abc.abstractmethod
    def resolve(self, explicit: str | None = None) -> list[LauncherCandidate]: ...

    @abc.abstractmethod
    def preflight(self, *, cwd: Path, model: str, reasoning_effort: str, explicit: str | None = None) -> PreflightResult: ...

    @abc.abstractmethod
    def preflight_exec_contract(
        self,
        request: CodexExecutionRequest,
        launcher: LauncherCandidate,
        *,
        controlled_work_root: Path,
    ) -> ExecContractPreflightResult: ...

    @abc.abstractmethod
    def execute(self, request: CodexExecutionRequest, launcher: LauncherCandidate) -> BackendExecutionResult: ...

    @abc.abstractmethod
    def classify_infrastructure_error(self, *, returncode: int, stop_reason: str | None, stderr: str) -> str | None: ...


class CodexCliBackend(ExecutionBackend):
    """Direct native Codex CLI backend. Windows shell shims are diagnostic-only."""

    def __init__(self) -> None:
        self._selected: LauncherCandidate | None = None
        self._approved_launcher_path: str | None = None
        self._controlled_work_root: Path | None = None
        self._approved_model_efforts: set[tuple[str, str]] = set()
        self._approved_identity: ExecutableIdentity | None = None

    @classmethod
    def contract_semantics(cls) -> dict[str, Any]:
        """Stable execution semantics included in the experiment fingerprint."""
        return {
            "version": EXEC_CONTRACT_VERSION,
            "backend": "codex-cli-native",
            "shell": False,
            "prompt_transport": "stdin",
            "stdin_policy": "pipe_prompt_then_close",
            "working_directory_flag": "-C/--cd",
            "process_cwd_matches_fixture": True,
            "json_output": "jsonl_stdout",
            "final_output": "--output-last-message",
            "user_config": "--ignore-user-config",
            "authentication": "CODEX_HOME auth retained",
            "git_repo_check": "--skip-git-repo-check only for controlled benchmark fixtures",
            "sandbox": "read-only for high-risk envelope, otherwise workspace-write",
            "required_flags": list(EXEC_REQUIRED_FLAGS),
            "model_override": "-m <model>",
            "effort_override": '-c model_reasoning_effort="<effort>"',
            "provider_override": '-c model_provider="openai"',
            "output_cap_override": "-c model_max_output_tokens=<integer>",
        }

    @classmethod
    def contract_semantics_sha256(cls) -> str:
        payload = json.dumps(cls.contract_semantics(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _environment() -> dict[str, str]:
        env = os.environ.copy()
        for name in API_BILLING_ENV_VARS:
            env.pop(name, None)
        return env

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _distribution_metadata(path: Path) -> tuple[str, str | None]:
        for parent in path.resolve().parents:
            if not parent.name.lower().startswith("openai.chatgpt-"):
                continue
            package_json = parent / "package.json"
            version = None
            if package_json.is_file():
                try:
                    raw = json.loads(package_json.read_text(encoding="utf-8"))
                    if isinstance(raw.get("version"), str):
                        version = raw["version"]
                except (OSError, json.JSONDecodeError):
                    version = None
            source = "vscode-extension-native" if parent.parent.parent.name.lower() == ".vscode" else "editor-extension-native"
            return source, version
        return "native-executable", None

    def _executable_identity(
        self,
        launcher: LauncherCandidate,
        *,
        cwd: Path,
        env: dict[str, str],
    ) -> ExecutableIdentity:
        executable = Path(launcher.path).resolve()
        version = self._capture([str(executable), "--version"], cwd=cwd, timeout=10, env=env)
        if version.returncode != 0 or not version.stdout.strip():
            raise RuntimeError("unable to read Codex CLI version for executable identity")
        source, extension_version = self._distribution_metadata(executable)
        return ExecutableIdentity(
            codex_cli_version=version.stdout.strip(),
            codex_executable_sha256=self._file_sha256(executable),
            codex_distribution_source=source,
            vscode_extension_version=extension_version,
        )

    @staticmethod
    def _launcher_kind(path: Path) -> tuple[str, bool]:
        suffix = path.suffix.lower()
        if suffix in {".cmd", ".bat"}:
            return "windows-command-shim", False
        if suffix == ".ps1":
            return "powershell-shim", False
        try:
            magic = path.read_bytes()[:2]
        except OSError:
            return "unreadable", False
        if magic == b"MZ":
            return ("native-exe" if suffix == ".exe" else "extensionless-native-pe"), True
        if suffix == ".exe":
            return "invalid-exe", False
        return "text-or-script-shim", False

    @staticmethod
    def _candidate(path: Path, source: str) -> LauncherCandidate:
        resolved = path.expanduser().resolve()
        kind, spawnable = CodexCliBackend._launcher_kind(resolved)
        return LauncherCandidate(str(resolved), kind, source, spawnable)

    def resolve(self, explicit: str | None = None) -> list[LauncherCandidate]:
        paths: list[tuple[Path, str]] = []
        if explicit:
            candidate = Path(explicit).expanduser()
            if not candidate.exists():
                located = shutil.which(explicit)
                if not located:
                    raise FileNotFoundError(f"Codex launcher not found: {explicit}")
                candidate = Path(located)
            paths.append((candidate, "explicit"))
        elif os.name == "nt":
            for root_name in (".vscode", ".cursor"):
                root = Path.home() / root_name / "extensions"
                if root.is_dir():
                    found = sorted(
                        root.glob("openai.chatgpt-*/bin/windows-*/codex.exe"),
                        key=lambda item: item.stat().st_mtime,
                        reverse=True,
                    )
                    paths.extend((item, f"{root_name}-extension-native") for item in found)
            appdata = os.getenv("APPDATA")
            if appdata:
                npm_root = Path(appdata) / "npm"
                paths.extend(
                    (item, "npm-optional-native")
                    for item in sorted(npm_root.glob(
                        "node_modules/@openai/codex/node_modules/@openai/codex-win32-*/"
                        "vendor/*-pc-windows-msvc/bin/codex.exe"
                    ))
                )
            for name in ("codex.exe", "codex.cmd", "codex.ps1", "codex"):
                located = shutil.which(name)
                if located:
                    paths.append((Path(located), f"path-{name}"))
            if appdata:
                for name in ("codex.cmd", "codex.ps1", "codex"):
                    item = Path(appdata) / "npm" / name
                    if item.is_file():
                        paths.append((item, "npm-shim"))
        else:
            located = shutil.which("codex")
            if located:
                paths.append((Path(located), "path"))
        candidates: list[LauncherCandidate] = []
        seen: set[str] = set()
        for path, source in paths:
            try:
                candidate = self._candidate(path, source)
            except OSError:
                continue
            key = os.path.normcase(candidate.path)
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
        if not candidates:
            raise FileNotFoundError("No Codex launcher candidates found")
        return candidates

    @staticmethod
    def _capture(command: Sequence[str], *, cwd: Path, timeout: float, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command), cwd=str(cwd), env=env, capture_output=True, text=True,
            timeout=timeout, check=False, shell=False,
        )

    @staticmethod
    def _safe_stderr(stderr: str) -> str:
        lowered = stderr.lower()
        for marker in ("spawn eftype", "not a valid application", "access is denied", "timed out", "timeout"):
            if marker in lowered:
                return marker
        return "nonzero exit without retained stderr" if stderr else ""

    @staticmethod
    def _execution_diagnostic(stderr: str) -> str | None:
        if not stderr.strip():
            return None
        value = " ".join(stderr.split())
        value = re.sub(r"(?i)bearer\s+\S+", "Bearer <redacted>", value)
        value = re.sub(r"(?i)\b(?:sk|sess|token)-[A-Za-z0-9._-]+", "<redacted-secret>", value)
        return value[:500]

    @staticmethod
    def _cancel_probe(executable: str, cwd: Path, env: dict[str, str]) -> bool:
        process = subprocess.Popen(
            [executable, "mcp-server"], cwd=str(cwd), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, shell=False,
        )
        try:
            time.sleep(0.15)
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=5)
            return process.poll() is not None
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
            return process.poll() is not None

    def preflight(self, *, cwd: Path, model: str, reasoning_effort: str, explicit: str | None = None) -> PreflightResult:
        resolved_cwd = cwd.resolve()
        if not resolved_cwd.is_dir():
            return PreflightResult(False, cwd=str(resolved_cwd), diagnostics=[{"stage": "cwd", "error": "not-a-directory"}])
        result = PreflightResult(False, cwd=str(resolved_cwd))
        env = self._environment()
        for candidate in self.resolve(explicit):
            diagnostic: dict[str, Any] = {
                "path": candidate.path, "kind": candidate.kind, "source": candidate.source,
                "directly_spawnable": candidate.directly_spawnable,
            }
            if not candidate.directly_spawnable:
                diagnostic["status"] = "rejected-shell-or-script-launcher"
                result.diagnostics.append(diagnostic)
                continue
            try:
                version = self._capture([candidate.path, "--version"], cwd=resolved_cwd, timeout=10, env=env)
            except (OSError, subprocess.SubprocessError) as exc:
                diagnostic.update(status="version-spawn-failed", error=type(exc).__name__)
                result.diagnostics.append(diagnostic)
                continue
            if version.returncode != 0:
                diagnostic.update(status="version-failed", error=self._safe_stderr(version.stderr))
                result.diagnostics.append(diagnostic)
                continue
            invalid = self._capture([candidate.path, "--stage-a0-invalid-option"], cwd=resolved_cwd, timeout=10, env=env)
            login = self._capture([candidate.path, "login", "status"], cwd=resolved_cwd, timeout=15, env=env)
            doctor = self._capture([candidate.path, "doctor", "--json"], cwd=resolved_cwd, timeout=30, env=env)
            catalog = self._capture([candidate.path, "debug", "models", "--bundled"], cwd=resolved_cwd, timeout=20, env=env)
            try:
                doctor_data = json.loads(doctor.stdout)
                observed_cwd = doctor_data["checks"]["config.load"]["details"]["cwd"]
            except (json.JSONDecodeError, KeyError, TypeError):
                observed_cwd = None
            try:
                models = json.loads(catalog.stdout)["models"]
                selected_model = next(item for item in models if item.get("slug") == model)
                supported_efforts = {item.get("effort") for item in selected_model.get("supported_reasoning_levels", [])}
            except (json.JSONDecodeError, KeyError, TypeError, StopIteration):
                selected_model, supported_efforts = None, set()
            try:
                cancel_ok = self._cancel_probe(candidate.path, resolved_cwd, env)
            except (OSError, subprocess.SubprocessError):
                cancel_ok = False
            cwd_ok = observed_cwd is not None and Path(observed_cwd).resolve() == resolved_cwd
            stderr_capture_ok = invalid.returncode != 0 and bool(invalid.stderr.strip())
            passed = all((login.returncode == 0, doctor.returncode == 0, catalog.returncode == 0, cwd_ok, selected_model is not None, reasoning_effort in supported_efforts, cancel_ok, stderr_capture_ok))
            diagnostic.update(
                status="passed" if passed else "preflight-failed",
                version_returncode=version.returncode,
                login_returncode=login.returncode,
                doctor_returncode=doctor.returncode,
                catalog_returncode=catalog.returncode,
                cwd_matches=cwd_ok,
                model_supported=selected_model is not None,
                effort_supported=reasoning_effort in supported_efforts,
                timeout_cancel_ok=cancel_ok,
                stderr_capture_ok=stderr_capture_ok,
            )
            result.diagnostics.append(diagnostic)
            if passed:
                source, extension_version = self._distribution_metadata(Path(candidate.path))
                self._selected = candidate
                result.passed = True
                result.selected = candidate
                result.version = version.stdout.strip()
                result.stdout_capture_ok = bool(version.stdout.strip())
                result.stderr_capture_ok = stderr_capture_ok
                result.timeout_cancel_ok = cancel_ok
                result.login_ok = True
                result.model_supported = True
                result.effort_supported = True
                result.executable_identity = ExecutableIdentity(
                    codex_cli_version=version.stdout.strip(),
                    codex_executable_sha256=self._file_sha256(Path(candidate.path)),
                    codex_distribution_source=source,
                    vscode_extension_version=extension_version,
                )
                return result
        return result

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
            return path.resolve() != root.resolve()
        except ValueError:
            return False

    @staticmethod
    def _argument_value(args: Sequence[str], flag: str) -> str | None:
        try:
            return str(args[args.index(flag) + 1])
        except (ValueError, IndexError):
            return None

    def build_command_contract(
        self,
        request: CodexExecutionRequest,
        launcher: LauncherCandidate,
    ) -> CommandContract:
        sandbox = "read-only" if request.read_only else "workspace-write"
        args = (
            "--ask-for-approval", "never", "exec", "--json", "--ephemeral",
            "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
            "--sandbox", sandbox, "--color", "never", "-C", str(request.workspace.resolve()),
            "-m", request.model, "-c", 'model_provider="openai"',
            "-c", f'model_reasoning_effort="{request.reasoning_effort}"',
            "-c", f"model_max_output_tokens={request.max_output_tokens}",
            "--output-last-message", str(request.output_path.resolve()), "-",
        )
        return CommandContract(
            executable=str(Path(launcher.path).resolve()),
            args=args,
            cwd=str(request.workspace.resolve()),
        )

    def _validate_contract_static(
        self,
        contract: CommandContract,
        request: CodexExecutionRequest,
        launcher: LauncherCandidate,
        controlled_work_root: Path,
    ) -> list[str]:
        errors: list[str] = []
        args = list(contract.args)
        workspace = request.workspace.resolve()
        executable = Path(contract.executable)
        if not launcher.directly_spawnable or not executable.is_file():
            errors.append("executable_not_directly_spawnable")
        if Path(launcher.path).resolve() != executable.resolve():
            errors.append("launcher_path_mismatch")
        if not workspace.is_dir() or Path(contract.cwd).resolve() != workspace:
            errors.append("fixture_cwd_invalid")
        if not self._is_within(workspace, controlled_work_root):
            errors.append("workspace_not_under_controlled_root")
        if "exec" not in args or args.index("exec") != 2:
            errors.append("exec_subcommand_position_invalid")
        if args[:2] != ["--ask-for-approval", "never"]:
            errors.append("approval_policy_invalid")
        for flag in EXEC_REQUIRED_FLAGS:
            if flag not in args:
                errors.append(f"missing_required_flag:{flag}")
        if self._argument_value(args, "-m") != request.model:
            errors.append("model_override_invalid")
        expected_effort = f'model_reasoning_effort="{request.reasoning_effort}"'
        config_values = [args[index + 1] for index, value in enumerate(args[:-1]) if value == "-c"]
        if expected_effort not in config_values:
            errors.append("reasoning_effort_override_invalid")
        if 'model_provider="openai"' not in config_values:
            errors.append("model_provider_override_invalid")
        if f"model_max_output_tokens={request.max_output_tokens}" not in config_values:
            errors.append("output_cap_override_invalid")
        if self._argument_value(args, "--sandbox") != ("read-only" if request.read_only else "workspace-write"):
            errors.append("sandbox_invalid")
        if self._argument_value(args, "-C") != str(workspace):
            errors.append("working_directory_override_invalid")
        if self._argument_value(args, "--output-last-message") != str(request.output_path.resolve()):
            errors.append("output_path_override_invalid")
        if not request.output_path.parent.is_dir():
            errors.append("output_parent_missing")
        if contract.prompt_transport != "stdin" or contract.stdin_policy != "pipe_prompt_then_close":
            errors.append("stdin_policy_invalid")
        if not args or args[-1] != "-" or request.prompt in args:
            errors.append("prompt_transport_invalid")
        if contract.shell:
            errors.append("shell_must_be_false")
        return errors

    def preflight_exec_contract(
        self,
        request: CodexExecutionRequest,
        launcher: LauncherCandidate,
        *,
        controlled_work_root: Path,
    ) -> ExecContractPreflightResult:
        contract = self.build_command_contract(request, launcher)
        result = ExecContractPreflightResult(
            passed=False,
            contract_sha256=self.contract_semantics_sha256(),
            command=contract.public_dict(),
            fixture_workspace=contract.cwd,
            workspace_contains_git=(request.workspace / ".git").exists(),
            controlled_workspace=self._is_within(request.workspace, controlled_work_root),
            user_config_isolated="--ignore-user-config" in contract.args,
            auth_uses_codex_home="--ignore-user-config" in contract.args,
            output_parent_exists=request.output_path.parent.is_dir(),
        )
        static_errors = self._validate_contract_static(
            contract, request, launcher, controlled_work_root,
        )
        env = self._environment()
        identity: ExecutableIdentity | None = None
        try:
            identity = self._executable_identity(launcher, cwd=request.workspace, env=env)
            result.executable_identity = identity.public_dict()
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            static_errors.append("executable_identity_unavailable")
            result.diagnostics.append({"stage": "executable-identity", "error": type(exc).__name__})
        try:
            inside = self._capture(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=request.workspace, timeout=10, env=env,
            )
            toplevel = self._capture(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=request.workspace, timeout=10, env=env,
            )
            result.git_inside_work_tree = inside.returncode == 0 and inside.stdout.strip().lower() == "true"
            result.git_toplevel = toplevel.stdout.strip() if toplevel.returncode == 0 else None
        except (OSError, subprocess.SubprocessError) as exc:
            result.diagnostics.append({"stage": "git", "error": type(exc).__name__})
            result.git_inside_work_tree = None

        # Replace the stdin sentinel with --help. Clap parses the complete real
        # option sequence, but exits before reading stdin or starting a model.
        parse_command = [contract.executable, *contract.args[:-1], "--help"]
        try:
            parsed = self._capture(parse_command, cwd=request.workspace, timeout=15, env=env)
            help_text = parsed.stdout + "\n" + parsed.stderr
            result.exact_command_parse_ok = parsed.returncode == 0
            result.cli_flag_support = {
                flag: flag in help_text for flag in EXEC_REQUIRED_FLAGS
            }
            if parsed.returncode != 0:
                result.diagnostics.append({
                    "stage": "exact-command-parse",
                    "returncode": parsed.returncode,
                    "error": self._safe_stderr(parsed.stderr),
                })
        except (OSError, subprocess.SubprocessError) as exc:
            result.cli_flag_support = {flag: False for flag in EXEC_REQUIRED_FLAGS}
            result.diagnostics.append({"stage": "exact-command-parse", "error": type(exc).__name__})

        git_contract_ok = bool(result.git_inside_work_tree) or (
            "--skip-git-repo-check" in contract.args and result.controlled_workspace
        )
        if result.git_toplevel:
            repo_root = Path(result.git_toplevel).resolve()
            current = request.workspace.resolve()
            while True:
                agents = current / "AGENTS.md"
                project_config = current / ".codex" / "config.toml"
                if agents.is_file():
                    result.agents_files_found.append(str(agents))
                if project_config.is_file():
                    result.project_codex_configs_found.append(str(project_config))
                if current == repo_root or repo_root not in current.parents:
                    break
                current = current.parent
        result.repo_instruction_contamination = bool(
            result.agents_files_found or result.project_codex_configs_found
        )
        if result.repo_instruction_contamination:
            static_errors.append("repo_instruction_contamination")
        if not git_contract_ok:
            static_errors.append("git_repo_or_controlled_skip_contract_invalid")
        if not all(result.cli_flag_support.values()):
            static_errors.append("required_cli_flag_unsupported")
        if not result.exact_command_parse_ok:
            static_errors.append("exact_command_parse_failed")
        if static_errors:
            result.diagnostics.append({"stage": "contract", "errors": sorted(set(static_errors))})
        result.passed = not static_errors
        if result.passed and identity is not None:
            self._approved_launcher_path = os.path.normcase(str(Path(launcher.path).resolve()))
            self._controlled_work_root = controlled_work_root.resolve()
            self._approved_model_efforts.add((request.model, request.reasoning_effort))
            self._approved_identity = identity
        return result

    @staticmethod
    def _extract_safe_events(stdout: str) -> tuple[dict[str, int], list[str], str | None, str | None, int, int]:
        usage = {"input_tokens": 0, "cached_tokens": 0, "cache_write_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
        event_types: list[str] = []
        effective_model = None
        effective_effort = None
        tool_calls = 0
        files: set[str] = set()
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = event.get("type")
            if isinstance(event_type, str):
                event_types.append(event_type)
            raw_usage = event.get("usage") if isinstance(event.get("usage"), dict) else {}
            aliases = {
                "input_tokens": "input_tokens", "cached_input_tokens": "cached_tokens",
                "cached_tokens": "cached_tokens", "cache_write_tokens": "cache_write_tokens",
                "output_tokens": "output_tokens", "reasoning_output_tokens": "reasoning_tokens",
                "reasoning_tokens": "reasoning_tokens",
            }
            for key, target in aliases.items():
                if isinstance(raw_usage.get(key), int):
                    usage[target] = max(usage[target], int(raw_usage[key]))
            for key in ("model", "model_slug", "effective_model"):
                if isinstance(event.get(key), str):
                    effective_model = event[key]
            for key in ("reasoning_effort", "effort", "effective_reasoning_effort"):
                if isinstance(event.get(key), str):
                    effective_effort = event[key]
            item = event.get("item") if isinstance(event.get("item"), dict) else {}
            if item.get("type") in {"command_execution", "mcp_tool_call", "file_change", "tool_call"}:
                tool_calls += 1
            path = item.get("path") or item.get("file")
            if isinstance(path, str):
                files.add(path)
        return usage, sorted(set(event_types)), effective_model, effective_effort, tool_calls, len(files)

    def execute(self, request: CodexExecutionRequest, launcher: LauncherCandidate) -> BackendExecutionResult:
        if not launcher.directly_spawnable:
            raise ValueError("Codex CLI execution requires a directly spawnable native launcher")
        if self._approved_launcher_path != os.path.normcase(str(Path(launcher.path).resolve())):
            raise RuntimeError("Codex execution blocked: exec-contract preflight has not approved this launcher")
        if self._controlled_work_root is None:
            raise RuntimeError("Codex execution blocked: controlled work root is not approved")
        if (request.model, request.reasoning_effort) not in self._approved_model_efforts:
            raise RuntimeError("Codex execution blocked: model/effort pair did not pass exec-contract preflight")
        contract = self.build_command_contract(request, launcher)
        contract_errors = self._validate_contract_static(
            contract, request, launcher, self._controlled_work_root,
        )
        if contract_errors:
            raise RuntimeError(f"Codex execution blocked by exec contract: {','.join(contract_errors)}")
        command = contract.command
        env = self._environment()
        current_identity = self._executable_identity(launcher, cwd=request.workspace, env=env)
        if self._approved_identity is None or current_identity != self._approved_identity:
            raise RuntimeError("Codex execution blocked: executable hash/version changed after preflight")
        started = time.perf_counter()
        try:
            process = subprocess.Popen(
                command, cwd=contract.cwd, env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False,
            )
        except OSError as exc:
            stderr = str(exc)
            return BackendExecutionResult(
                returncode=-1, stop_reason="spawn_failed",
                infrastructure_error="infrastructure_launcher",
                diagnostic=self._execution_diagnostic(stderr),
                usage={
                    "input_tokens": 0, "cached_tokens": 0, "cache_write_tokens": 0,
                    "output_tokens": 0, "reasoning_tokens": 0,
                },
                usage_available=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                tool_calls=0, unique_files_read=0, event_types=[],
                effective_model=None, effective_reasoning_effort=None,
                command_executable=contract.executable, command_args=list(contract.args), cwd=contract.cwd,
                command_contract_sha256=self.contract_semantics_sha256(),
                stdout_sha256=hashlib.sha256(b"").hexdigest(), stdout_chars=0,
                stderr_sha256=hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
                stderr_chars=len(stderr), non_json_stdout_lines=0,
                executable_identity=current_identity.public_dict(),
                process_spawned=False, codex_process_started=False,
                turn_started_seen=False, turn_completed_seen=False, usage_seen=False,
                candidate_seen=False, output_file_seen=False,
                failure_category="app/runtime initialization",
            )
        stop_reason = None
        try:
            stdout, stderr = process.communicate(input=request.prompt, timeout=request.timeout_seconds)
        except subprocess.TimeoutExpired:
            stop_reason = "timeout"
            process.kill()
            stdout, stderr = process.communicate(timeout=10)
        latency_ms = (time.perf_counter() - started) * 1000
        usage, event_types, model, effort, tool_calls, unique_files = self._extract_safe_events(stdout)
        non_json_stdout_lines = sum(
            1 for line in stdout.splitlines() if line.strip() and not line.lstrip().startswith("{")
        )
        infra = self.classify_infrastructure_error(returncode=process.returncode, stop_reason=stop_reason, stderr=stderr)
        failure_category = self.classify_failure_category(
            returncode=process.returncode, stop_reason=stop_reason, stderr=stderr,
        )
        output_file_seen = request.output_path.is_file()
        candidate_seen = output_file_seen and request.output_path.stat().st_size > 0
        return BackendExecutionResult(
            returncode=process.returncode, stop_reason=stop_reason, infrastructure_error=infra,
            diagnostic=self._execution_diagnostic(stderr),
            usage=usage, usage_available=any(usage.values()), latency_ms=latency_ms,
            tool_calls=tool_calls, unique_files_read=unique_files, event_types=event_types,
            effective_model=model, effective_reasoning_effort=effort,
            command_executable=contract.executable, command_args=list(contract.args), cwd=contract.cwd,
            command_contract_sha256=self.contract_semantics_sha256(),
            stdout_sha256=hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
            stdout_chars=len(stdout),
            stderr_sha256=hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
            stderr_chars=len(stderr),
            non_json_stdout_lines=non_json_stdout_lines,
            executable_identity=current_identity.public_dict(),
            process_spawned=True,
            codex_process_started=True,
            turn_started_seen="turn.started" in event_types,
            turn_completed_seen="turn.completed" in event_types,
            usage_seen=any(usage.values()),
            candidate_seen=candidate_seen,
            output_file_seen=output_file_seen,
            failure_category=failure_category,
        )

    @staticmethod
    def classify_failure_category(
        *, returncode: int, stop_reason: str | None, stderr: str,
    ) -> str | None:
        if returncode == 0 and stop_reason is None:
            return None
        lowered = stderr.lower()
        categories = (
            (("authentication", "unauthorized", "not logged in", "login required", "401"), "authentication"),
            (("model unavailable", "model not found", "unsupported model", "unknown model"), "model unavailable"),
            (("reasoning effort", "model_reasoning_effort", "invalid reasoning"), "reasoning effort/config invalid"),
            (("sandbox", "workspace", "not a git repository", "permission denied"), "sandbox/workspace initialization"),
            (("subscription", "billing", "quota", "entitlement", "account", "rate limit", "429", "403"), "account/subscription"),
            (("connection", "network", "dns", "timed out", "timeout"), "network"),
            (("unexpected argument", "invalid option", "usage:"), "CLI contract"),
            (("spawn", "eftype", "panic", "runtime", "app server"), "app/runtime initialization"),
        )
        for markers, category in categories:
            if any(marker in lowered for marker in markers):
                return category
        if stop_reason == "timeout":
            return "network"
        return "unknown"

    def classify_infrastructure_error(self, *, returncode: int, stop_reason: str | None, stderr: str) -> str | None:
        if stop_reason == "timeout":
            return "infrastructure_timeout"
        lowered = stderr.lower()
        markers = (
            (("spawn eftype", "not a valid application for this os platform", "access is denied"), "infrastructure_launcher"),
            (("429", "rate limit"), "infrastructure_rate_limit"),
            (("connection reset", "connection refused", "network", "dns"), "infrastructure_network"),
            (("timed out", "timeout"), "infrastructure_timeout"),
        )
        if returncode != 0:
            for values, category in markers:
                if any(value in lowered for value in values):
                    return category
        return None
