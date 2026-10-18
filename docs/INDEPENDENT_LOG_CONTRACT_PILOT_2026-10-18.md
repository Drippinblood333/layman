# Two independent clarified-log pairs: limited positive result

## Result and decision

Both newly authored synthetic log tasks passed the same strict six-field check
in raw and encoded form. Across the two complete pairs, native total usage fell
from **51,326 to 42,854 tokens (16.51%)**. This is an observed same-check reduction
for these two extraction tasks, NOT a general coding, API invoice or release claim.
Keep the feature experimental and opt-in; do not erase the earlier failed pilots.

| Case | Raw total | Encoded total | Raw cached input | Encoded cached input | Both exact checks |
| --- | ---: | ---: | ---: | ---: | --- |
| archive_lf | 23,731 | 21,410 | 23,552 | 0 | 6/6 PASS |
| unicode_crlf_edges | 27,595 | 21,444 | 27,392 | 21,248 | 6/6 PASS |
| Sum | 51,326 | 42,854 | 50,944 | 21,248 | all four pass |

Per-invocation details:

| Case / arm | Input | Output | Reasoning included in output | Latency ms |
| --- | ---: | ---: | ---: | ---: |
| archive_lf / raw | 23,684 | 47 | 0 | 13,126 |
| archive_lf / encoded | 21,348 | 62 | 13 | 19,467 |
| unicode_crlf_edges / encoded | 21,366 | 78 | 24 | 21,639 |
| unicode_crlf_edges / raw | 27,543 | 52 | 0 | 30,450 |

Total means input + output; cache is not subtracted and reasoning is not added
twice. Cache is strongly unequal, especially the first pair. Lower total token
count therefore does not establish lower billing, lower quota consumption, or
stable latency. The first encoded run was slower; no speed improvement is claimed.

## Controlled scope

The four-invocation ceiling and order were frozen before execution: first case raw
then encoded; second encoded then raw. These were not the old v1-v3 fixture or the
three public contract unit cases. Manual expected values agreed with an independent
reference parser; encoded logs restored exactly. The clarified contract excludes
CRLF/LF/CR terminators but preserves all other characters, including the second
case's leading whitespace/tab, Unicode and trailing spaces.

Within each pair: same task, schema, Sol/medium, read-only workspace, verified
full private alpha.20 runtime and native settings. Only log representation differed.
No user developer-instruction override, skill suppression, model fallback or
production-default change. All four had complete usage, zero tools/file references/
compactions, exit zero and unchanged real configuration hash.

Preparation was frozen at e99263dc24fa149cfc9f6b85e54d8801700aa352; execution source
was acd7850a1e9f53e28bc9707543b6962f7a8396a2. Relevant fixture/helper/protocol hashes
were verified unchanged before launch, and runner/codec/runtime identities were
recorded before reservations. Journals contain exactly four fsynced reservations
and four results. All strict gates passed; no replacement/replay was needed.

## Quota preflight recovery

Earlier app quota reads and the first native quota read failed; their records
remain intact. A subsequent documented native account/rateLimits/read succeeded,
reporting 56%/9% used. No authentication/proxy settings or reset credits were
changed. The original error's cause is still unknown; recovery is not proof of a
configuration fix. The successful native result was fresh before execution.

The [official native quota RPC](https://learn.chatgpt.com/docs/app-server#6-rate-limits-chatgpt)
and [usage events](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
were searched/fetched before this work. Native internal requests/retries were not
independently counted: four CLI invocations are not a four-HTTP-request guarantee.

## Remaining limits

- Six exact extraction fields are not coding correctness, repetition-count
  understanding, human root-cause quality or representative end-user acceptance.
- Two hand-authored tasks, one model/runtime and a single run per arm do not
  establish generalization or stable causal effects.
- This provided synthetic log data to CLI tasks. It did not exercise production
  API function-call-output transport or automatically intercept Plus shell output.
- Earlier v2/v3 marker failures still stand. Different tasks and a clarified
  contract prevent attributing improvement solely to wording or claiming the old
  failures were fixed.

No paid API, extra judge, reset, installed-version replacement, tag or formal
release. No model answers/config text are stored in committed evidence; private
numeric journals and frozen synthetic fixtures are under ignored
build/independent-log-contract-pilot-2026-10-18/. Next acceptance work must cover
real development tasks and broader quality, not extrapolate this percentage.
