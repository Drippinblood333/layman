# Project Stages

Use this model to choose the next smallest useful step.

## Stage 0: Idea

Goal: turn a vague thought into a bounded MVP.

Output:

- Target user.
- Core job or use case.
- First version scope.
- Explicit non-goals.
- First coding-agent prompt.

Do not choose architecture, payments, accounts, or deployment unless the MVP requires them.

## Stage 1: MVP Definition

Goal: make the first buildable plan.

Output:

- Feature list capped to the smallest useful version.
- Data model or content model.
- Page, route, command, or API sketch.
- Development phases.
- Acceptance criteria for phase 1.

## Stage 2: Build

Goal: implement one feature slice at a time.

Rules:

- Start with existing project structure.
- Keep each task reviewable.
- Prefer existing dependencies and conventions.
- Verify after each slice.

## Stage 3: Stabilization

Goal: turn a demo into something dependable.

Check:

- Error states.
- Empty states.
- Loading states.
- Input validation.
- Data persistence.
- Tests or manual verification.

## Stage 4: Release

Goal: prepare the project for real users.

Check:

- Build command passes.
- Environment variables are documented.
- README explains setup and usage.
- Deployment target is chosen.
- No secrets, debug logs, or unsafe defaults remain.

## Stage 5: Maintenance

Goal: keep the project understandable and changeable.

Check:

- Known limitations are documented.
- Next tasks are prioritized.
- Bug reports can be reproduced.
- Broad refactors are separated from feature work.
