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

Check the Codex login and preview the fixed 18-case, 36-call calibration without making a model call:

```powershell
layman codex-plus status
layman codex-plus eval
```

Run the resumable calibration in batches of at most 12 calls:

```powershell
layman codex-plus eval --run
```

Plus mode does not exercise the HTTP proxy, API fallback, or API billing. Use `$layman` for idea-to-result work and `$layman-status` to understand project progress.

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
