# Third-party notices

Layman 1.0 does not copy or vendor source code from the comparison projects below. They are credited because their public designs informed the capability boundaries described in the documentation.

| Project | Upstream | License | Layman 1.0 use |
|---|---|---|---|
| Caveman | https://github.com/JuliusBrussee/caveman | MIT | Design comparison only |
| RTK | https://github.com/rtk-ai/rtk | Apache-2.0 | Design comparison only; no Rust code included |
| Spec Kit | https://github.com/github/spec-kit | MIT | Workflow comparison only |
| Superpowers | https://github.com/obra/superpowers | MIT | Skill-composition comparison only |
| Claude Code Router | https://github.com/musistudio/claude-code-router | MIT | Routing-architecture comparison only |

Layman's runtime Python dependencies are listed in `services/layman-router/pyproject.toml` and the release SBOM. Their licenses remain those of their respective authors.

Before vendoring third-party source in a future release:

1. Pin an upstream commit.
2. Record every copied file and local modification here.
3. Retain required copyright, license, and NOTICE text.
4. Keep Apache-2.0 source under its original terms rather than relabeling it as MIT.
5. Review names and logos separately from source-code permissions.
