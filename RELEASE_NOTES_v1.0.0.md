# Layman 1.0.0

Layman 1.0.0 is the first intended public release and the internal v3 milestone. It is a Codex optimization and execution layer that helps beginners turn ideas into verified software and helps developers reduce unnecessary context, workflow, model, and output work.

The unified plugin includes `$layman`, `$layman-status`, `$layman-auto`, and `$layman-router`. The CLI adds `layman status`, `layman plan`, and `layman run`. Project inspection is bounded and content-free; it reports an evidence-based stage but never treats the presence of tests or CI as proof that a release gate passes.

ChatGPT Plus users do not need an API key for `$layman`, `$layman-auto`, or the capped subscription calibrations. `$layman-auto` launches an ephemeral child task rather than switching the active conversation model. Transparent API routing requires an OpenAI API key and remains Beta. The 60-call paired gate did not pass, so no fixed token-saving or measured API-dollar claim is made.

Before general availability, the release candidate must pass all automated gates, fresh-machine installation checks, the 36-call Plus calibration and invited-user acceptance with no unresolved P0/P1 issue.

The Windows release candidate probes Codex executables before selecting one, so a broken npm wrapper does not mask a healthy CLI bundled by a supported editor. Uninstall removes both the Layman plugin and its local marketplace before optional data purging. API cost estimates use the official 2026-07-30 GPT-5.6 standard prices and switch the full request to long-context rates above 272K input tokens.

The release wheel and source distribution include the complete Layman local marketplace, so package installs can run `layman setup` without a repository checkout. CI independently clean-installs both formats and verifies every bundled plugin file. GitHub Release publishing stages a flat allowlisted asset set so installer filenames and checksum entries stay identical.

The release also publishes a hash-locked runtime requirements file. The isolated publishing job installs it with `--require-hashes`, rejects dependency drift, and generates a CycloneDX SBOM containing the complete locked direct and transitive runtime set.

Standalone installers require the release `SHA256SUMS.txt` manifest and stop before extraction when verification fails. After installation, users restart Codex and open a new task to load the plugin and updated executable path.

The 2026-07-16 Plus calibration completed 36/36 calls with no answer text stored. Auto's API-price-table equivalent was 5.79% lower, while total latency was 14.43% higher. Because outputs were not retained, semantic quality review remains an open release gate.

The separate 30-task token benchmark completed 60 accepted calls. Layman passed 30/30 hidden validations versus Direct's 29/30, but increased paired median total tokens by 19.54%, output tokens by 47.00%, and median files read from 5 to 8. All four high-risk Layman tasks stayed Deep/Sol-high/read-only. Token optimization therefore ships as Experimental with an explicit negative result.

Layman 1.0 combines output, tool, workflow, skill-composition, routing, safety, and verification capabilities through its own modular control layer. It does not vendor code from Caveman, RTK, Spec Kit, Superpowers, or Claude Code Router; provenance requirements for future adapters are recorded in `THIRD_PARTY_NOTICES.md`.
