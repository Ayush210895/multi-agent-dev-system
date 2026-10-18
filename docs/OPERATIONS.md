# Operations and Safety Boundary

## Default execution

The CLI now uses the SDK's `default` permission mode. Unattended edits require
the explicit `--allow-unattended-edits` flag or `CLAUDE_PERMISSION_MODE=acceptEdits`.
Generated applications must be reviewed before they are executed or deployed.

## Run evidence

Each run keeps:

- the original request;
- per-agent transcripts;
- `RUN_SUMMARY.md` for human review;
- `RUN_MANIFEST.json` with the request hash, model, permission mode, timing,
  success state, and agent-level failures.

## Production gates

Before using this pipeline in a shared environment:

1. Run generated code in an isolated container or sandbox.
2. Restrict network and filesystem access to the minimum required scope.
3. Scan generated dependencies and images for known vulnerabilities.
4. Require human approval before deployment, credential use, or destructive tools.
5. Benchmark task success, intervention rate, latency, and cost on a fixed suite.
6. Retain transcripts and manifests under an approved data-retention policy.
