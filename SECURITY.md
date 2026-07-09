# Security

## Reporting

Please report vulnerabilities privately via
[GitHub security advisories](https://github.com/supernovae-st/nika-action/security/advisories/new)
— not in public issues. You'll get an acknowledgment within 72 hours.

## What this action does and does not do

- **Static by default.** The `check` lane parses your workflow file and
  renders a report. No workflow executes, no provider is called, no secret
  is read. The `test` lane runs `nika test` against the offline mock
  provider — still zero keys.
- **There is no run lane.** An unknown `mode` is refused by name. Executing
  workflows belongs in your own job steps, deliberately.
- **Checksum-verified install.** The engine binary is downloaded from the
  pinned GitHub release and verified against the release's `SHA256SUMS`
  before it runs (fail-closed). Pin the action itself by full SHA for the
  strongest supply-chain posture:
  `uses: supernovae-st/nika-action@<commit-sha> # v1.0.2`.
- **Fork PRs degrade, never escalate.** The default fork token is
  read-only: the sticky comment falls back to the step summary. Do not
  grant `pull_request_target` to work around this — the README says the
  same, on purpose.
- **Verification is transfer-integrity today.** `SHA256SUMS` ships in the
  same release as the tarball (trust-on-first-use per release). Signed
  provenance is tracked upstream on the engine's trust roadmap.

## Supported versions

The `v1` major tag tracks the latest v1.x.y release. Older tags stay
available but only the newest v1 receives fixes.
