# Layman Router v2.1 RC offline test report

Date: 2026-07-16  
Platform: Windows, Python 3.14 test environment  
API boundary: `OPENAI_API_KEY` was removed from every test subprocess. No OpenAI Responses API request was made.

## Results

- Unit and integration tests: 29 passed.
- Routing matrix: 300/300 passed; 80 fast, 60 balanced, 160 deep.
- Routing stress run: 15,000 classifications at approximately 2,213 routes/second.
- Annotated routing mismatches: 0; high-risk under-routes: 0.
- Ruff static checks: passed.
- Bandit medium/high severity scan: passed.
- Locked dependency audit: no known vulnerabilities.
- Layman Skill v1 and Router v2 release gates: passed.
- Codex plugin and bundled Skill validation: passed.
- JavaScript syntax check: passed.

## Codex compatibility probe

The probe used an isolated temporary `CODEX_HOME`, fake credentials and a local fake Responses server. It captured a Codex request with:

- `model: auto`;
- streaming enabled;
- tools present;
- instructions present;
- Codex exit code 0.

The first invocation used the ambiguous Windows `codex` command and was denied by a protected executable path. Re-running with the explicit npm path `C:\Users\Administrator\AppData\Roaming\npm\codex.cmd` passed. The real user `config.toml` hash was unchanged and no Layman restore-state file was created.

## Release and dashboard verification

- Wheel version: 0.3.0.
- Wheel, source distribution and plugin ZIP were reproducible across two consecutive builds.
- The wheel installed successfully into a clean temporary virtual environment.
- The installed package served the offline dashboard successfully.
- Demo mode loaded 36 synthetic records across fast, balanced and deep tiers.
- Dashboard HTML, CSS and JavaScript assets loaded successfully.
- Demo mode returned HTTP 403 for `/v1/responses`, preventing accidental upstream API calls.
- Temporary processes and test directories were removed after verification.

## Not covered without external credentials or platforms

- Real OpenAI answer quality, latency, usage and measured savings.
- Live fallback behavior against actual OpenAI 429/5xx responses.
- macOS, Linux and Docker runtime acceptance; Docker and a POSIX shell were unavailable on this machine.

This report qualifies the build as an offline-tested release candidate, not a generally available release with measured cost-savings claims.
