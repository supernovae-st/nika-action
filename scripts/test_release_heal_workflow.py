#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Static safety ratchets for the release-heal publication order."""

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).parent.parent
HEAL = (ROOT / ".github/workflows/release-heal.yml").read_text()
CI = (ROOT / ".github/workflows/ci.yml").read_text()
OPERATIONS = "\n".join(
    line for line in HEAL.splitlines() if not line.lstrip().startswith("#")
)


class ReleaseHealGate(unittest.TestCase):
    def test_permissions_are_only_the_two_required_write_scopes(self):
        match = re.search(r"^permissions:\n((?:  [^\n]+\n)+)", HEAL, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(
            set(match.group(1).splitlines()),
            {"  actions: write", "  contents: write"},
        )

    def test_exact_sha_ci_success_precedes_every_publication_mutation(self):
        ordered = [
            "git push",
            'oid="$(git rev-parse HEAD)"',
            "/actions/workflows/ci.yml/dispatches",
            ".head_sha == $oid",
            'if [ "$run_sha" != "$oid" ]',
            'if [ "$conclusion" != success ]',
            'if [ "$ci_passed" != true ]',
            'ref="refs/tags/${next}"',
            "/git/refs/tags/v1",
            'gh release create "$next"',
        ]
        positions = [OPERATIONS.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_ref_races_and_waits_fail_closed_with_a_bound(self):
        self.assertIn('if [ "$remote_oid" != "$oid" ]', OPERATIONS)
        self.assertIn("for attempt in $(seq 1 180)", OPERATIONS)
        self.assertIn("sleep 5", OPERATIONS)
        self.assertIn("timed out waiting for successful CI", OPERATIONS)
        self.assertRegex(HEAL, r"timeout-minutes: 25\b")

    def test_ci_executes_every_static_workflow_test(self):
        self.assertIn(
            "python3 -m unittest discover -s scripts -p 'test_*.py' -v",
            CI,
        )


if __name__ == "__main__":
    unittest.main()
