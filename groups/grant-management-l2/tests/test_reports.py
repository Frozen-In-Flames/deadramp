"""Core: Post-award report records. Traces to UNION-SPEC core
function 6 (post_award_reports_access). Report status is derived at
read from the due date and the submission timestamp, never stored."""

import unittest

import grants_helpers as H
from grants.errors import ValidationError


class TestReports(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()
        _, result = H.make_award(self.store, self.program, self.org)
        self.award = result["award"]

    def test_create_and_pending_status(self):
        report = self.store.create_report(H.MEMBER, self.award["id"],
                                          "progress", "2026-09-30")
        self.assertTrue(report["id"].startswith("rep-"))
        view = self.store.get_report(H.MEMBER, report["id"], now="2026-08-01")
        self.assertEqual(view["status"], "pending")

    def test_overdue_is_derived_from_the_read_clock(self):
        report = self.store.create_report(H.MEMBER, self.award["id"],
                                          "progress", "2026-09-30")
        self.assertEqual(
            self.store.get_report(H.MEMBER, report["id"],
                                  now="2026-09-30")["status"], "pending")
        self.assertEqual(
            self.store.get_report(H.MEMBER, report["id"],
                                  now="2026-10-01")["status"], "overdue")

    def test_stored_record_carries_no_status(self):
        report = self.store.create_report(H.MEMBER, self.award["id"],
                                          "final", "2026-09-30")
        raw = self.store._reports[report["id"]]
        self.assertNotIn("status", raw)
        self.assertIsNone(raw["submitted_at"])

    def test_submit_marks_submitted_even_after_due(self):
        report = self.store.create_report(H.MEMBER, self.award["id"],
                                          "progress", "2026-09-30")
        done = self.store.submit_report(H.MEMBER, report["id"], "Q3 outcomes",
                                        submitted_at="2026-10-15")
        self.assertEqual(done["status"], "submitted")
        self.assertEqual(done["summary"], "Q3 outcomes")
        self.assertEqual(
            self.store.get_report(H.MEMBER, report["id"],
                                  now="2027-01-01")["status"], "submitted")

    def test_double_submit_rejected(self):
        report = self.store.create_report(H.MEMBER, self.award["id"],
                                          "progress", "2026-09-30")
        self.store.submit_report(H.MEMBER, report["id"], "once")
        with self.assertRaises(ValidationError):
            self.store.submit_report(H.MEMBER, report["id"], "twice")

    def test_bad_kind_and_bad_due_date(self):
        with self.assertRaises(ValidationError):
            self.store.create_report(H.MEMBER, self.award["id"],
                                     "weekly", "2026-09-30")
        with self.assertRaises(ValidationError):
            self.store.create_report(H.MEMBER, self.award["id"],
                                     "progress", "next Friday")

    def test_list_reports_for_award(self):
        self.store.create_report(H.MEMBER, self.award["id"], "progress",
                                 "2026-09-30")
        self.store.create_report(H.MEMBER, self.award["id"], "final",
                                 "2027-03-31")
        reports = self.store.list_reports(H.MEMBER, self.award["id"],
                                          now="2026-08-01")
        self.assertEqual(len(reports), 2)
        self.assertTrue(all(r["status"] == "pending" for r in reports))


if __name__ == "__main__":
    unittest.main()
