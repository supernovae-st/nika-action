<p align="center">
  <a href="https://nika.sh">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://nika.sh/brand/nika-logo-dark.svg">
      <img src="https://nika.sh/brand/nika-logo-light.svg" alt="Nika" width="220">
    </picture>
  </a>
</p>

<h1 align="center">supernovae-st/nika-action@v1</h1>

<p align="center">
  <strong>The <code>nika check</code> gate for pull requests: the verdict, the cost floor, the models and secrets, the DAG, as one sticky comment before anyone spends a token.</strong><br>
  Static and keyless by default; an offline golden lane on request; running workflows is never this action's job.
</p>

<p align="center">
  <a href="https://github.com/supernovae-st/nika-action/releases/latest"><img src="https://img.shields.io/github/v/release/supernovae-st/nika-action?label=release" alt="Latest release"></a>
  <a href="https://github.com/supernovae-st/nika-action/actions/workflows/ci.yml"><img src="https://github.com/supernovae-st/nika-action/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status"></a>
  <a href="https://github.com/supernovae-st/nika/releases/latest"><img src="https://img.shields.io/github/v/release/supernovae-st/nika?label=engine" alt="Engine release"></a>
  <a href="https://docs.nika.sh"><img src="https://img.shields.io/badge/docs-docs.nika.sh-8b8cf8.svg" alt="Documentation"></a>
</p>

<p align="center">
  <a href="https://scorecard.dev/viewer/?uri=github.com/supernovae-st/nika-action"><img src="https://api.scorecard.dev/projects/github.com/supernovae-st/nika-action/badge" alt="OpenSSF Scorecard"></a>
  <a href="https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/supernovae-st/nika-action"><img src="https://archive.softwareheritage.org/badge/origin/https://github.com/supernovae-st/nika-action/" alt="Archived by Software Heritage"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="Apache-2.0"></a>
</p>

## Thirty seconds, no API key

Paste this as `.github/workflows/nika.yml`:

```yaml
name: nika
on:
  pull_request:
    paths: ['**.nika', '.github/workflows/nika.yml']
permissions:
  contents: read
  pull-requests: write      # the sticky comment · without it the receipt lands in the step summary
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: supernovae-st/nika-action@v1
        with:
          workflow: flows/readme-summary.nika
          mode: check           # or: test · the offline golden lane, still no key
```

`@v1` tracks the latest v1.x.y. For production, pin the full commit SHA with
the release in a comment: the form Dependabot and Renovate bump, and the line
this repository's release bot re-points at every engine release:

```yaml
      - uses: supernovae-st/nika-action@cd9dac753bd1d4139192e5ab28e2c75dc84f193b # v1.0.23
```

Point `workflow:` at a `.nika` in the repository. This is the one the
replay below uses; `mock/echo` rehearses with no key and no network, and a
real seat in its place changes nothing about the check:

```yaml
nika: readme-summary
model: mock/echo            # no key, no network · or ollama/qwen3.5:4b, mistral/mistral-small-latest, …

permits:
  tools: ["nika:read"]
  fs: { read: ["README.md"] }

tasks:
  readme:
    invoke:
      tool: "nika:read"
      args: { path: "README.md" }
  summary:
    with: { readme: "${{ tasks.readme.output }}" }
    infer:
      prompt: "Summarize this README in three bullets:\n${{ with.readme }}"
      max_tokens: 200

outputs:
  summary: ${{ tasks.summary.output }}
```

No workflow yet? `nika compile hello hello.nika` writes the offline
lesson. For `chain`, preview with `nika compile chain --json` and answer
its questions with `--answer KEY=JSON_LITERAL` before naming a
destination; only Ready writes.

Open a pull request. The job downloads the pinned engine release, verifies the
tarball against the release's `SHA256SUMS`, runs `nika check --json` on the
file and posts the report as one sticky comment (and as the step summary).
GitHub Actions cannot be replayed on a laptop, so everything below was
replayed with the action's own scripts and the released engine
`nika 0.118.7 (f3a31a6ee)`, in a scratch repository holding the two files
above.

The install step, `scripts/install_nika.sh 0.118.7`, printed (the runner
picks its own platform asset):

