# Executable repair fixture: limited component evidence

## Result

Both executions repaired the capped-backoff fixture and passed the same
signature, 52 numeric-case and no-stdout checks. Only target.py changed; final
driver, codec and instruction hashes were intact. Intended raw/encoded driver
execution was observed, including a native nonzero exit before repair and a zero
exit afterward. Both had complete usage and unchanged real configuration hash.

Native totals were **172,897 raw versus 114,338 encoded (33.87% lower)** for this
single paired fixture. This is not a general Layman, production-development or
invoice-saving claim. Defaults remain unchanged.

| Metric | Raw | Encoded |
| --- | ---: | ---: |
| Input tokens | 171,314 | 113,069 |
| Cached input tokens | 165,632 | 110,464 |
| Uncached input, arithmetic difference | 5,682 | 2,605 |
| Output tokens, including reasoning | 1,583 | 1,269 |
| Reported reasoning tokens | 731 | 691 |
| Total input + output | 172,897 | 114,338 |
| Tool events | 6 | 4 |
| File-reference metadata count | 3 | 3 |
| Observed command output characters | 24,865 | 1,447 |
| Completed command outputs observed | 4 | 3 |
| Driver observations: native exits | 1, 0, 0 | 1, 0 |
| Latency ms | 64,562 | 44,247 |

Reasoning is not added twice, and cached tokens are not subtracted from total.
Cache and tool sequences differ. Raw performed an additional successful driver
check, so the entire difference cannot be causally assigned to the codec. These
latencies do not establish stable speedups; output characters are not input tokens.
File-reference counts are metadata observations, not independently verified reads.

## Controlled task and validation

Same original task, source bytes, public driver, copied production codec function,
AGENTS guidance, requested Sol/medium and full matched private alpha.20 runtime.
Separate fresh workspaces began with identical file hashes. Only the inherited
driver-output mode differed; 2000-token native output limit and five-file/ten-tool
ceilings were identical, not enlarged to manufacture a reduction.

The driver emits repeated deprecation warnings plus actual result details. Its
mode marker is test instrumentation, not a production feature. Offline checks
rejected the original, accepted the reference repair and proved both log modes
preserved failure exit one and exact restoration. During model executions,
immutable driver output markers and native command metadata established mode/
failure/pass coverage. This is not adversarial execution attestation.

The hidden validator covers capped/uncapped, zero, equality and fractional cases,
parameter names/kinds/defaults and unexpected stdout. It is a bounded numeric
sample, not proof of all float/overflow behavior, integration correctness or human
acceptance. Generated Python bytecode is excluded from scope comparison. No human
judge or additional model was launched by the controller; no external MCP or
collaboration events were observed. Backend requests are not independently counted.

## Provenance and limits

Execution source: 60764c0189eb3c2c2fcddec7b2416df8c7a2340c. Protocol, original
file/task, runner, fixture, quota and runtime identities were frozen before calls.
Exactly two reservations/results, both strict gates passed; hashes and usage
arithmetic were independently rechecked. Fresh preflight reported ordinary usage
allowed, five-hour 70% used and weekly 11%. No reset or paid API was used.

Private evidence is under build/coding-log-pair-2026-10-18/. Journals retain fixed
labels, numeric metrics and booleans, not source, answers or full tool logs; the
generated code necessarily remains in private test workspaces.
[Official JSON usage documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
was searched/fetched before execution.

This is a small synthetic but executable coding task, not a repair of a live
production repository. It does not exercise the API proxy or install automatic
Plus shell interception: the fixture driver explicitly applied the existing
encoder. One fixed-order pair and different tool choices do not establish broad
causal savings. Do not pool it with the earlier extraction or router comparisons.
Earlier negative evidence remains intact. No user install, model policy, tag or
formal release changed; broader development-quality evidence remains required.
