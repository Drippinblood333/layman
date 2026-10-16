# Large-input streaming: timeout and pipe deadlock repair

## What failed

`_consume_bound_process` synchronously wrote all stdin before starting stdout/
stderr readers or its timeout clock. A child that did not read stdin could block
the write indefinitely. A child that filled stderr before reading stdin could
deadlock both processes. Neither situation needs a model call to reproduce.

Two local Python-child regressions failed before the fix. Each sent 1 MiB input;
one child slept without reading, the other wrote 20,000 diagnostic lines before
reading. An independent five-second cancellation watchdog was needed to release
both. Watchdog activation is test failure, not successful timeout handling.

## Minimal change and evidence

Start output readers and a daemon stdin writer before consuming events. Start
the timeout clock before these threads, so a blocked input write no longer blocks
deadline enforcement. The writer closes stdin in a finally block, suppressing
expected broken-pipe/OS errors from a child that exits early. After process exit,
join the writer with a bounded one-second wait. Existing process-tree cancellation,
tool/file ceilings, native UTF-8 handling, usage parsing and original input remain
unchanged. No new dependency, model policy or prompt rewrite.

- **103** execution tests passed, including blocked-input timeout, concurrent
  output draining and early-exit diagnostics/return-code preservation.
- **96** additional evaluation/benchmark/MCP tests passed.
- Existing lossless-output regressions: **28** passed.
- Scoped Ruff, Bandit, release secret scan and diff checks passed.
- An offline native `debug prompt-input` configuration refusal with 1 MiB piped
  stdin exited one with its original refusal preserved, no timeout, no usage, and
  no destructor-time pipe-flush error. It did not invoke model inference.

These tests cover the owned process/input path, not a guarantee that arbitrary
detached descendants or every operating-system failure are bounded by exactly the
configured timeout. Existing termination/cleanup grace time still applies.

## Related codec pilot: invalid startup, not a token result

Before the pipe fix, a private synthetic log-extraction pilot was preregistered
for at most two subscription executions: raw versus the existing lossless codec,
same Sol/medium, read-only workspace, native runtime, instruction, schema and
six-field exact-value quality gate. Offline round-trip passed (59,566 raw UTF-8
bytes versus 376 encoded bytes). This byte reduction is not token savings.

The first reservation failed at startup in 117 ms with return code one and no
completed-turn usage. The assistant's private script incorrectly attempted to
set retries under the reserved built-in `model_providers.openai` table. Native
offline rendering reproduced that exact configuration rejection; removing those
overrides made offline rendering succeed. This was a harness mistake, not evidence
that the codec or model failed the task. The raw invocation also exposed an ignored
stdin finalizer OS error that the explicit-close repair addresses.

The immutable pilot journal contains **one reservation and one failed result**.
The encoded arm was not launched, and the pilot was closed without replacement,
fallback or replay. Missing usage is not measured zero usage or a billing claim.
No paired comparison or live task-quality/token conclusion exists. A future pilot
needs a newly declared protocol compatible with native provider rules; do not
silently relax the frozen protocol or spend its unused slot.

The [official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
was searched and fetched before the attempted pilot for JSON usage, ephemeral
execution and structured final-output behavior. Documentation does not substitute
for actual successful usage/quality evidence. No API key, paid API, reset credit,
installed-version replacement, tag or formal release was used.

[Hosted CI 38876269707](https://github.com/Drippinblood333/layman/actions/runs/38876269707)
completed SUCCESS without retries on exact
`eeea9ca2358d04a947da1773e6f5ead6b51cc67e`: all ten validation jobs passed,
including three OS test suites, five standalone targets, Docker and combined
release assets. Publish skipped. The exact SHA was fast-forwarded non-force to
main after an ancestry check. Automatic main CI 38876769558 was observed queued;
its final result is not yet claimed. No additional model attempt was launched.
