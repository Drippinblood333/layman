# Optional brief offline plan — 2026-10-18

An actual CLI-plan payload for a small repair used 84 JSON lines including
repeated task/risk/workflow labels, nested routing reasons and timing diagnostics.
This is useful for integrations, but unnecessary for a beginner's first preview.

`layman plan --brief` now renders the same computed plan as actionable text:
offline/non-verified notice, stage/risk/mode, permissions, initial/expanded file
budgets, tool budget, every clarification question, every next step, every
acceptance criterion and every stop condition. It omits internal route diagnostics.
Default JSON, MCP responses, routing, original task, execution and permissions
remain unchanged. No model, third-party package or automatic rewrite is added.
The brief renderer is English like the existing CLI; clarification questions
retain their existing language. This is not a full localization change.

## Evidence

Four brief-mode tests failed first because the option did not exist; default JSON
control passed. After implementation, CLI/task-plan/MCP suites: **52 passed**.
Tests cover concrete repair, vague prompt, explicit read-only and high-risk tasks,
all required guidance, unchanged plan data and no execution. Ruff/Bandit passed;
Ruff's initial implicit-concatenation warning was corrected, not suppressed.

Same-plan UTF-8 payload measurements (temporary empty workspace, no trailing
print newline; route timing/path bytes can vary):

| Case | Full JSON bytes / lines | Brief bytes / lines |
|---|---:|---:|
| Concrete repair | 2719 / 84 | 782 / 16 |
| Vague project request | 2845 / 85 | 906 / 17 |
| Explicit read-only | 2541 / 82 | 635 / 14 |
| High-risk task | 2622 / 84 | 704 / 15 |

These are observed display bytes/lines, not token counts, API charges, task-quality
or usability-study results. The full JSON remains available when routing details
are needed. No native model invocation or user-install replacement occurred.
Hosted validation of the exact forthcoming source commit remains required.
