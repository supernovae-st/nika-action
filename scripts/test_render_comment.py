#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Unit tests for render_comment.py — fixtures are REAL captures from nika
# 0.98.0 (clean · broken-JSON NIKA-VAR-001 · parse-fatal non-JSON). Run:
#   python3 -m unittest scripts/test_render_comment.py -v

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import render_comment as rc

FIX = pathlib.Path(__file__).parent.parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


class Honesty(unittest.TestCase):
    def test_unpriced_is_never_zero_dollars(self):
        body = rc.render(load("check-clean.json"), 0, "f.nika.yaml", "", "", "0.98.0")
        self.assertIn("unpriced", body)
        # the unpriced task line must not carry a $ amount
        for line in body.splitlines():
            if "unpriced (" in line:
                self.assertNotIn("$", line)

    def test_cost_is_a_floor(self):
        body = rc.render(load("check-clean.json"), 0, "f.nika.yaml", "", "", "0.98.0")
        self.assertIn("cost floor ≥", body)
        self.assertNotIn("total cost", body.lower())

    def test_money_none_is_unpriced(self):
        self.assertEqual(rc.money(None), "unpriced")
        self.assertEqual(rc.money(0), "$0.00")


class Findings(unittest.TestCase):
    def test_broken_shows_code_and_fails(self):
        body = rc.render(load("check-broken.json"), 2, "b.nika.yaml", "", "", "0.98.0")
        self.assertIn("❌", body)
        self.assertIn("NIKA-VAR-001", body)

    def test_clean_exit_nonzero_is_not_clean(self):
        # exit code wins over the clean flag (belt over braces)
        body = rc.render(load("check-clean.json"), 2, "f.nika.yaml", "", "", "0.98.0")
        self.assertIn("❌", body)

    def test_unknown_report_version_warns_not_crashes(self):
        report = load("check-clean.json")
        report["report_version"] = 99
        body = rc.render(report, 0, "f.nika.yaml", "", "", "0.98.0")
        self.assertIn("report_version: 99", body)
        self.assertIn("⚠", body)


class ParseFatal(unittest.TestCase):
    def test_non_json_renders_fenced_error(self):
        raw = (FIX / "check-broken.txt").read_text()
        body = rc.render_parse_fatal(raw, 2, "p.nika.yaml", "0.98.0")
        self.assertIn("parse failed", body)
        self.assertIn("NIKA-PARSE-005", body)
        self.assertIn(rc.MARKER_FMT.format(path="p.nika.yaml"), body)


class Budget(unittest.TestCase):
    def test_verdict_survives_a_flooded_report(self):
        report = load("check-broken.json")
        # flood one finding class far past the budget
        report["gate_findings"] = [
            {"code": f"NIKA-X-{i:04}", "message": "y" * 400} for i in range(4000)
        ]
        body = rc.render(report, 2, "b.nika.yaml", "", "", "0.98.0")
        self.assertLessEqual(len(body), 65_000)
        self.assertIn("nika check", body.splitlines()[0])
        self.assertIn(rc.MARKER_FMT.format(path="b.nika.yaml"), body)

    def test_marker_is_per_path_idempotence_key(self):
        a = rc.render(load("check-clean.json"), 0, "a.nika.yaml", "", "", "0.98.0")
        b = rc.render(load("check-clean.json"), 0, "b.nika.yaml", "", "", "0.98.0")
        self.assertIn("nika-action:v1:a.nika.yaml", a)
        self.assertIn("nika-action:v1:b.nika.yaml", b)


class Sections(unittest.TestCase):
    def test_mermaid_wraps_in_details(self):
        body = rc.render(load("check-clean.json"), 0, "f.nika.yaml",
                         "graph TD\n  a --> b", "", "0.98.0")
        self.assertIn("```mermaid", body)
        self.assertIn("<details>", body)

    def test_task_count_comes_from_waves(self):
        body = rc.render(load("check-clean.json"), 0, "f.nika.yaml", "", "", "0.98.0")
        self.assertIn("3 task(s) · 3 wave(s)", body)

    def test_wave_width_note_only_when_parallel(self):
        report = load("check-clean.json")
        body = rc.render(report, 0, "f.nika.yaml", "", "", "0.98.0")
        self.assertNotIn("worst-case", body)  # width 1 → no overshoot note
        report["waves"] = [[0, 1], [2]]
        body = rc.render(report, 0, "f.nika.yaml", "", "", "0.98.0")
        self.assertIn("worst-case", body)     # width 2 → the bound appears


if __name__ == "__main__":
    unittest.main()

class ModelsResolve(unittest.TestCase):
    """0.99 additive field: present-true, present-false, absent (0.98)."""

    def _base(self):
        return load("check-clean.json")

    def test_absent_says_nothing(self):
        body = rc.render(self._base(), 0, "f.nika.yaml", "", "", "0.98.0")
        self.assertNotIn("resolve in this engine", body)

    def test_true_affirms(self):
        r = self._base()
        r["models_resolve"] = True
        body = rc.render(r, 0, "f.nika.yaml", "", "", "0.99.0")
        self.assertIn("all resolve in this engine", body)

    def test_false_warns_without_inventing_names(self):
        r = self._base()
        r["models_resolve"] = False
        body = rc.render(r, 0, "f.nika.yaml", "", "", "0.99.0")
        self.assertIn("do not resolve in this engine", body)
        self.assertIn("nika doctor", body)

