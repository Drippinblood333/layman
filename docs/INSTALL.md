# Installation

Layman has two user modes. Every user receives `$layman` and `$layman-status`. ChatGPT users can use the Experimental `$layman-auto` one-task launcher. OpenAI API users additionally receive the local `model="auto"` Responses proxy. A ChatGPT subscription cannot authenticate the API proxy.

No public Layman release exists yet. Until a verified GitHub release is published, the one-line commands below intentionally have no installable target; contributors should use [source installation](#source-installation).

## Standalone installation

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/Drippinblood333/layman/main/install.ps1 | iex
```

macOS or Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Drippinblood333/layman/main/install.sh | sh
```

The installer downloads the matching release artifact and `SHA256SUMS.txt`, verifies the archive before extraction, adds the executable to the user path, installs the bundled local Codex plugin marketplace, and runs `layman setup --mode auto`. It never enables API routing without an API key. Code signing is not claimed for the first release candidate. Restart Codex and open a new task after installation so the plugin and updated path are loaded.

Installers also retain `THIRD_PARTY_LICENSES/`, third-party notices and the build,
runtime and component inventories. Missing required package files stop installation
before replacing the executable. On Windows these records stay beside the executable
in `%LOCALAPPDATA%\Layman\bin`; macOS/Linux use
`${XDG_DATA_HOME:-$HOME/.local/share}/layman/installation`, keeping generic notice
names out of the shared executable directory. They are installer-managed records,
not `LAYMAN_HOME` user data; `layman uninstall --purge-data` does not delete them.
Upgrades preserve older notice files rather than recursively clearing the directory.

Release-candidate testers must target the exact prerelease tag because GitHub's `latest` endpoint excludes prereleases:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/Drippinblood333/layman/main/install.ps1))) -Version v1.0.0-rc.1
```

```bash
curl -fsSL https://raw.githubusercontent.com/Drippinblood333/layman/main/install.sh | LAYMAN_VERSION=v1.0.0-rc.1 sh
```

## ChatGPT Plus mode

You do not need an API key, a running router service, a dashboard, or a benchmark to start. After installation, restart Codex and open a new task.

Check the Codex login and project status; neither command launches a model task:

```powershell
layman codex-plus status
layman status
```

When the saved setup mode is Plus, project `status` skips the optional API-router
health request and labels it `not_checked` / `required: false`, rather than
presenting an offline API service as part of Plus setup. This does not check
ChatGPT login; use `layman codex-plus status` for that. `layman status --service-only`
still explicitly checks the API service, as do API-mode or unknown-mode status requests.

`layman doctor` also follows the saved Plus setup mode: it checks CLI startup and
stored ChatGPT login, and labels the API key, dashboard token and router service
`not_required`. It still validates the shared routing configuration, but does not
require the API database. Exit zero means credentials
were detected, not that subscription access, the selected model or sandboxed
task execution was verified. No login credentials or raw login diagnostics are
printed. API and unknown setup modes retain the API configuration/service checks.
[Official CLI login reference](https://learn.chatgpt.com/docs/developer-commands#codex-login).

For a short task, you can instead enter `layman plan` or `layman run --dry-run`
directly. When prompted, type one line and press Enter. This input is read by
Layman rather than the shell, so it is not placed in shell command history;
the prompt goes to stderr, leaving structured stdout unchanged. Use the clipboard
or UTF-8 stdin for multiline requests. Planning and dry runs do not launch a model;
`layman run` does execute the entered task and consumes subscription allowance.

Or copy your actual task to the clipboard and preview the plan without launching a model:

```powershell
layman run --dry-run --clipboard
```

When the preview matches your intent, run `layman run --clipboard`. This step executes a task through your ChatGPT subscription and consumes its usage allowance. Alternatively, ask `$layman` in Codex to help with your task; `$layman-status` explains project progress. You do not need to select model tiers or write a formal specification for a simple task.

If you are unsure how to describe the task, `layman plan --clipboard` offers an offline plan. For a few obvious vague phrases such as "improve the whole project", it asks at most two questions about the intended result and acceptance criteria and marks the plan as `plan-first`. It does not rewrite, execute or retain your task. The same limited check applies to `run` and MCP: recognized vague requests return `prompt_clarification_required` before starting Codex. Supply the original task with the intended outcome and acceptance details before trying again; no scope is silently removed. This limited wording check is not a complete prompt-quality or safety assessment; an empty question list is not proof that a request is unambiguous.

Plus mode does not exercise the HTTP proxy, API fallback, or API billing.

In CLI/MCP `plan` results, read clarification from the top-level `prompt_guidance`.
It is not duplicated under `route`. Standalone `run --dry-run` previews still
include their own `prompt_guidance`; their execution-blocking behavior is unchanged.

When the selected route is read-only, plan next steps and acceptance criteria also
stay read-only: report the requested evidence and limits, without recommending
implementation or publishing. This takes precedence over project-stage release
steps; clarification questions, when present, still come first. It reuses the
selected permission result, not a new claim to understand every prompt.

Project status treats failed Git branch/status reads as unknown (`null`), not as
proof of a clean checkout. Each successful field remains available independently;
the `repository` flag indicates a `.git` marker, not a repository integrity check.

Release-candidate planning ignores recognized future-approval boilerplate such as
"公开发布时，我会批准" or "When we publish, I will approve" when selecting the
current workflow. English `ship` must be a whole word, not part of `ownership` or
`membership`. A separate request to check or perform a release still selects the
release gate. This narrow wording filter does not grant authorization, rewrite the
task, or understand all future/negated/quoted instructions.

Use `$layman-auto` in a new task to route the original request through the bundled local MCP tool. The tool verifies ChatGPT login, removes API-key environment variables, and starts an ephemeral Codex run. Terminal users can copy a task to the clipboard and pipe standard input without placing the task text in command history:

```powershell
layman codex-plus run --dry-run --clipboard
layman codex-plus run --clipboard
```

The shorter public commands are equivalent:

```powershell
layman status
layman plan --clipboard
layman run --dry-run --clipboard
layman run --clipboard
```

`--clipboard` reads Unicode text directly and avoids both shell history and Windows PowerShell 5 pipeline encoding loss. Standard input remains available for scripts that already emit UTF-8.

High-risk tasks are routed to deep and run read-only. Model-unavailable fallback only moves upward; subscription or authentication errors never fall back to API billing.

### Developer calibration — not a first-use requirement

`layman codex-plus eval` previews the fixed 18-case, 36-call comparison without launching a model. Running it is an evaluation workload, not setup or an ordinary user task. Only execute after a separate approval that names the cumulative call budget and output journal. A per-batch limit alone is not a cumulative allowance; failures also consume budget. See the [benchmark controls](BENCHMARKS.md) and [current release evidence](SELF_UPDATE_STATUS.md). Existing exhausted approvals do not authorize a new run.

## OpenAI API mode

Set `OPENAI_API_KEY` only in the shell or secret manager used to start Layman. Then preview setup:

```powershell
layman setup --mode api
layman codex enable --dry-run
```

After reviewing the diff:

```powershell
layman codex enable --apply
layman start
layman status
layman dashboard
```

`layman setup --mode api --apply-codex --start` performs the same steps explicitly in one command. API routing is Beta until a release-grade live API benchmark is completed.

## Source installation

Until a standalone release is available, use the source checkout with Python
3.11 or newer and Git installed. Ordinary use needs only the locked runtime
dependencies, not the test, audit or packaging tools. This is the currently
available install path, not the unavailable release installer above.

Offline planning works without Codex CLI, ChatGPT login, API keys or `setup`.
The offline CLI does not preload the API server; `serve` and `demo` load it when
needed. This does not change the locked dependency set or remove API support.
To enable the Codex plugin and execute tasks, you additionally need a working
Codex CLI with plugin support; Plus execution needs ChatGPT sign-in. Follow the
[official Codex CLI installation and sign-in guide](https://developers.openai.com/codex/cli#getting-started)
if needed. Layman does not install or upgrade Codex for you. An installed desktop
app alone is not proof that Layman can find a compatible CLI.
If automatic discovery cannot find/start Codex CLI, default setup now stops before
creating or changing Layman's installation state. This is a prerequisite check,
not an all-or-nothing installation guarantee: detection may create an explicitly
configured Codex home, and later plugin/configuration failures can still leave
partial setup work. Login is not required merely to install the plugin.

First download the project and enter its root directory. If you already have a
checkout, open a terminal in that directory instead; do not clone inside it:

```text
git clone https://github.com/Drippinblood333/layman.git
cd layman
```

Windows PowerShell (run from the directory containing the top-level `README.md`):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes -r .\services\layman-router\requirements.lock
.\.venv\Scripts\python -m pip install --no-deps .\services\layman-router
.\.venv\Scripts\python -m pip check
.\.venv\Scripts\layman plan --brief
```

macOS/Linux (run from the same project root):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r services/layman-router/requirements.lock
.venv/bin/python -m pip install --no-deps services/layman-router
.venv/bin/python -m pip check
.venv/bin/layman plan --brief
```

Keep using the full `.venv` executable paths shown above after opening a new
terminal in this checkout. A source install does not put `layman` on the global
PATH; bare `layman` examples elsewhere assume a PATH-enabled installation. No
activation script or shell execution-policy change is required. `plan` reads a
task you type and does not launch a model. Piped task input must be UTF-8 regardless of the terminal's text
encoding; invalid UTF-8 is rejected before planning or execution. Terminal
one-line entry and `--clipboard` retain their existing Unicode input paths. Use
`--clipboard` if your shell would encode a text pipeline differently.
`--brief` keeps clarification questions, permissions, budgets, next
steps, success criteria and stop conditions but omits internal route diagnostics.
It does not execute, rewrite the task or certify readiness. Omit the flag for the
unchanged full JSON output used by integrations. Stop here if you only want offline
planning. To enable plugin/execution, first check CLI discovery and saved login,
then run setup:

```powershell
# Windows PowerShell
.\.venv\Scripts\layman codex-plus status
.\.venv\Scripts\layman setup --mode auto
```

```bash
# macOS/Linux
.venv/bin/layman codex-plus status
.venv/bin/layman setup --mode auto
```

`codex-plus status` checks saved login, not actual model access or plugin-command
compatibility. If the CLI is missing or cannot start, resolve that before setup;
if ChatGPT credentials are missing, sign into Codex before Plus execution. Setup
installs the plugin; restart Codex and open a new task afterward. Auto mode may
choose API routing when an API key is present; use `--mode plus` instead when you
specifically want ChatGPT-login execution without API routing.

Setup pins the installed plugin's MCP launcher to the Python environment or
standalone executable that ran setup, rather than relying on the desktop app's
PATH. Keep that runtime in place. If you move or recreate the virtual environment,
run setup again from its new full command path, then restart Codex. The portable
plugin source bundle is not rewritten.

Only contributors who need tests, audits or builds should additionally install
the development tools:

```powershell
.\.venv\Scripts\python -m pip install -e ".\services\layman-router[dev]"
```

## Upgrade and uninstall

Install the new release over the old executable, then run `layman doctor`. Legacy v2 data is copied from `~/.layman-router` to `~/.layman` only when the new destination does not exist; the source is retained.

On Windows, the installer prepares the executable and its records in a sibling
staging directory before switching the installation. Existing extra files are
preserved. A file-copy or caught directory-switch failure leaves or restores
the previous tree; close any running Layman process before retrying a file-in-use
error. If automatic restoration fails, the error reports the preserved backup
directory. Successful updates remove the staging/backup directories, or warn
when an old backup cannot be fully removed. This needs temporary staging space.
It is not crash/power-loss recovery, concurrent-installer coordination, or rollback
of `setup` changes; a failed setup still reports failure with installed files
preserved.

On macOS/Linux, the installer stages both the executable and its records beside
their destinations. It preserves extra record files and restores the old records
if their switch or the final executable rename fails; staging failure leaves both
old components untouched. A failed restoration keeps the backup and reports its
path. This is caught-error recovery, not a single atomic transaction across the
two directories, concurrent-installer coordination, interruption/power-loss
recovery, or rollback of subsequent `setup` changes. Temporary staging space is
required. Setup failure remains a failure after the files have been installed.

Run `layman uninstall` to stop the service, remove the Layman plugin and local marketplace, and restore managed Codex settings. Data and backups remain in `~/.layman`. Add `--purge-data` only when permanent deletion is intended. Purging succeeds only when plugin/marketplace references are resolved, the home has a valid Layman ownership marker, Layman originally created the directory, and every remaining entry appears in its managed-path manifest. A pre-existing custom `LAYMAN_HOME`, an unknown file, a malformed marker or an unavailable Codex CLI when references may remain causes a refusal and preserves the data. A fresh installation created with `setup --skip-plugin` records that no plugin was managed and can purge its isolated Layman-created home without calling Codex. Re-running that option never downgrades an existing or legacy installation's conservative cleanup state.

Destructive tasks are blocked before a child Codex process starts. After reviewing the exact stdin task and scope, a local terminal user can make a one-run authorization with `layman run --allow-destructive --clipboard`. The Codex MCP tool intentionally has no equivalent switch.
