# Lossless-log pilot v2: lower usage, failed quality gate

## Decision

**Do not count this as verified token savings or enable encoding by default.**
Raw input passed the preregistered answer check; encoded input did not. Both
invocations completed with usage, but only one met the same quality requirement.
Reversible text encoding does not prove equivalent model comprehension.

## Fixed comparison and results

The independently declared v2 protocol reused the synthetic fixture and validator
from the earlier startup-refused pilot, without editing its frozen records. Before
any reservation, native offline rendering succeeded with corrected configuration;
the round trip was exact and the six mutated expected answers were rejected.
V2 removed prohibited built-in-provider retry overrides from both arms. Native
internal retries remained unchanged, not disabled or independently counted.

Fixed order: raw then encoded; same `gpt-6-sol`/medium, verified full private
0.162.0-alpha.20 runtime, instruction, six-field JSON Schema/expected-value gate,
workspace and read-only permissions. No developer-instruction replacement or
skill-catalog suppression. Source at execution:
`1c7e6084e214239bb9b4a97ecb20e200016fabe7`, confirmed against the immutable
private manifest and local Git object.

| Metric | Raw log | Encoded log |
| --- | ---: | ---: |
| Input tokens | 37,255 | 21,236 |
| Cached input tokens | 0 | 0 |
| Output tokens | 46 | 109 |
| Reported reasoning tokens, included in output | 0 | 60 |
| Total input + output | 37,301 | 21,345 |
| Latency, milliseconds | 15,785 | 21,393 |
| Tool calls / file references / compactions | 0 / 0 / 0 | 0 / 0 / 0 |
| Native return code | 0 | 0 |
| Same strict answer gate | PASS | FAIL |
| Global config hash unchanged | yes | yes |

Observed total usage was 42.78% lower for the encoded arm, but the same-quality
gate failed, so that percentage is **not an accepted saving**. Encoded latency
also increased. Reasoning tokens are not added to output a second time.

The journal has exactly two fsynced reservations and two results; the run exited
zero after recording the failed gate and stopping as designed. No replacement,
replay, fallback, extra model call, paid API or reset credit was used. The raw
result was recorded before the encoded launch. Temporary answer files were
removed after checking; no raw model answer was retained in telemetry/results.

## Limits and next action

- The gate checked six exact fields: first/second error order, expected/actual
  integers, checkpoint marker and final exit status. It did not test repetition
  counts, open-ended root-cause quality, code edits or human usefulness.
- Result records retain only an aggregate quality boolean. They do not identify
  which field, JSON parsing or schema check failed. The removed answer cannot be
  reconstructed; do not invent a specific misreading or claim proven semantic
  degradation from this one strict-check failure.
- This supplied log representations in a local CLI extraction task. It did not
  exercise production API `function_call_output` transport or automatic Plus tool
  interception. One synthetic, fixed-order pair is not a representative benchmark.
- Frozen evidence lives under ignored
  `build/lossless-log-pair-v2-2026-10-16/`: protocol, wrapper identity, manifest,
  attempts and numeric results. The earlier v1 remains separate and unchanged.

Keep the encoder experimental and opt-in. Update onboarding to distinguish exact
text restoration from model-answer quality. Any future quality investigation
should preregister per-field pass/fail metadata without retaining answers, and
address validator clarity before spending more calls; it is not automatically
authorized as a replay of this closed pair. Broader task-token benefits remain
unproven. No production behavior, installation or formal release changed here.

The [official non-interactive usage documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
was searched/fetched before v2 for native usage events. The
[main CI 38876769558](https://github.com/Drippinblood333/layman/actions/runs/38876769558)
is now terminal SUCCESS on exact `eeea9ca2358d04a947da1773e6f5ead6b51cc67e`,
closing the previous source-repair main gate. No duplicate CI was dispatched for
this documentation-only evidence batch.
