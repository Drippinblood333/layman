# Approved Plus calibration — 2026-10-09

The owner explicitly approved the proposed new maximum of 36 entire ChatGPT-subscription Codex executions. This is a separate authorization from the exhausted 12-execution task trial. No paid API evaluation, answer-text retention, installed configuration replacement, release tags or publication is authorized.

The fixed release corpus has 18 self-contained cases with auto/deep arms (36 planned executions). Sessions are ephemeral/read-only and request no tools. This is routing/text calibration, not a repository implementation benchmark, human semantic-quality review or whole-task token-savings proof. Output text remains excluded from telemetry; source prompts are existing synthetic fixtures.

New approval output/journal: `build/plus-calibration-2026-10-09/results.jsonl` and its `.attempts.jsonl`; immutable ceiling for this approval: 36. Failures and interrupted launches count. Do not increase the cap, discard the journal, change output to bypass it or replay an interrupted reservation. Execution stops on failure. Protocol v4 adds persistent pre-launch reservations, fsync result writes and an exclusive output writer lock; locks are not automatically stolen. The old task trial is preserved unchanged.

Before launch, 327 local tests pass. Three new regressions cover failure-inclusive cumulative limits, interrupted-reservation refusal and pre-Codex lock exclusion. Configured lint and secret scanning must pass before live execution. Human scores remain absent until actual review; completion of 36 executions alone cannot close the semantic-quality or public-release gates.

Execution evidence will be appended after actual bounded runs; this document is not a completed-calibration claim.
