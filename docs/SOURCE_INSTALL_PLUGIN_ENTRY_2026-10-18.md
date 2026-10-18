# Source installation: verify the plugin, not just pip

## Evidence and repair

A fresh Python 3.14.3 virtual environment in a Windows path containing Chinese
characters and spaces installed the hashed runtime lock and source package with
--no-deps. Pip check, installed-package provenance, isolated auto setup,
offline plan and read-only dry-run all passed. The environment contained 26
distributions; checked development stacks were absent. This used the local
checkout, not a new Git clone or a clean operating-system image.

However, the installed plugin's .mcp.json still declared bare layman. A source
virtual environment is not automatically on the desktop app's PATH. Two
source/frozen launcher regression cases failed before the repair. A restricted
native shell with no Layman on PATH also could not launch the original command.
An initial direct Python-parent check was confounded by Windows executable search
including the parent's venv directory; it was not accepted as missing-PATH proof.

install_codex_plugin now pins command/args in the **durable installed copy**
before native marketplace/plugin registration, reusing the existing process
command helper:

- Python: current interpreter, -m layman_router.cli mcp-server.
- Standalone: current executable, mcp-server.

Paths remain separate JSON arguments, including Unicode/spaces. Other server
metadata stays intact; the portable packaged/source bundle remains unchanged.
No global PATH editing, new dependency, model call or routing-policy change.
Moving/deleting the runtime requires rerunning setup from the replacement runtime.

## Validation

- **51** lifecycle/CLI/MCP tests passed, including both launcher modes and unchanged
  bundle/metadata checks. Scoped Ruff/Bandit, secret and diff checks passed.
- Reinstalled only the repaired package inside the new test venv, leaving its
  runtime dependencies unchanged. Repeated auto setup in the same isolated Codex
  profile: native 0.162.0-alpha.20 plugin cache matched the repaired command.
- Launched the **cached** command with no global layman on PATH: initialize,
  three-tool listing and an offline plan call all passed.
- Real user's Codex configuration SHA stayed unchanged. Test setup/profile/state
  stayed under ignored build directories; no existing installation was replaced.
  Model calls: zero. No paid API, reset credit, tag or release.

The new interpreter/profile and real local MCP handshake are stronger evidence
than pip success, but do not certify GUI restart behavior, logged-in model access,
every Python version, or an actual frozen/native plugin setup on all platforms.
Frozen launcher selection is unit-tested; hosted build gates are recorded
separately when terminal.

[Official desktop-local MCP guidance](https://developers.openai.com/plugins/deploy/desktop-only#configure-a-local-mcp-server)
was searched/fetched before editing. It documents a local executable and argument
vector; the repair preserves the repository's existing plugin layout rather than
migrating formats. Native CLI/cache behavior was verified locally, not inferred
from those docs. Private phase/results evidence is under
build/source-onboarding-2026-10-18/; no raw model/user configuration is retained
in the committed report. This is installation correctness, not token savings.
