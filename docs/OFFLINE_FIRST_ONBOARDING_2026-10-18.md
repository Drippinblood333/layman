# Offline-first onboarding — 2026-10-18

## Evidence-backed documentation correction

The source guide previously listed only Git/Python prerequisites but ran `setup`
before `plan`. Actual default setup calls `install_codex_plugin`, which requires
a discoverable working Codex CLI and successful plugin commands. Missing that
dependency need not prevent trying offline planning.

English/Chinese READMEs and the installation guide now distinguish:

- Install the locked runtime and try `plan` without setup or credentials.
- For plugin/execution, check CLI discovery/login before setup. A successful login
  check does not certify plugin compatibility, model access or execution readiness.
- Setup does not install/upgrade Codex; Plus execution needs ChatGPT credentials.
- Auto detection selects API mode if an API key is present; explicit Plus mode is
  available when the user wants subscription execution instead.

The [official Codex CLI guide](https://developers.openai.com/codex/cli#getting-started)
was fetched after official documentation search to verify installation/sign-in
guidance. No Codex installer was executed and no user configuration was changed.

## Verification and limits

An actual in-process CLI `plan` with temporary workspace/stdin succeeded while
Codex discovery, plugin installation and task-execution entrypoints were patched
to fail on invocation; all three call counts were zero. The first ad-hoc check
failed because its harness used `patch.DEFAULT` instead of importing `DEFAULT`;
the corrected harness passed. This was not a product failure or model call.
Existing CLI regressions: **22 passed**. Whitespace check passed.

Only documentation changed. No full package rebuild or repeated model evaluation
is needed for this batch. This does not certify a fresh operating-system install,
all supported platforms, public-release installation or token savings. The overall
goal remains active; runtime release checks still apply.
