# Layman Skill v1 Release Notes

Release date: 2026-07-08

## Summary

Layman Skill v1 is the first repo-local MVP for turning vague software ideas and risky AI coding prompts into scoped, safe, verifiable coding-agent tasks.

The v1 release is Chinese-first bilingual and targets Codex, Claude Code, Cursor, and similar coding agents.

## Included

- Repo-local skill: `skills/layman-skill`
- Skill UI metadata: `skills/layman-skill/agents/openai.yaml`
- Five MVP scenarios:
  - Idea to MVP
  - Prompt audit
  - Safe task generation
  - New project handoff
  - Pre-release check
- Reference docs for risk scoring, task patterns, project stages, bad prompts, and release checks.
- Example outputs and smoke-test prompts.
- Deterministic release check script: `evals/check_release.py`
- Local release package: `dist/layman-skill-v1.zip`
- Package checksum: `dist/layman-skill-v1.zip.sha256`

## Not Included

- No CLI.
- No Web app.
- No account system.
- No installation into the user-level Codex skills directory.
- No scripts or assets inside the skill folder.
- No fixed token-saving percentage claim.

## Release Validation

Run:

```powershell
python C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\skills\layman-skill
python .\evals\check_release.py
python -m json.tool .\evals\prompts.json
```

Expected result:

- Skill validator passes.
- Release checks pass.
- `prompts.json` is valid JSON.

Observed result on 2026-07-08:

- `Skill is valid!`
- `Layman Skill v1 release checks passed.`
- `prompts.json valid`
- Package SHA256: `A9F1736B6754BD1A5E6BAAD4E53ABBB1F9F07742D7C82C55CA96F457FC7D1B84`

## Known Limitations

- Smoke tests are structural and rubric-based; they do not yet run a model-in-the-loop evaluation.
- This folder is not currently a git repository, so release tagging and commit verification are outside the current workspace state.
- v1 focuses on Skill behavior and examples, not automated project scanning.
