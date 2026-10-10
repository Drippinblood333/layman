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

Python 3.11 or newer is required only for source development:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".\services\layman-router[dev]"
.\.venv\Scripts\layman setup --mode auto
```

On macOS/Linux, use `.venv/bin/python` and `.venv/bin/layman`.

To reproduce the release runtime dependency set instead of resolving the compatible ranges again:

```powershell
python -m pip install --require-hashes -r .\services\layman-router\requirements.lock
python -m pip install --no-deps .\services\layman-router
python -m pip check
```

## Upgrade and uninstall

Install the new release over the old executable, then run `layman doctor`. Legacy v2 data is copied from `~/.layman-router` to `~/.layman` only when the new destination does not exist; the source is retained.

Run `layman uninstall` to stop the service, remove the Layman plugin and local marketplace, and restore managed Codex settings. Data and backups remain in `~/.layman`. Add `--purge-data` only when permanent deletion is intended. Purging succeeds only when plugin/marketplace references are resolved, the home has a valid Layman ownership marker, Layman originally created the directory, and every remaining entry appears in its managed-path manifest. A pre-existing custom `LAYMAN_HOME`, an unknown file, a malformed marker or an unavailable Codex CLI when references may remain causes a refusal and preserves the data. A fresh installation created with `setup --skip-plugin` records that no plugin was managed and can purge its isolated Layman-created home without calling Codex. Re-running that option never downgrades an existing or legacy installation's conservative cleanup state.

Destructive tasks are blocked before a child Codex process starts. After reviewing the exact stdin task and scope, a local terminal user can make a one-run authorization with `layman run --allow-destructive --clipboard`. The Codex MCP tool intentionally has no equivalent switch.
