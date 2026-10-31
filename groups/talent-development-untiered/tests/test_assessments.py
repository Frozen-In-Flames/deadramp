import unittest

from talentdev.errors import NotFoundError, PermissionDenied, ValidationError
from talentdev_helpers import ADMIN, OPERATOR, VIEWER, make_org, make_store


class TestAssessments(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org = make_org(self.store)

    def test_create_and_list(self):
        assessment = self.store.create_assessment(
            OPERATOR, self.org["id"], "Workforce Skills Baseline",
            "Panel Instrument v2")
        self.assertEqual(assessment["id"], "asm-1")
        self.assertEqual(assessment["instrument_label"], "Panel Instrument v2")
        self.assertEqual(len(self.store.list_assessments(ADMIN)), 1)
        with self.assertRaises(NotFoundError):
            self.store.create_assessment(ADMIN, "org-99", "X", "Y")

    def test_record_result_administration_outcomes(self):
        assessment = self.store.create_assessment(
            ADMIN, self.org["id"], "Baseline", "Instrument")
        result = self.store.record_result(
            OPERATOR, assessment["id"], "person-001", "completed",
            "2026-10-05")
        self.assertEqual(result["id"], "res-1")
        self.assertEqual(result["outcome"], "completed")
        for outcome in ("partial", "not_completed"):
            self.store.record_result(ADMIN, assessment["id"], "person-002",
                                     outcome, "2026-10-06")
        summary = self.store.summary(ADMIN)
        self.assertEqual(summary["results_by_outcome"],
                         {"completed": 1, "partial": 1, "not_completed": 1})

    def test_result_refuses_judgment_outcomes(self):
        # The outcome vocabulary is administration states only. A
        # score band, a pass/fail judgment, or a rating is not a
        # recordable value anywhere in this store.
        assessment = self.store.create_assessment(
            ADMIN, self.org["id"], "Baseline", "Instrument")
        for bad in ("passed", "failed", "excellent", "85", ""):
            with self.assertRaises(ValidationError):
                self.store.record_result(ADMIN, assessment["id"],
                                         "person-001", bad, "2026-10-05")
        self.assertEqual(self.store.list_results(ADMIN), [])

    def test_result_requires_known_assessment_and_clean_ref(self):
        with self.assertRaises(NotFoundError):
            self.store.record_result(ADMIN, "asm-99", "person-001",
                                     "completed", "2026-10-05")
        assessment = self.store.create_assessment(
            ADMIN, self.org["id"], "Baseline", "Instrument")
        with self.assertRaises(ValidationError):
            self.store.record_result(ADMIN, assessment["id"],
                                     "person@example.gov", "completed",
                                     "2026-10-05")

    def test_viewer_cannot_assess(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_assessment(VIEWER, self.org["id"], "X", "Y")


if __name__ == "__main__":
    unittest.main()
