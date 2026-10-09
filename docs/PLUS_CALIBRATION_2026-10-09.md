# Approved Plus calibration — 2026-10-09

The owner explicitly approved the proposed new maximum of 36 entire ChatGPT-subscription Codex executions. This is a separate authorization from the exhausted 12-execution task trial. No paid API evaluation, answer-text retention, installed configuration replacement, release tags or publication is authorized.

The fixed release corpus has 18 self-contained cases with auto/deep arms (36 planned executions). Sessions are ephemeral/read-only and request no tools. This is routing/text calibration, not a repository implementation benchmark, human semantic-quality review or whole-task token-savings proof. Output text remains excluded from telemetry; source prompts are existing synthetic fixtures.

New approval output/journal: `build/plus-calibration-2026-10-09/results.jsonl` and its `.attempts.jsonl`; immutable ceiling for this approval: 36. Failures and interrupted launches count. Do not increase the cap, discard the journal, change output to bypass it or replay an interrupted reservation. Execution stops on failure. Protocol v4 adds persistent pre-launch reservations, fsync result writes and an exclusive output writer lock; locks are not automatically stolen. The old task trial is preserved unchanged.

Before launch, 327 local tests pass. Three new regressions cover failure-inclusive cumulative limits, interrupted-reservation refusal and pre-Codex lock exclusion. Configured lint and secret scanning must pass before live execution. Human scores remain absent until actual review; completion of 36 executions alone cannot close the semantic-quality or public-release gates.

The following execution evidence was appended after the actual bounded runs; pre-launch planning alone was not treated as completion.

## Completed execution evidence

Source: `f1ae6db427226fcd463849559ed720a49cc23c60`; protocol v4; Codex `0.162.0-alpha.2`; runtime fingerprint `3fc8739a20cfef88233a9504558f293da35465ca6637ab11bc7eeb12ac743c72`. The originally configured CLI path had disappeared after a local app update. That preflight failed before any reservation/model call; normal executable discovery found the current native CLI and ChatGPT login was verified. No account configuration or installed application was replaced.

Two diagnostic executions completed first, then the remaining 34 completed under the same source, fingerprint, original approval journal and total cap 36. All 36 executions completed: zero failures, zero incomplete usage records, zero tools, 18 complete auto/deep pairs. Auto routes: six fast (GPT-6 Luna / low), two balanced (GPT-6.1 Sol / medium), ten deep (GPT-6 Astra / high); the baseline always uses Astra / high. No model fallback or extra replay occurred. Both process handles are terminal. **36/36 reservations used, zero remaining**; the preceding 12-execution task trial is separately exhausted and unchanged.

Total tokens are input plus output; cached input and reasoning are subsets and are not added again. Category rows aggregate three pairs each:

| Category | Auto total | Deep total | Auto output | Deep output |
| --- | ---: | ---: | ---: | ---: |
| Summary | 45,961 | 47,244 | 245 | 272 |
| Rewrite | 45,708 | 47,059 | 88 | 183 |
| Code explanation | 49,720 | 47,475 | 553 | 561 |
| Debugging | 49,686 | 47,506 | 616 | 561 |
| Architecture | 51,890 | 49,682 | 2,831 | 2,748 |
| Extraction | 47,847 | 46,978 | 91 | 91 |
| **All 18 cases** | **290,812** | **285,944** | **4,424** | **4,416** |

Aggregate auto total is **1.70% higher**, and median paired total-token reduction is **0.00%**. Aggregate elapsed times are 319,792 ms auto and 322,095 ms deep; these summed sequential observations are not a randomized latency or user-benefit study. Fast-category improvements do not justify selecting only favorable results; no general savings claim is established. Model/tier differences are part of this routing comparison, not evidence that a prompt compressor works. This read-only text calibration cannot replace the 30-task implementation benchmark, Responses API tests, fresh holdout or actual invoice measurement. Arms run auto then deep in fixed order, so cache/order effects are not isolated.

### Complete paired totals

| Case | Auto tier | Auto total | Deep total |
| --- | --- | ---: | ---: |
| plus-summary-001 | fast | 15,062 | 15,692 |
| plus-summary-002 | fast | 15,151 | 15,804 |
| plus-summary-003 | deep | 15,748 | 15,748 |
| plus-rewrite-001 | fast | 15,015 | 15,737 |
| plus-rewrite-002 | fast | 15,041 | 15,670 |
| plus-rewrite-003 | deep | 15,652 | 15,652 |
| plus-code-explanation-001 | balanced | 15,937 | 15,886 |
| plus-code-explanation-002 | balanced | 17,936 | 15,734 |
| plus-code-explanation-003 | deep | 15,847 | 15,855 |
| plus-debugging-001 | deep | 15,984 | 15,932 |
| plus-debugging-002 | deep | 15,786 | 15,784 |
| plus-debugging-003 | deep | 17,916 | 15,790 |
| plus-architecture-001 | deep | 18,896 | 16,709 |
| plus-architecture-002 | deep | 16,580 | 16,512 |
| plus-architecture-003 | deep | 16,414 | 16,461 |
| plus-extraction-001 | fast | 15,040 | 15,668 |
| plus-extraction-002 | fast | 17,169 | 15,672 |
| plus-extraction-003 | deep | 15,638 | 15,638 |

No raw prompt, answer or stderr was published or retained in the result journal. All human scores remain null, so this closes execution/usage coverage only, not semantic-quality acceptance. No paid API, release tag, public publication, local installation replacement or automatic price/savings policy change occurred. Further model execution requires new explicit authorization, not raising this cap or choosing another output path.

The safety implementation passed 327 local tests, configured lint and secret scanning, then all ten checks in [CI run 37951429441](https://github.com/Drippinblood333/layman/actions/runs/37951429441), including three OS tests, five standalone builds, Docker and release assembly. Publication was skipped. Human evaluation and participant acceptance remain required before release readiness can be claimed.
