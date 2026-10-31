"""Insight snapshot tests: the records form of the analytics
family, and the small-cohort guard that binds it."""

import unittest

from talentdev.errors import PermissionDenied, ValidationError
from talentdev.store import MIN_COHORT_SIZE
from talentdev_helpers import ADMIN, OPERATOR, VIEWER, make_org, make_store


class TestSnapshots(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org = make_org(self.store)

    def snapshot(self, cohort=40, value=17, **kwargs):
        return self.store.record_snapshot(
            OPERATOR, self.org["id"], "behavioral-trend-index", "2026-Q4",
            cohort, value, **kwargs)

    def test_record_and_list(self):
        snapshot = self.snapshot()
        self.assertEqual(snapshot["id"], "ins-1")
        self.assertEqual(snapshot["cohort_size"], 40)
        self.assertEqual(snapshot["value_count"], 17)
        listed = self.store.list_snapshots(
            ADMIN, metric_label="behavioral-trend-index")
        self.assertEqual(len(listed), 1)
        self.assertEqual(self.store.summary(ADMIN)["snapshots"], 1)

    def test_snapshot_shape_has_no_person_reference(self):
        # An aggregate snapshot names no individual: no key on the
        # shape can carry a person reference of any kind.
        snapshot = self.snapshot()
        for key in snapshot:
            for token in ("participant", "subject", "person", "decided"):
                self.assertNotIn(token, key)

    def test_small_cohort_guard(self):
        # The guard: a snapshot over a cohort below MIN_COHORT_SIZE
        # is refused, records nothing, and consumes no id.
        for small in (0, 1, MIN_COHORT_SIZE - 1):
            with self.assertRaises(ValidationError):
                self.snapshot(cohort=small, value=0)
        self.assertEqual(self.store.list_snapshots(ADMIN), [])
        allowed = self.snapshot(cohort=MIN_COHORT_SIZE, value=2)
        self.assertEqual(allowed["id"], "ins-1")

    def test_value_cannot_exceed_cohort(self):
        with self.assertRaises(ValidationError):
            self.snapshot(cohort=10, value=11)
        self.assertEqual(self.store.list_snapshots(ADMIN), [])

    def test_counts_are_strict_integers(self):
        for bad in (True, 4.5, "40", -1):
            with self.assertRaises(ValidationError):
                self.snapshot(cohort=bad, value=0)
            with self.assertRaises(ValidationError):
                self.snapshot(cohort=40, value=bad)

    def test_viewer_cannot_record_snapshot(self):
        with self.assertRaises(PermissionDenied):
            self.store.record_snapshot(VIEWER, self.org["id"], "m", "p",
                                       40, 1)


if __name__ == "__main__":
    unittest.main()
