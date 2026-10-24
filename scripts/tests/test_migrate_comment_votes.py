"""Unit tests for the fail-closed comment vote migration."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.migrate_comment_votes import (
    MigrationBlocked,
    _validate_apply_arguments,
    analyze_snapshot,
    classify_table_state,
    _verify_merge_result,
)


class CommentVotePreflightTests(unittest.TestCase):
    def test_classifies_all_four_table_states(self):
        self.assertEqual(classify_table_state(set()), "none")
        self.assertEqual(classify_table_state({"comment_vote"}), "legacy_only")
        self.assertEqual(classify_table_state({"comment_votes"}), "canonical_only")
        self.assertEqual(
            classify_table_state({"comment_vote", "comment_votes"}), "both"
        )

    def test_same_vote_duplicates_are_reported_and_blocked(self):
        row = {"id": 1, "commentid": 7, "userid": 3, "vote_type": 1}
        report = analyze_snapshot(
            {"comment_vote"},
            {"comment_vote": [row, {**row, "id": 2}]},
            {7: (2, 0)},
            {7},
            {3},
        )

        self.assertEqual(report["state"], "legacy_only")
        self.assertEqual(len(report["tables"]["comment_vote"]["duplicate_business_keys"]), 1)
        self.assertIn("duplicate_business_key", report["blocking_findings"])

    def test_opposite_votes_in_one_legacy_table_are_a_hard_block(self):
        report = analyze_snapshot(
            {"comment_vote"},
            {
                "comment_vote": [
                    {"id": 1, "commentid": 7, "userid": 3, "vote_type": 1},
                    {"id": 2, "commentid": 7, "userid": 3, "vote_type": -1},
                ]
            },
            {7: (1, 1)},
            {7},
            {3},
        )

        self.assertIn("opposite_direction_conflict", report["hard_blocking_findings"])

    def test_dual_table_conflicts_and_primary_key_collisions_are_separate(self):
        report = analyze_snapshot(
            {"comment_vote", "comment_votes"},
            {
                "comment_vote": [
                    {"id": 1, "commentid": 7, "userid": 3, "vote_type": 1},
                    {"id": 2, "commentid": 8, "userid": 4, "vote_type": -1},
                ],
                "comment_votes": [
                    {"id": 3, "commentid": 7, "userid": 3, "vote_type": -1},
                    {"id": 2, "commentid": 9, "userid": 4, "vote_type": 1},
                ],
            },
            {7: (1, 0), 8: (0, 1), 9: (1, 0)},
            {7, 8, 9},
            {3, 4},
        )

        self.assertEqual(len(report["cross_table"]["opposite_direction_conflicts"]), 1)
        self.assertEqual(len(report["cross_table"]["primary_key_collisions"]), 1)
        self.assertIn("opposite_direction_conflict", report["blocking_findings"])
        self.assertIn("primary_key_collision", report["blocking_findings"])

    def test_orphans_invalid_types_and_count_deltas_are_reported(self):
        report = analyze_snapshot(
            {"comment_votes"},
            {
                "comment_votes": [
                    {"id": 1, "commentid": 7, "userid": 3, "vote_type": 0},
                    {"id": 2, "commentid": 99, "userid": 3, "vote_type": 1},
                    {"id": 3, "commentid": 7, "userid": 99, "vote_type": -1},
                ]
            },
            {7: (4, 0)},
            {7},
            {3},
        )

        table = report["tables"]["comment_votes"]
        self.assertEqual(len(table["invalid_vote_types"]), 1)
        self.assertEqual(len(table["orphan_comments"]), 1)
        self.assertEqual(len(table["orphan_users"]), 1)
        self.assertEqual(table["count_differences"][0]["agree_delta"], 4)
        self.assertIn("invalid_vote_type", report["blocking_findings"])
        self.assertIn("orphan_record", report["blocking_findings"])

    def test_count_differences_preserve_existing_comment_counts(self):
        report = analyze_snapshot(
            {"comment_votes"},
            {"comment_votes": [{"id": 1, "commentid": 7, "userid": 3, "vote_type": 1}]},
            {7: (5, 0)},
            {7},
            {3},
        )

        difference = report["tables"]["comment_votes"]["count_differences"][0]
        self.assertEqual(difference["stored_agreecount"], 5)
        self.assertEqual(difference["vote_agree_count"], 1)
        self.assertEqual(difference["agree_delta"], 4)
        self.assertIn("count_difference", report["blocking_findings"])

    def test_dual_table_logical_count_delta_deduplicates_same_vote(self):
        report = analyze_snapshot(
            {"comment_vote", "comment_votes"},
            {
                "comment_vote": [{"id": 1, "commentid": 7, "userid": 3, "vote_type": 1}],
                "comment_votes": [{"id": 2, "commentid": 7, "userid": 3, "vote_type": 1}],
            },
            {7: (1, 0)},
            {7},
            {3},
        )

        self.assertEqual(report["cross_table"]["logical_count_state"], "available")
        self.assertEqual(report["cross_table"]["logical_count_differences"], [])

    def test_apply_requires_matching_write_freeze_and_verified_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = Path(directory) / "sandbox.sql"
            backup.write_bytes(b"isolated backup")
            args = SimpleNamespace(
                run_id="iter21-sandbox",
                writes_frozen_run_id="different-run",
                backup_file=str(backup),
                backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
                backup_restore_verified=True,
                preserve_comment_counts=True,
                approved_preflight_sha256="a" * 64,
                approval_file="approval.json",
            )

            with self.assertRaises(MigrationBlocked):
                _validate_apply_arguments(args)

    def test_merge_verification_checks_copied_rows_and_preserved_fingerprints(self):
        source = {
            "id": 12,
            "commentid": 7,
            "userid": 3,
            "vote_type": 1,
            "createtime": "2026-10-23 10:00:00",
        }
        before = {
            "source_table_sha256": "source",
            "comment_counts_sha256": "counts",
            "user_ids_sha256": "users",
            "source_rows": [source],
            "canonical_rows": [],
        }
        after = {
            **before,
            "hard_blocking_findings": [],
            "canonical_rows": [source],
        }
        _verify_merge_result(
            before,
            after,
            [
                {
                    "source_id": 12,
                    "target_id": 12,
                    "commentid": 7,
                    "userid": 3,
                }
            ],
        )

    def test_merge_verification_preserves_source_vote_after_approved_id_remap(self):
        source = {
            "id": 1,
            "commentid": 7,
            "userid": 3,
            "vote_type": 1,
            "createtime": "2026-10-23 10:00:00",
        }
        existing = {
            "id": 1,
            "commentid": 8,
            "userid": 4,
            "vote_type": -1,
            "createtime": "2026-10-23 10:01:00",
        }
        remapped = {**source, "id": 2}
        before = {
            "source_table_sha256": "source",
            "comment_counts_sha256": "counts",
            "user_ids_sha256": "users",
            "source_rows": [source],
            "canonical_rows": [existing],
        }
        after = {
            **before,
            "hard_blocking_findings": [],
            "canonical_rows": [existing, remapped],
        }

        _verify_merge_result(
            before,
            after,
            [
                {
                    "source_id": 1,
                    "target_id": 2,
                    "commentid": 7,
                    "userid": 3,
                    "action": "reassigned",
                }
            ],
        )

    def test_merge_verification_rejects_counter_or_source_changes(self):
        source = {
            "id": 12,
            "commentid": 7,
            "userid": 3,
            "vote_type": -1,
            "createtime": "2026-10-23 10:00:00",
        }
        before = {
            "source_table_sha256": "source",
            "comment_counts_sha256": "counts",
            "user_ids_sha256": "users",
            "source_rows": [source],
            "canonical_rows": [],
        }
        after = {
            **before,
            "comment_counts_sha256": "changed-counts",
            "hard_blocking_findings": [],
            "canonical_rows": [source],
        }

        with self.assertRaises(MigrationBlocked):
            _verify_merge_result(
                before,
                after,
                [{"source_id": 12, "target_id": 12, "commentid": 7, "userid": 3}],
            )


if __name__ == "__main__":
    unittest.main()
