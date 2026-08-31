#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Static safety ratchets for the release-heal publication order."""

import os
import pathlib
import re
import subprocess
import tempfile
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
            'if [ "$GITHUB_REF" != refs/heads/main ]',
            'tag="$(gh release view',
            "/actions/workflows/ci.yml/dispatches",
            ".head_sha == $oid",
            'if [ "$run_sha" != "$oid" ]',
            'if [ "$conclusion" != success ]',
            'if [ "$ci_passed" != true ]',
            "main moved after CI",
            'ref="refs/tags/${next}"',
            "/git/refs/tags/v1",
            'gh release create "$next"',
        ]
        cursor = -1
        for token in ordered:
            cursor = OPERATIONS.find(token, cursor + 1)
            self.assertNotEqual(cursor, -1, f"missing ordered operation: {token}")

    def test_ref_races_and_waits_fail_closed_with_a_bound(self):
        self.assertGreaterEqual(
            OPERATIONS.count('if [ "$remote_oid" != "$oid" ]'), 2
        )
        self.assertIn("for attempt in $(seq 1 180)", OPERATIONS)
        self.assertIn("sleep 5", OPERATIONS)
        self.assertIn("timed out waiting for successful CI", OPERATIONS)
        self.assertRegex(HEAL, r"timeout-minutes: 25\b")

    def test_dispatch_is_fresh_and_unique_to_the_caller_attempt(self):
        self.assertIn("release_heal_nonce:", CI)
        self.assertIn(
            "run-name: ci · ${{ inputs.release_heal_nonce || github.event_name }}",
            CI,
        )
        self.assertIn(
            'nonce="release-heal-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${oid}"',
            OPERATIONS,
        )
        self.assertIn('-f "inputs[release_heal_nonce]=${nonce}"', OPERATIONS)
        self.assertIn(".display_title == $title", OPERATIONS)
        self.assertIn("(.created_at | fromdateiso8601) >= $started", OPERATIONS)
        self.assertIn('[ "$run_title" != "$expected_title" ]', OPERATIONS)

    def test_numbered_tag_discovery_is_paginated_and_exact(self):
        discovery = re.search(
            r'numbered_refs="\$\((.*?)\n          \)"', OPERATIONS, re.DOTALL
        )
        self.assertIsNotNone(discovery)
        self.assertIn("gh api --paginate --slurp", discovery.group(1))
        self.assertIn("git/matching-refs/tags/v1.0.?per_page=100", discovery.group(1))
        self.assertIn(r'^refs/tags/v1\\.0\\.[0-9]+$', OPERATIONS)

    def test_numbered_tag_is_verified_around_release_creation(self):
        create = OPERATIONS.index('gh release create "$next"')
        before = OPERATIONS.rfind("assert_numbered_tag", 0, create)
        after = OPERATIONS.find("assert_numbered_tag", create)
        self.assertNotEqual(before, -1)
        self.assertNotEqual(after, -1)
        self.assertLess(before, create)
        self.assertGreater(after, create)

    def test_release_discovery_accepts_only_public_stable_releases(self):
        discovery = re.search(
            r'release_matches="\$\((.*?)\n          \)"', OPERATIONS, re.DOTALL
        )
        self.assertIsNotNone(discovery)
        self.assertIn(".draft == false", discovery.group(1))
        self.assertIn(".prerelease == false", discovery.group(1))
        self.assertIn(".body == $notes", discovery.group(1))
        self.assertIn(".immutable // false", discovery.group(1))

    def test_new_release_must_be_public_stable_immutable_and_exact(self):
        create = OPERATIONS.index('gh release create "$next"')
        immutable_check = OPERATIONS.index("new release ${next} is not public", create)
        check_body = OPERATIONS[create:immutable_check]
        for invariant in (
            ".tag_name == $tag",
            ".body == $notes",
            ".draft == false",
            ".prerelease == false",
            ".immutable == true",
        ):
            self.assertIn(invariant, check_body)

    def test_readme_only_recovery_proves_state_and_pushes_without_force(self):
        start = OPERATIONS.index('[ "$released_immutable" = true ]')
        dispatch = OPERATIONS.index("/actions/workflows/ci.yml/dispatches")
        recovery = OPERATIONS[start:dispatch]
        for proof in (
            '[ "$released_immutable" = true ]',
            ".draft == false",
            ".prerelease == false",
            ".immutable == true",
            'observed_numbered" != "$oid',
            'observed_floating" != "$oid',
            '.head_sha == $oid',
            '.conclusion == "success"',
            'git merge-base --is-ancestor "$oid" "$remote_oid"',
            'git show "${remote_oid}:action.yml"',
            'git switch --detach "$remote_oid"',
            "git push origin HEAD:main",
        ):
            self.assertIn(proof, recovery)
        self.assertNotIn("--force", recovery)
        self.assertLess(recovery.index("git commit -m"), recovery.rindex("observed_numbered="))
        self.assertLess(recovery.rindex("observed_numbered="), recovery.index("git push origin HEAD:main"))

    def test_reruns_reconcile_every_partial_surface(self):
        self.assertNotIn("default already $ver", OPERATIONS)
        self.assertIn('git log -1 --format=%H -- action.yml', OPERATIONS)
        for state in (
            'numbered_oid" = "$oid',
            'released_tag',
            'floating_oid" = "$oid',
            'grep -Fq "$readme_pin" README.md',
        ):
            self.assertIn(state, OPERATIONS)
        self.assertIn('if [ -z "$numbered_oid" ]', OPERATIONS)
        self.assertIn('if [ -z "$released_tag" ]', OPERATIONS)
        self.assertIn('if ! grep -Fq "$readme_pin" README.md', OPERATIONS)

    def test_readme_replacement_preserves_the_literal_at_sign(self):
        old = "supernovae-st/nika-action@" + "1" * 40 + " # v1.0.18\n"
        expected = "nika-action@" + "a" * 40 + " # v1.0.19"
        env = os.environ | {"README_PIN": expected}
        with tempfile.TemporaryDirectory() as directory:
            readme = pathlib.Path(directory) / "README.md"
            readme.write_text(old)
            subprocess.run(
                [
                    "perl",
                    "-pi",
                    "-e",
                    r"s/nika-action\@[a-f0-9]{40} # v1\.0\.[0-9]+/$ENV{README_PIN}/",
                    str(readme),
                ],
                check=True,
                env=env,
            )
            self.assertEqual(
                readme.read_text(),
                "supernovae-st/" + expected + "\n",
            )

    def test_main_ref_guard_precedes_every_mutation(self):
        guard = OPERATIONS.index('if [ "$GITHUB_REF" != refs/heads/main ]')
        first_edit = OPERATIONS.index("perl -pi")
        self.assertLess(guard, first_edit)

    def test_ci_executes_every_static_workflow_test(self):
        self.assertIn(
            "python3 -m unittest discover -s scripts -p 'test_*.py' -v",
            CI,
        )


if __name__ == "__main__":
    unittest.main()
