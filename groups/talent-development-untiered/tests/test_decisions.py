import unittest

from talentdev.errors import NotFoundError, PermissionDenied, ValidationError
from talentdev_helpers import ADMIN, OPERATOR, VIEWER, make_org, make_store


class TestDecisions(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org = make_org(self.store)
        self.other = make_org(self.store, ref="agency-beta", label="Beta")
        self.assessment = self.store.create_assessment(
            ADMIN, self.org["id"], "Baseline", "Instrument")
        self.snapshot = self.store.record_snapshot(
            ADMIN, self.org["id"], "trend-index", "2026-Q4", 40, 12)

    def test_record_decision_with_basis(self):
        decision = self.store.record_decision(
            OPERATOR, self.org["id"], "Expand the leadership program",
            "approved", "board-ref-1",
            basis_assessment_ids=[self.assessment["id"]],
            basis_snapshot_ids=[self.snapshot["id"]],
            decided_at="2026-10-21")
        self.assertEqual(decision["id"], "dec-1")
        self.assertEqual(decision["basis_assessment_ids"], ["asm-1"])
        self.assertEqual(decision["basis_snapshot_ids"], ["ins-1"])
        summary = self.store.summary(ADMIN)
        self.assertEqual(summary["decisions_by_decision"],
                         {"approved": 1, "deferred": 0, "declined": 0})

    def test_decision_vocabulary_is_closed(self):
        for bad in ("recommended", "pending", "yes", ""):
            with self.assertRaises(ValidationError):
                self.store.record_decision(
                    ADMIN, self.org["id"], "X", bad, "board-ref-1")
        self.assertEqual(self.store.list_decisions(ADMIN), [])

    def test_basis_must_exist_and_belong_to_the_org(self):
        foreign = self.store.create_assessment(
            ADMIN, self.other["id"], "Foreign", "Instrument")
        with self.assertRaises(ValidationError):
            self.store.record_decision(
                ADMIN, self.org["id"], "X", "approved", "board-ref-1",
                basis_assessment_ids=[foreign["id"]])
        with self.assertRaises(NotFoundError):
            self.store.record_decision(
                ADMIN, self.org["id"], "X", "approved", "board-ref-1",
                basis_snapshot_ids=["ins-99"])
        with self.assertRaises(NotFoundError):
            self.store.record_decision(
                ADMIN, self.org["id"], "X", "approved", "board-ref-1",
                basis_assessment_ids=["asm-99"])

    def test_decider_is_an_opaque_reference(self):
        with self.assertRaises(ValidationError):
            self.store.record_decision(
                ADMIN, self.org["id"], "X", "approved",
                "decider@example.gov")
        self.assertEqual(self.store.list_decisions(ADMIN), [])

    def test_viewer_cannot_decide(self):
        with self.assertRaises(PermissionDenied):
            self.store.record_decision(VIEWER, self.org["id"], "X",
                                        "approved", "board-ref-1")


if __name__ == "__main__":
    unittest.main()
