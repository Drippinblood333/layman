# Error recovery

## Codex no longer starts or rejects the provider

1. Stop Layman and run `layman codex disable --dry-run`.
2. Review the diff, then run `layman codex disable --apply`.
3. If the restore-state file is missing or a conflict is reported, list backups with `layman codex backups`.
4. Preview a selected backup with `layman codex restore <backup-path> --dry-run`.
5. Apply it only after review with `--apply`. A second safety backup is made first.

Disable never overwrites a `model`, `model_provider`, or Layman provider block changed after enablement. It reports the conflict and keeps the recovery state for manual resolution.

## Port 8787 is occupied

Run `layman doctor`. Either stop the stale process or set `LAYMAN_ROUTER_PORT` and update the Codex provider URL consistently. Do not bind the service to a LAN address outside an isolated container.

## API authentication errors

The key must exist in the environment of both Codex and the router launch context. `doctor` reports only `set` or `missing`; it never prints the value. A 401 is not retried or upgraded.

## Interrupted stream

Before the first SSE event, a retryable network/429/5xx/empty response may upgrade once. After output begins, the router emits a terminal stream error and does not replay the request, preventing duplicate text or tool actions.

## Corrupt or locked telemetry database

Stop the router and copy `~/.layman/usage.sqlite3` before repair. The service can start against a new path by setting `LAYMAN_ROUTER_DATABASE_PATH`; do not delete the original until its data is no longer needed.
