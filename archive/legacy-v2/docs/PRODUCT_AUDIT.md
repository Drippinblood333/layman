# Product audit — 2026-07-16

## Fixed release blockers

- High-risk metadata bypass: `layman_route=fast` could override a high-risk route. Deep is now an unconditional safety floor.
- Codex tool inflation: any single advertised tool or `previous_response_id` forced routine work to balanced. Only tool-heavy requests now raise routine fast tasks; unknown tasks remain balanced.
- Circular evaluation: the previous 300 cases were six repeated templates aligned with keyword rules. The replacement suite contains adversarial and boundary variations.
- Cache-write double charging: cache-write tokens were charged once as uncached input and again at the write rate. They are now partitioned correctly.
- Unknown-model pricing: explicit unconfigured models previously inherited balanced pricing. Their cost is now marked unavailable rather than fabricated.
- Configuration recovery: writes were non-atomic and disable could clobber later user changes. Writes are atomic, conflicts are preserved, and scoped backup restore is available.
- Product operations: added doctor, token generation, retention pruning, recent/segmented usage APIs, installer scripts and a loopback dashboard.

The first adversarial run exposed 85 task/risk/route mismatches, including 25 under-routes. After the safety-floor, intent-priority, long-input and tool-heavy fixes, the same 300-case suite reports 0 mismatches with a 80 fast / 60 balanced / 160 deep distribution. This is rule-conformance evidence, not model-answer quality evidence.

## Residual release constraints

- A small real-API calibration does not prove the full 300-case quality gate.
- Model prices and capabilities are versioned configuration and must be checked against official OpenAI documentation for every release.
- Windows is the primary manual acceptance target; macOS, Linux and Docker require release-machine smoke tests.
- The project is not currently backed by Git metadata in this workspace, so signed tags and source provenance cannot be produced here.
