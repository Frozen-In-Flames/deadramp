"""Record-shape pins: exact key sets, and a recursive scan that no
record anywhere in the store carries a scoring key, a money key,
or a personal-data key.

The exact key sets are the strongest form of the set's honesty
rules: the participation shape has no ``status`` key (status is
derived at read), the result shape has no numeric field of any
kind (no scoring), and the snapshot shape has no person
reference (aggregate only).
"""

import unittest

from talentdev_helpers import ADMIN, make_org, make_program, make_store

FORBIDDEN_KEY_PARTS = (
    "score", "grade", "rank", "rating", "rate",
    "email", "ssn", "password", "secret",
    "salary", "wage", "price", "fee", "amount", "cost",
    "diagnosis", "health",
)


def scan_keys(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                if part in lowered:
                    hits.append("%s.%s" % (path, key))
            hits.extend(scan_keys(value, "%s.%s" % (path, key)))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            hits.extend(scan_keys(value, "%s[%d]" % (path, index)))
    return hits


class TestShapes(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org = make_org(self.store)
        self.program = make_program(self.store, org_id=self.org["id"])
        self.participation = self.store.enroll(
            ADMIN, self.program["id"], "person-001", enrolled_at="2026-10-01")
        self.assessment = self.store.create_assessment(
            ADMIN, self.org["id"], "Baseline", "Instrument")
        self.result = self.store.record_result(
            ADMIN, self.assessment["id"], "person-001", "completed",
            "2026-10-05")
        self.snapshot = self.store.record_snapshot(
            ADMIN, self.org["id"], "trend-index", "2026-Q4", 40, 12)
        self.decision = self.store.record_decision(
            ADMIN, self.org["id"], "Expand", "approved", "board-ref-1",
            basis_assessment_ids=[self.assessment["id"]],
            basis_snapshot_ids=[self.snapshot["id"]])

    def test_exact_key_sets(self):
        self.assertEqual(
            set(self.org),
            {"id", "ref", "label", "created_by", "created_utc"})
        self.assertEqual(
            set(self.program),
            {"id", "org_id", "label", "kind", "goal_label",
             "created_by", "created_utc"})
        stored_participation = self.store._participations[
            self.participation["id"]]
        self.assertEqual(
            set(stored_participation),
            {"id", "program_id", "participant_ref", "enrolled_at",
             "completed_at", "created_by", "created_utc"})
        # The view adds exactly one derived key: status.
        self.assertEqual(
            set(self.participation), set(stored_participation) | {"status"})
        self.assertEqual(
            set(self.assessment),
            {"id", "org_id", "label", "instrument_label",
             "created_by", "created_utc"})
        self.assertEqual(
            set(self.result),
            {"id", "assessment_id", "subject_ref", "outcome",
             "administered_at", "created_by", "created_utc"})
        self.assertEqual(
            set(self.snapshot),
            {"id", "org_id", "metric_label", "period_label",
             "cohort_size", "value_count", "recorded_at",
             "created_by", "created_utc"})
        self.assertEqual(
            set(self.decision),
            {"id", "org_id", "label", "decision", "decided_by_ref",
             "basis_assessment_ids", "basis_snapshot_ids", "decided_at",
             "created_by", "created_utc"})

    def test_result_record_has_no_numeric_field(self):
        for key, value in self.result.items():
            self.assertNotIsInstance(
                value, (int, float),
                "result field %r carries a number; assessment results "
                "in this core are administration records, not scores"
                % (key,))

    def test_no_forbidden_keys_anywhere(self):
        haystacks = [
            self.store.list_organizations(ADMIN),
            self.store.list_programs(ADMIN),
            self.store.list_participations(ADMIN),
            self.store.list_assessments(ADMIN),
            self.store.list_results(ADMIN),
            self.store.list_snapshots(ADMIN),
            self.store.list_decisions(ADMIN),
            self.store.search(ADMIN, "a"),
            self.store.summary(ADMIN),
        ]
        for haystack in haystacks:
            self.assertEqual(scan_keys(haystack), [])


if __name__ == "__main__":
    unittest.main()
