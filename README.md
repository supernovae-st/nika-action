<p align="center">
  <a href="https://nika.sh">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://nika.sh/brand/nika-logo-dark.svg">
      <img src="https://nika.sh/brand/nika-logo-light.svg" alt="Nika" width="220">
    </picture>
  </a>
</p>

# nika-action · plan with receipts

[![ci](https://github.com/supernovae-st/nika-action/actions/workflows/ci.yml/badge.svg)](https://github.com/supernovae-st/nika-action/actions/workflows/ci.yml)

Static pre-flight for [Nika](https://github.com/supernovae-st/nika) workflows
in CI: when a PR touches a `.nika.yaml`, this action posts **what the change
would do before anyone runs it** — the `nika check` verdict, an honest cost
floor, the models and secrets it needs, its egress statics, and the DAG
(rendered natively by GitHub):

> ✅ **nika check** — clean · `flows/report.nika.yaml` · 3 task(s) · 3 wave(s)
> 💰 **cost floor ≥ $0.12** · ⚠ 1 unpriced task — never rendered as $0
> 🔐 **requires** — models: `ollama/qwen3.5:4b` · secrets: `OPENAI_API_KEY`
> 🌊 **schedule** — 3 wave(s), max width 1
> 🗺 DAG *(collapsible mermaid)*

```yaml
name: nika
on:
  pull_request:
    paths: ['**.nika.yaml']   # fire only when a workflow file changes
permissions:
  contents: read
  pull-requests: write        # the sticky comment — drop it and the body
                              # lands in the step summary instead
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: supernovae-st/nika-action@e90a55b5436f1d41f5dfe9b80af9970a7cca2fe7 # v1.0.2
        with:
          workflow: flows/report.nika.yaml
          mode: check           # or: test (offline mock golden lane)
```

The pin is the full commit SHA with the release in a comment — the form
Dependabot and Renovate bump for you. `@v1` also works and tracks the
latest v1.x.y.

No workflow yet? `nika new flows/report.nika.yaml --from chain` scaffolds
one ([authoring in 10 minutes](https://docs.nika.sh/integrations/quickstart))
— or start from this repo's own [`fixtures/flow.nika.yaml`](fixtures/flow.nika.yaml),
which is what the CI checks against itself.

## What it does — and refuses to do

| lane | what runs | secrets |
|---|---|---|
| `check` (default) | `nika check --json` + `nika graph` — static analysis, **nothing executes** | **none** |
| `test` | + `nika test` against `<file>.golden.json` — the **mock provider**, offline, deterministic | **none** |
| ~~run~~ | **not provided.** Executing workflows (which can carry `exec:` shell steps) under a CI token is a decision this action refuses to make for you — run lanes belong in your own workflow, behind your own review, never on fork-origin events | — |

## Security posture (the boring contract)

- **The install is verified**: the release tarball is checked against the
  release's published `SHA256SUMS` before extraction. No bare `curl | tar`.
- **Zero secrets by default**: both lanes are static/offline. The action
  never reads provider keys.
- **Fork PRs**: the default `GITHUB_TOKEN` on a fork `pull_request` is
  read-only — the comment degrades to the **step summary** automatically.
  **Never** wire this (or anything) via `pull_request_target` + a checkout
  of the PR head: a `.nika.yaml` can declare `exec:` steps by design, so
  "run the PR's file under a privileged token" is code execution with your
  secrets. Same-repo PRs get the sticky comment; forks get the summary.
- **One comment, forever**: the comment is upserted by a hidden per-file
  marker — re-pushes edit it in place, never spam the thread.
- **Pin this action by commit SHA** — demonstrated in the usage block
  above, and what we do to nika itself inside. Full posture: [SECURITY.md](SECURITY.md).

## Honesty semantics (why "receipts")

- **The cost figure is a floor, not a total**: `spend ≥ floor`. Rendered as
  `≥ $X`, always.
- **Unpriced is never $0**: a task with no list rate renders as `unpriced`
  with its reason verbatim (`NoTokenLimit`, uncataloged model, …). A model
  the engine cannot price does not become free by omission.
- **The budget bound is stated, not hidden**: `--max-cost-usd` (in your own
  run lanes) stops *new* admissions — the worst-case overshoot is one full
  wave: `spend ≤ floor_checked + W · c_max`, where `W` is the max wave width
  the comment prints. Tighten with `max_parallel:` when the budget is strict.
- **Unknown `report_version`** → the comment renders the stable subset and
  says so. This action never guesses at fields it does not know.

## Inputs

| input | default | notes |
|---|---|---|
| `workflow` | — | path to the `.nika.yaml` (one file; matrix over paths for more) |
| `mode` | `check` | `check` \| `test` |
| `comment` | `true` | sticky PR comment (needs `pull-requests: write`) |
| `engine-version` | `0.99.0` | the nika release to install (checksum-verified) |
| `native-strict` | `false` | fail while native-first hints remain |
| `github-token` | `github.token` | override for the comment upsert |

## Outputs

`check-exit` (0 clean · 2 findings) · `clean` (`true`/`false` — chainable in
`if:`) · `cost-floor` (static floor in USD · empty when unavailable, never a
fake 0) · `cost-unbounded` (`true` when unpriced/unbounded tasks exist — a
0.0 floor with this true is NOT free; consume the pair, never the bare
number) · `comment-file` (rendered markdown path).

## More than one workflow file

`workflow` takes one path; fan out with a matrix — one sticky comment per
file, upserted independently:

```yaml
jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        flow: [flows/report.nika.yaml, flows/triage.nika.yaml]
    steps:
      - uses: actions/checkout@v4
      - uses: supernovae-st/nika-action@v1
        with:
          workflow: ${{ matrix.flow }}
```

## FAQ

**Does this run my workflow?** No — and there is deliberately no mode that
does. `check` is static; `test` runs the offline mock provider. Execution
belongs in your own steps, behind your own review.

**Why did the comment land in the step summary instead?** Fork PR — the
default token is read-only there. That's the designed degradation, not a
bug; never grant `pull_request_target` to force the comment.

**The cost line says `unpriced` — is that an error?** No: a task without a
list rate renders as unpriced with its reason, because a model the engine
cannot price does not become free by omission.

## Links

- Engine: [github.com/supernovae-st/nika](https://github.com/supernovae-st/nika) (Rust, AGPL-3.0-or-later)
- Language spec: [github.com/supernovae-st/nika-spec](https://github.com/supernovae-st/nika-spec) (Apache-2.0)
- Docs: [docs.nika.sh](https://docs.nika.sh)

## License

[Apache-2.0](LICENSE) — the adoption side of the Nika license split. The
engine this action downloads stays AGPL-3.0-or-later; invoking it as a
subprocess imposes nothing on your repository.

🦋 SuperNovae Studio · Paris
