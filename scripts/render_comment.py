#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
#
# render_comment.py — `nika check --json` (+ optional mermaid graph + trace
# verify verdict) → one PR-comment markdown body. The honesty rules are the
# contract:
#
#   · cost is a FLOOR: render "≥ $X" — never a total, and an unpriced task is
#     NEVER $0 (usd:null → "unpriced", with its unbounded_reason verbatim)
#   · findings are aggregated DEFENSIVELY across every known finding-class
#     key (the report has 8+ sibling arrays and no unified findings[] yet —
#     engine issue #331); unknown report_version → minimal render + warning,
#     never a crash
#   · the body is budgeted: sections render in priority order into a hard
#     byte budget (GitHub caps comment bodies at 65536 chars); a section that
#     does not fit is replaced by one truncation line — the verdict line
#     always fits
#   · the comment is IDEMPOTENT per (marker, workflow path): the caller
#     upserts on the marker, so re-pushes edit one comment instead of
#     spamming the thread
#
# stdin/args in, markdown out. Zero dependencies beyond the stdlib.

import argparse
import json
import pathlib
import sys

MARKER_FMT = "<!-- nika-action:v1:{path} -->"
BUDGET = 60_000  # hard GitHub cap is 65536 — keep headroom for the upsert wrapper

# The finding-class keys check --json scatters findings across today
# (report_version 1). A 9th class appearing under a bumped report_version
# renders via the version guard, not silently dropped.
FINDING_KEYS = (
    "conformance", "gate_findings", "schema_findings", "schema_lints",
    "unknown_tools", "unknown_args", "missing_args",
    "secret_leaks", "secret_egresses", "capability_escapes",
)
KNOWN_REPORT_VERSIONS = {1}


def money(v) -> str:
    """Floor-honest money: None is unpriced, never $0."""
    if v is None:
        return "unpriced"
    return f"${v:,.2f}" if v >= 0.005 or v == 0 else f"${v:.4f}"


def finding_rows(report: dict) -> list:
    rows = []
    for key in FINDING_KEYS:
        for item in report.get(key) or []:
            if isinstance(item, dict):
                code = item.get("code") or item.get("rule") or key
                msg = (item.get("message") or item.get("summary")
                       or json.dumps(item, ensure_ascii=False))
            else:
                code, msg = key, str(item)
            rows.append((key, str(code), str(msg)))
    return rows


def sec_verdict(report: dict, check_exit: int, path: str) -> str:
    rows = finding_rows(report)
    clean = bool(report.get("clean")) and check_exit == 0
    icon = "✅" if clean else "❌"
    waves = report.get("waves") or []
    # cost.tasks only carries model-bearing tasks — the DAG task count is the
    # sum of wave sizes (each wave is an antichain of task indices)
    n_tasks = (sum(len(w) for w in waves) if waves
               else len((report.get("cost") or {}).get("tasks") or []))
    head = (f"{icon} **nika check** — "
            f"{'clean' if clean else f'{len(rows)} finding(s)'} · "
            f"`{path}` · {n_tasks} task(s) · {len(waves)} wave(s)")
    if clean or not rows:
        return head
    lines = [head, "", "| class | code | finding |", "|---|---|---|"]
    for key, code, msg in rows[:20]:
        msg = msg.replace("|", "\\|")
        lines.append(f"| {key} | `{code}` | {msg[:180]} |")
    if len(rows) > 20:
        lines.append(f"| … | … | +{len(rows) - 20} more finding(s) |")
    return "\n".join(lines)


def sec_cost(report: dict) -> str:
    cost = report.get("cost") or {}
    floor = cost.get("min_path_total_usd")
    bounded = cost.get("bounded_total_usd")
    unpriced = [t for t in cost.get("tasks") or [] if t.get("usd") is None]
    head = f"💰 **cost floor ≥ {money(floor if floor is not None else bounded)}**"
    if cost.get("has_unbounded"):
        head += f" · ⚠ {len(unpriced)} unpriced/unbounded task(s) — never rendered as $0"
    lines = [head]
    for t in unpriced[:8]:
        lines.append(f"- `{t.get('task')}` · {t.get('model') or 'model unset'} · "
                     f"unpriced ({t.get('unbounded_reason') or 'no list rate'})")
    if len(unpriced) > 8:
        lines.append(f"- … +{len(unpriced) - 8} more unpriced task(s)")
    return "\n".join(lines)


