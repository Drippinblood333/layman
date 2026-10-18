# Prune ignored project roots before scanning — 2026-10-18

Workspace-path validation already rejects missing/non-directory paths; no change
was needed there. The actual reproduced issue was marker discovery: ignored roots
such as `node_modules` were filtered from results only after wildcard traversal.

Project inspection now enumerates candidate parent directories once, excluding
ignored top-level roots before entering them. Root, one-level and two-level parent
marker lookup depths remain the same. It reuses that list for manifests, source,
test and lock markers. Evidence stays content-free; risk/permission/model behavior
is unchanged. This is depth-limited discovery, not a hard directory-count cap or
new symlink sandbox; broad visible directory trees can still require substantial
metadata work. Nested ignored names retain the previous top-level-only rule.

## Evidence

- A guarded `os.scandir` regression failed first because old inspection entered
  the ignored dependency directory; it now passes.
- A nested-marker control verifies root/two-level discovery, source/test/lock
  markers and exclusion of deeper manifests. Its initial expected list omitted
  `services` (already a valid source marker); corrected the test, not production
  classification.
- Project-status/task-plan/CLI/MCP suites: **57 passed**. Ruff/Bandit passed after
  correcting the test import-spacing warning. No suppressed checks.
- A private paired fixture contains twelve ignored dependency subdirectories and
  visible `src`, `tests`, `services/api` markers. Original source from `f11e326`
  and new inspection returned exactly equal result objects for the same workspace.
  Instrumented directory enumerations: **163 → 4**; inside ignored root:
  **27 → 0**. These are filesystem-operation counts on this fixture/runtime,
  not elapsed-time, model-token or fee savings.

Private controller/result are in ignored `build/scan-pruning-2026-10-18/`.
No model calls, dependency additions, user-install replacement or formal release.
Hosted validation of the forthcoming source commit remains open.
