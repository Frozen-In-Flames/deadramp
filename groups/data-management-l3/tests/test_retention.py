"""Retention-policy tests.

Traces to: Core functions -- Retention policies, Retention due;
contract for ``set_retention_policy`` /
``update_retention_policy`` / ``get_retention_policy`` /
``retention_policy_for`` / ``list_retention_policies`` /
``retention_due``; SI-10, AC-3. Failed operations must consume no
ids. Due computation is deterministic: a policy's reference time is
the dataset's latest completed ingestion created_utc (else the
dataset's created_utc); a non-legal-hold policy is due when
(now - reference).days > retention_days. Tests pass an explicit
``now`` (reference + N days, ISO string) so ages are exact.
"""

import unittest
from datetime import datetime, timedelta

from datamgmt_helpers import STEWARD, VIEWER, fresh_store, make_store
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError


def _parse(ts):
    """Core: Retention. Timestamps parse as ISO-8601."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _iso(dt):
    """Core: Retention. Datetime -> ISO string for explicit now arguments."""
    return dt.isoformat().replace("+00:00", "Z")


class TestSetRetentionPolicy(unittest.TestCase):
    """Core: Retention -- set/get/list."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_set_shape(self):
        """Core: Retention. A new policy carries rp-1, dataset, days, disposition, legal_hold False."""
        policy = self.store.set_retention_policy(self.dataset["id"], 365, "archive", STEWARD)
        self.assertEqual(policy["id"], "rp-1")
        self.assertEqual(policy["dataset_id"], self.dataset["id"])
        self.assertEqual(policy["retention_days"], 365)
        self.assertEqual(policy["disposition"], "archive")
        self.assertFalse(policy["legal_hold"])
        self.assertIn("created_utc", policy)

    def test_set_legal_hold_true(self):
        """Core: Retention. legal_hold=True is preserved on the policy."""
        policy = self.store.set_retention_policy(
            self.dataset["id"], 365, "review", STEWARD, legal_hold=True
        )
        self.assertTrue(policy["legal_hold"])

    def test_all_dispositions_accepted(self):
        """Core: Retention. disposition in {delete, archive, review} is accepted."""
        for i, disp in enumerate(("delete", "archive", "review")):
            with self.subTest(disposition=disp):
                ds = self.store.create_dataset("D-%s" % disp, "d", STEWARD)
                policy = self.store.set_retention_policy(ds["id"], 30, disp, STEWARD)
                self.assertEqual(policy["disposition"], disp)

    def test_bad_disposition_rejected_no_id(self):
        """Core: Retention (SI-10). Bad disposition -> ValidationError and no id consumed."""
        with self.assertRaises(ValidationError):
            self.store.set_retention_policy(self.dataset["id"], 30, "shred", STEWARD)
        policy = self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        self.assertEqual(policy["id"], "rp-1")

    def test_bad_retention_days_rejected_no_id(self):
        """Core: Retention (SI-10). retention_days 0/negative/non-int -> ValidationError, no id consumed."""
        for bad in (0, -10, "365", 1.5):
            with self.subTest(retention_days=bad):
                with self.assertRaises(ValidationError):
                    self.store.set_retention_policy(self.dataset["id"], bad, "delete", STEWARD)
        policy = self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        self.assertEqual(policy["id"], "rp-1")

    def test_unknown_dataset_not_found(self):
        """Core: Retention. Setting a policy for an unknown dataset -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.set_retention_policy("ds-999", 30, "delete", STEWARD)

    def test_duplicate_policy_for_dataset_rejected_no_id(self):
        """Core: Retention (SI-10). A second policy for the same dataset -> ValidationError, no id consumed."""
        self.store.set_retention_policy(self.dataset["id"], 365, "archive", STEWARD)
        with self.assertRaises(ValidationError):
            self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        other = self.store.create_dataset("Other", "d", STEWARD)
        policy = self.store.set_retention_policy(other["id"], 30, "delete", STEWARD)
        self.assertEqual(policy["id"], "rp-2")

    def test_get_and_policy_for(self):
        """Core: Retention. get_retention_policy round-trips; retention_policy_for returns the policy or None."""
        self.assertIsNone(self.store.retention_policy_for(self.dataset["id"], actor=VIEWER))
        policy = self.store.set_retention_policy(self.dataset["id"], 365, "archive", STEWARD)
        self.assertEqual(self.store.get_retention_policy(policy["id"], VIEWER)["id"], "rp-1")
        self.assertEqual(
            self.store.retention_policy_for(self.dataset["id"], actor=VIEWER)["id"], "rp-1"
        )
        with self.assertRaises(NotFoundError):
            self.store.get_retention_policy("rp-999", STEWARD)

    def test_list_policies(self):
        """Core: Retention. list_retention_policies returns all policies in id order, viewer-readable."""
        self.store.set_retention_policy(self.dataset["id"], 365, "archive", STEWARD)
        other = self.store.create_dataset("Other", "d", STEWARD)
        self.store.set_retention_policy(other["id"], 30, "delete", STEWARD)
        self.assertEqual(
            [p["id"] for p in self.store.list_retention_policies(actor=VIEWER)],
            ["rp-1", "rp-2"],
        )

    def test_viewer_set_denied_no_id(self):
        """Core: Retention (AC-3). Viewer set -> PermissionDenied and no id consumed."""
        with self.assertRaises(PermissionDenied):
            self.store.set_retention_policy(self.dataset["id"], 30, "delete", VIEWER)
        policy = self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        self.assertEqual(policy["id"], "rp-1")


class TestUpdateRetentionPolicy(unittest.TestCase):
    """Core: Retention -- update_retention_policy."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()
        self.policy = self.store.set_retention_policy(
            self.dataset["id"], 365, "archive", STEWARD
        )

    def test_update_fields(self):
        """Core: Retention. update changes retention_days, disposition and legal_hold."""
        updated = self.store.update_retention_policy(
            self.policy["id"], STEWARD, retention_days=90,
            disposition="review", legal_hold=True,
        )
        self.assertEqual(updated["retention_days"], 90)
        self.assertEqual(updated["disposition"], "review")
        self.assertTrue(updated["legal_hold"])

    def test_update_partial(self):
        """Core: Retention. A partial update leaves the other fields unchanged."""
        updated = self.store.update_retention_policy(
            self.policy["id"], STEWARD, retention_days=90
        )
        self.assertEqual(updated["disposition"], "archive")
        self.assertFalse(updated["legal_hold"])

    def test_update_bad_values_rejected_unchanged(self):
        """Core: Retention (SI-10). Bad retention_days/disposition on update -> ValidationError, policy unchanged."""
        with self.assertRaises(ValidationError):
            self.store.update_retention_policy(self.policy["id"], STEWARD, retention_days=0)
        with self.assertRaises(ValidationError):
            self.store.update_retention_policy(self.policy["id"], STEWARD, disposition="shred")
        after = self.store.get_retention_policy(self.policy["id"], STEWARD)
        self.assertEqual(after["retention_days"], 365)
        self.assertEqual(after["disposition"], "archive")

    def test_update_unknown_not_found(self):
        """Core: Retention. Updating an unknown policy -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.update_retention_policy("rp-999", STEWARD, retention_days=1)

    def test_update_viewer_denied(self):
        """Core: Retention (AC-3). Viewer update -> PermissionDenied, policy unchanged."""
        with self.assertRaises(PermissionDenied):
            self.store.update_retention_policy(self.policy["id"], VIEWER, retention_days=1)
        self.assertEqual(
            self.store.get_retention_policy(self.policy["id"], STEWARD)["retention_days"], 365
        )


class TestRetentionDue(unittest.TestCase):
    """Core: Retention -- retention_due computation."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_due_after_retention_with_ingestion_reference(self):
        """Core: Retention due. Policy 30d; now = latest completed ingestion created + 40d -> due, age_days 40."""
        ing = self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD, record_count=10
        )
        policy = self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        now = _iso(_parse(ing["created_utc"]) + timedelta(days=40))
        due = self.store.retention_due(actor=STEWARD, now=now)
        self.assertEqual(len(due), 1)
        entry = due[0]
        self.assertEqual(entry["dataset_id"], self.dataset["id"])
        self.assertEqual(entry["policy_id"], policy["id"])
        self.assertEqual(entry["disposition"], "delete")
        self.assertFalse(entry["legal_hold"])
        self.assertEqual(entry["reference_utc"], ing["created_utc"])
        self.assertEqual(entry["age_days"], 40)

    def test_not_yet_due(self):
        """Core: Retention due. now = reference + 10d for a 30d policy -> not due."""
        ing = self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD, record_count=10
        )
        self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        now = _iso(_parse(ing["created_utc"]) + timedelta(days=10))
        self.assertEqual(self.store.retention_due(actor=STEWARD, now=now), [])

    def test_exactly_at_retention_not_due(self):
        """Core: Retention due. Age exactly retention_days is not > retention_days, so not due."""
        ing = self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD, record_count=10
        )
        self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        now = _iso(_parse(ing["created_utc"]) + timedelta(days=30))
        self.assertEqual(self.store.retention_due(actor=STEWARD, now=now), [])

    def test_due_without_ingestion_uses_dataset_created(self):
        """Core: Retention due. With no ingestion, the reference is the dataset created_utc."""
        policy = self.store.set_retention_policy(self.dataset["id"], 30, "archive", STEWARD)
        now = _iso(_parse(self.dataset["created_utc"]) + timedelta(days=31))
        due = self.store.retention_due(actor=VIEWER, now=now)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["reference_utc"], self.dataset["created_utc"])
        self.assertEqual(due[0]["age_days"], 31)

    def test_legal_hold_excluded_from_due(self):
        """Core: Retention due. A legal_hold policy is never listed as due, however old the data."""
        self.store.set_retention_policy(
            self.dataset["id"], 30, "delete", STEWARD, legal_hold=True
        )
        now = _iso(_parse(self.dataset["created_utc"]) + timedelta(days=400))
        self.assertEqual(self.store.retention_due(actor=STEWARD, now=now), [])

    def test_failed_ingestion_is_not_reference(self):
        """Core: Retention due. A failed ingestion does not become the reference; the dataset creation time stands."""
        self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD,
            record_count=10, status="failed",
        )
        self.store.set_retention_policy(self.dataset["id"], 30, "delete", STEWARD)
        now = _iso(_parse(self.dataset["created_utc"]) + timedelta(days=31))
        due = self.store.retention_due(actor=STEWARD, now=now)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["reference_utc"], self.dataset["created_utc"])

    def test_no_policies_no_due(self):
        """Core: Retention due. No policies -> empty due list."""
        self.assertEqual(self.store.retention_due(actor=STEWARD), [])


if __name__ == "__main__":
    unittest.main()