def sec_requirements(report: dict) -> str:
    req = report.get("requirements") or {}
    models = [m.get("model") for m in req.get("models") or []]
    secrets = req.get("secrets") or []
    env = req.get("env_reads") or []
    parts = []
    if models:
        parts.append("models: " + " · ".join(f"`{m}`" for m in models[:8]))
        # 0.99+ additive field: every model resolves in the installed binary.
        # Absent (0.98 reports) → say nothing rather than guess.
        resolve = report.get("models_resolve")
        if resolve is True:
            parts.append("all resolve in this engine")
        elif resolve is False:
            parts.append("⚠ **some models do not resolve in this engine** — "
                         "the check named them; `nika doctor` lists what runs")
    parts.append("secrets: " + (" · ".join(f"`{s}`" for s in secrets[:8]) if secrets else "none"))
    if env:
        parts.append("env reads: " + " · ".join(f"`{e}`" for e in env[:8]))
    return "🔐 **requires** — " + " · ".join(parts)


def sec_parallelism(report: dict) -> str:
    waves = report.get("waves") or []
    if not waves:
        return ""
    width = max(len(w) for w in waves)
    lines = [f"🌊 **schedule** — {len(waves)} wave(s), max width {width}"]
    if width > 1:
        lines.append(
            f"> budget note: `--max-cost-usd` stops NEW admissions — worst-case "
            f"overshoot is one full wave (≤ {width} task(s) beyond the cap at "
            f"the crossing). Tighten with `max_parallel:` when the budget is strict.")
    return "\n".join(lines)


def sec_graph(mermaid: str) -> str:
    if not mermaid.strip():
        return ""
    return ("<details><summary>🗺 DAG</summary>\n\n"
            "```mermaid\n" + mermaid.strip() + "\n```\n\n</details>")


def sec_trace(trace_verdict: str) -> str:
    if not trace_verdict.strip():
        return ""
    return f"🔗 **mock run** — {trace_verdict.strip()}"


def render(report: dict, check_exit: int, path: str, mermaid: str,
           trace_verdict: str, engine_version: str) -> str:
    rv = report.get("report_version")
    warn = ""
    if rv not in KNOWN_REPORT_VERSIONS:
        warn = (f"\n> ⚠ unknown `report_version: {rv}` — rendering the stable "
                f"subset only (this action knows {sorted(KNOWN_REPORT_VERSIONS)}).")
    # priority-ordered candidate sections; greedy fit inside the byte budget —
    # the verdict is index 0 and always fits by construction
    sections = [s for s in (
        sec_verdict(report, check_exit, path) + warn,
        sec_cost(report),
        sec_requirements(report),
        sec_parallelism(report),
        sec_trace(trace_verdict),
        sec_graph(mermaid),
    ) if s]
    footer = (f"\n---\n<sub>nika {engine_version} · report_version {rv} · "
              f"floor semantics: spend ≥ floor · "
              f"[what this checks](https://docs.nika.sh/reference/machine-surfaces)</sub>\n"
              f"{MARKER_FMT.format(path=path)}")
    budget = BUDGET - len(footer)
    out, used = [], 0
    for i, s in enumerate(sections):
        block = ("\n\n" if out else "") + s
        if used + len(block) <= budget:
            out.append(block)
            used += len(block)
        else:
            trunc = ("\n\n" if out else "") + f"> …section truncated (body budget) — see the workflow log."
            if used + len(trunc) <= budget:
                out.append(trunc)
                used += len(trunc)
            break
    return "".join(out) + footer


def render_parse_fatal(raw: str, check_exit: int, path: str,
                       engine_version: str) -> str:
    """check --json emitted non-JSON (the parse-fatal path — engine #331)."""
    body = raw.strip()[:2000]
    return (f"❌ **nika check** — parse failed · `{path}` (exit {check_exit})\n\n"
            f"```\n{body}\n```\n\n"
            f"---\n<sub>nika {engine_version} · non-JSON check output "
            f"(parse-fatal path)</sub>\n{MARKER_FMT.format(path=path)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-json", required=True,
                    help="path to the captured `nika check --json` stdout")
    ap.add_argument("--check-exit", type=int, required=True)
    ap.add_argument("--workflow", required=True, help="workflow path (display + marker)")
    ap.add_argument("--mermaid", default="", help="path to `nika graph --format mermaid` output")
    ap.add_argument("--trace-verdict", default="", help="one-line trace verify summary")
    ap.add_argument("--engine-version", default="unknown")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    raw = pathlib.Path(a.check_json).read_text(encoding="utf-8", errors="replace")
    mermaid = (pathlib.Path(a.mermaid).read_text(encoding="utf-8", errors="replace")
               if a.mermaid and pathlib.Path(a.mermaid).is_file() else "")
    try:
        report = json.loads(raw)
        body = render(report, a.check_exit, a.workflow, mermaid,
                      a.trace_verdict, a.engine_version)
    except json.JSONDecodeError:
        body = render_parse_fatal(raw, a.check_exit, a.workflow, a.engine_version)
    if len(body) > 65_000:  # belt over the budget's braces
        body = body[:64_000] + "\n> …hard-truncated.\n" + MARKER_FMT.format(path=a.workflow)
    pathlib.Path(a.out).write_text(body, encoding="utf-8")
    print(f"rendered {len(body)} chars → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