```
nika-macos-arm64-0.118.7.tar.gz: OK
installed nika 0.118.7 (macos-arm64) → /tmp/readme-wave-action/runner/nika-bin/nika (SHA256 verified)
nika 0.118.7 (f3a31a6ee)
```

The check that gates the job is the one `nika check` prints locally; the job
keeps its JSON form and exits with the same code, 0 here. The closing lines
of the card:

```
 ✔ ORDER    no exec: sits downstream of a net-effecting task · unauthored content never reaches a shell
 ✔ PERMITS  literal + const: args fit the boundary · computed paths + symlinks are the RUN's verdict
 ✔ TRIFECTA no lethal trifecta over the declared permits: without a human gate
 ✔ JOURNEY internal · 1 source · 0 destinations · 1 model endpoint · no secret reaches an external destination
 ✔ audited · 2 tasks · 2 waves · permits tools:nika:read read:README.md · est out ≤$0.0000 · 0 hints · risk supervised
 layers · valid ✔ · access ready ✔ · capacity fit ✔ · run ready ✔
```

The comment the job posts, rendered by the action's `scripts/render_comment.py`
from that check's JSON and from `nika inspect --format mermaid` (GitHub draws
the DAG):

> ✅ **nika check** — clean · `flows/readme-summary.nika` · 2 task(s) · 2 wave(s)
>
> 💰 **cost floor ≥ $0.00**
>
> 🔐 **requires** — models: `mock/echo` · all resolve in this engine · secrets: none
>
> 🌊 **schedule** — 2 wave(s), max width 1
>
> <details><summary>🗺 DAG</summary>
>
> ```mermaid
> graph TD
>   readme["readme · invoke · nika:read"]:::invoke
>   summary["summary · infer · mock/echo"]:::infer
>   readme --> summary
>   classDef infer fill:#5b8cff22,stroke:#5b8cff,color:#5b8cff
>   classDef invoke fill:#22d3ee22,stroke:#22d3ee,color:#22d3ee
> ```
>
> </details>
> ---
> <sub>nika 0.118.7 · report_version 1 · floor semantics: spend ≥ floor · [what this checks](https://docs.nika.sh/reference/machine-surfaces)</sub>
> <!-- nika-action:v1:flows/readme-summary.nika -->

Every push re-renders the same comment in place; nothing is spent, no
provider is called, no key is read.

## Why this building

- **Audited before it runs.** The job is `nika check`: the order of effects,
  the permits, the lethal trifecta, the journey of every secret and the cost
  floor, judged on the file alone. A red check fails the job with the finding
  and its fix; nothing executes to find out.
- **Sovereign by default.** The engine is a checksum-verified release tarball
  running on your runner; the workflow file never leaves the repository. The
  same file targets local models (Ollama, llama.cpp, vLLM), Mistral, Hugging
  Face, OpenAI, xAI, Anthropic and the rest of the engine's catalog, and the
  check needs none of their keys.
- **Receipts, not reassurance.** Cost is a floor and is rendered as one; an
  unpriced task is never `$0`; the models and secrets a run would need are
  named; the DAG is drawn. Every figure comes from the engine's JSON, never
  from this action's prose.
- **One comment per file, forever.** Upserted by a hidden marker, so re-pushes
  edit it instead of spamming the thread. Fork pull requests degrade to the
  step summary; they never escalate.

<!-- engine hero pinned to the release tag it demonstrates · re-pin on lockstep bumps -->
![nika check audits a workflow on the released engine, then runs it](https://raw.githubusercontent.com/supernovae-st/nika/v0.118.7/media/nika-hero.gif)

## What it does, and what it refuses to

| lane | what runs | secrets |
|---|---|---|
| `check` (default) | `nika check --json` + `nika inspect --format mermaid`: static analysis, **nothing executes** | **none** |
| `test` | + `nika test` against `<file>.golden.json`: the **mock provider**, offline, deterministic | **none** |
| ~~run~~ | **not provided.** An unknown `mode` is refused by name. Executing workflows (which can carry `exec:` shell steps) under a CI token is a decision this action refuses to make for you: run lanes belong in your own steps, behind your own review, never on fork-origin events | none |

## When the check is red

The gate step exits with the check's own code (2 for findings) and the
comment carries the finding table. This repository's CI runs the action on
`fixtures/broken.nika`, a workflow that reads a task that does not
exist, and requires that failure; the same file on `nika 0.118.7` opens with:

```
 ✖ CONFORM  [NIKA-DAG-002] unknown dependency: task `use_ghost` depends on `ghost`, which does not exist
   fix: nika explain NIKA-DAG-002 · https://nika.sh/language/errors/NIKA-DAG-002
```

## The offline golden lane

`mode: test` adds `nika test`, which runs the workflow under the engine's mock
provider and compares the typed `outputs:` with `<file>.golden.json`, still
with no key. Write the golden once with `nika test <file> --update`, review
it, commit it; from then on the lane compares:

```sh
nika test flows/readme-summary.nika
```

```
✔ golden match · 1 key · 142B · flows/readme-summary.nika.golden.json
```

A missing golden skips the lane and says so in the receipt; a red golden is
rendered first and gates after, because receipts matter most when red.

## Security posture

- **The install is verified**: the release tarball is checked against the
  release's published `SHA256SUMS` before extraction. No bare `curl | tar`.
- **Zero secrets by default**: both lanes are static or offline. The action
  never reads provider keys.
- **Fork pull requests**: the default `GITHUB_TOKEN` on a fork `pull_request`
  is read-only, so the comment degrades to the **step summary**. Never wire
  this (or anything) through `pull_request_target` plus a checkout of the
  pull request's head: a `.nika` can declare `exec:` steps by design, so
  « run the PR's file under a privileged token » is code execution with your
  secrets.
- **One comment, forever**: upserted by a hidden per-file marker.
- **Pin this action by commit SHA**: shown above, and what this repository
  does to its own dependencies. Full posture: [SECURITY.md](SECURITY.md).

## Honesty semantics (why « receipts »)

- **The cost figure is a floor, not a total**: `spend ≥ floor`, rendered as
  `≥ $X`, always.
- **Unpriced is never $0**: a task with no list rate renders as `unpriced`
  with its reason verbatim (`NoTokenLimit`, an uncataloged model, …). A model
  the engine cannot price does not become free by omission.
- **The budget bound is stated, not hidden**: `--max-cost-usd` (in your own
  run lanes) stops *new* admissions. The worst-case overshoot is one full
  wave, `spend ≤ floor_checked + W · c_max`, where `W` is the max wave width
  the comment prints. Tighten with `max_parallel:` when the budget is strict.
- **Unknown `report_version`**: the comment renders the stable subset and says
  so. This action never guesses at fields it does not know.

## Inputs

| input | default | notes |
|---|---|---|
| `workflow` | required | path to the `.nika` (one file; matrix over paths for more) |
| `mode` | `check` | `check` \| `test` |
| `comment` | `true` | sticky PR comment (needs `pull-requests: write`) |
| `engine-version` | `0.120.2` | the engine release to install, verified against the release's `SHA256SUMS` |
| `native-strict` | `false` | fail while native-first hints remain (`nika check --native-strict`) |
| `github-token` | `github.token` | override for the comment upsert |

The default `engine-version` follows the engine's latest release: a scheduled
workflow in this repository (`release-heal.yml`) bumps it, tags the next
`v1.0.N` and moves `v1` once this repository's CI has passed on that exact
commit. Set it to hold an older release; whatever the value, the tarball is
downloaded from the engine's GitHub release and verified against its
`SHA256SUMS`.

## Outputs

| output | value |
|---|---|
| `check-exit` | exit code of `nika check` (0 clean · 2 findings) |
| `clean` | `true` / `false`, chainable in `if:` |
| `cost-floor` | static floor in USD; empty when unavailable, never a fake 0 |
| `cost-unbounded` | `true` when unpriced or unbounded tasks exist: a `0.0` floor with this `true` is not free, consume the pair, never the bare number |
| `comment-file` | path to the rendered markdown body |

```yaml
      - id: nika
        uses: supernovae-st/nika-action@v1
        with:
          workflow: flows/readme-summary.nika
      - run: echo "clean=${CLEAN} floor=${FLOOR} unbounded=${UNBOUNDED}"
        env:
          CLEAN: ${{ steps.nika.outputs.clean }}
          FLOOR: ${{ steps.nika.outputs.cost-floor }}
          UNBOUNDED: ${{ steps.nika.outputs.cost-unbounded }}
```

## More than one workflow file

`workflow` takes one path; fan out with a matrix, one sticky comment per
file, upserted independently:

```yaml
jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        flow: [flows/report.nika, flows/triage.nika]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: supernovae-st/nika-action@v1
        with:
          workflow: ${{ matrix.flow }}
```

## FAQ

**Does this run my workflow?** No, and there is deliberately no mode that
does. `check` is static; `test` runs the offline mock provider. Execution
belongs in your own steps, behind your own review.

**Does the job need my provider key?** No. The check is static, and a runner
without the key is not a finding: the same two-task file with
`mistral/mistral-small-latest` in place of `mock/echo`, checked on
`nika 0.118.7` with no key in the environment, still exits 0 with
`clean: true` and a priced floor (`cost floor ≥ $0.0001`), and its ACCESS
line reads:

```
 ✖ ACCESS   mistral/mistral-small-latest → no path on this machine · mistral · not_configured (access layer) · MISTRAL_API_KEY unset in process env
```

**Why did the comment land in the step summary instead?** Fork pull request:
the default token is read-only there. That is the designed degradation, not a
bug; never grant `pull_request_target` to force the comment.

**The cost line says `unpriced`: is that an error?** No. A task without a
list rate renders as unpriced with its reason, because a model the engine
cannot price does not become free by omission.

## Documentation

- [docs.nika.sh/integrations/everywhere](https://docs.nika.sh/integrations/everywhere) · every door in one page: install paths, IDEs, agents, skills, MCP, CI, SDKs
- [docs.nika.sh/integrations/quickstart](https://docs.nika.sh/integrations/quickstart) · the authoring quickstart
- [docs.nika.sh/reference/machine-surfaces](https://docs.nika.sh/reference/machine-surfaces) · what `nika check --json` carries, the report this action renders
- [github.com/supernovae-st/nika](https://github.com/supernovae-st/nika) · the engine (Rust, AGPL-3.0-or-later)
- [github.com/supernovae-st/nika-spec](https://github.com/supernovae-st/nika-spec) · the language (Apache-2.0)

## Development proof

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v   # the renderer and the release-heal ratchets, on captured fixtures
shellcheck scripts/*.sh
actionlint
```

The repository's CI runs three lanes: the unit tests above; a smoke lane that
installs the served default and requires every taught subcommand (`check`,
`test`, `inspect`, `new`) to answer `--help`; and an end-to-end lane in which
the action runs itself, `fixtures/flow.nika` must pass, `fixtures/broken.nika`
must fail, the golden lane must pass offline and `mode: run` must be refused.

<!-- city:map -->
## The city · where this repo sits

```text
📜 nika-spec ──── language law and conformance
    │
    ▼
⚙️ nika ───────── engine, admission, execution, receipts and schedules
    │
    ▼
🏭 nika-action ── this gate, used as supernovae-st/nika-action@v1: the engine's verdict on every pull request
    │
    ▼
🧩 any GitHub repository that keeps .nika files
```

This repository runs the engine's released binary and reports what it says.
It is not authoritative for the workflow language or for the engine: the
verdict is the binary's exit code and its JSON, never this action's prose.

All the buildings: [nika-spec](https://github.com/supernovae-st/nika-spec) ·
[nika](https://github.com/supernovae-st/nika) ·
[nika.sh](https://nika.sh) ·
[nika-docs](https://github.com/supernovae-st/nika-docs) ·
[nika-client](https://github.com/supernovae-st/nika-client) ·
[nika-vscode](https://github.com/supernovae-st/nika-vscode) ·
[nika-plugins](https://github.com/supernovae-st/nika-plugins) ·
[gh-nika](https://github.com/supernovae-st/gh-nika) ·
[homebrew-tap](https://github.com/supernovae-st/homebrew-tap) ·
[nika-action](https://github.com/supernovae-st/nika-action) ·
[nika-actions-starter](https://github.com/supernovae-st/nika-actions-starter) ·
[nika-registry](https://github.com/supernovae-st/nika-registry) ·
[nika-estate](https://github.com/supernovae-st/nika-estate).
<!-- /city:map -->

## License

[Apache-2.0](LICENSE): the adoption side of the Nika license split. The engine
this action downloads stays AGPL-3.0-or-later; invoking it as a subprocess
imposes nothing on your repository. Vulnerabilities: [SECURITY.md](SECURITY.md).
