"""Core function 6: expense records -- reports with derived
totals and a recorded-outcome lifecycle (CM-6, AU-2/AU-3, SI-10).

The fork's expense claim names Expense Reports, Travel Plans,
Payment Requests, and Timesheets as its applications; this build
keeps the report record (timesheets are the time-entry records).
Policy enforcement and fraud detection over reports are Extended
engines, not this substrate.
"""

import unittest

from erp.errors import NotFoundError, ValidationError

from erp_helpers import (OPERATOR, PERSON_REF, make_org, make_person,
                         make_store)

LINES = [
    {"category_label": "Travel", "amount_cents": 4200},
    {"category_label": "Meals", "amount_cents": 1575},
]


def make_report(store, org, actor=OPERATOR, ref="EXP-0001"):
    return store.create_expense_report(actor, org["id"], PERSON_REF, ref,
                                       LINES)


class ExpenseReportTests(unittest.TestCase):
    def setUp(self):
        self.store, _ = make_store()
        self.org = make_org(self.store)
        make_person(self.store, self.org)

    def test_total_is_derived_and_never_stored(self):
        report = make_report(self.store, self.org)
        self.assertEqual(report["total_cents"], 4200 + 1575)
        self.assertEqual(report["status"], "submitted")
        stored = self.store._expense_reports[report["id"]]
        self.assertNotIn("total_cents", stored)

    def test_outcome_lifecycle_is_terminal(self):
        report = make_report(self.store, self.org)
        done = self.store.record_expense_outcome(
            OPERATOR, report["id"], "approved", note="Within policy (label)")
        self.assertEqual(done["status"], "approved")
        self.assertEqual(done["outcome_note"], "Within policy (label)")
        with self.assertRaises(ValidationError):
            self.store.record_expense_outcome(OPERATOR, report["id"],
                                              "rejected")

    def test_unknown_outcome_refused(self):
        report = make_report(self.store, self.org)
        with self.assertRaises(ValidationError):
            self.store.record_expense_outcome(OPERATOR, report["id"],
                                              "pending")

    def test_report_requires_a_person_record(self):
        with self.assertRaises(NotFoundError):
            self.store.create_expense_report(
                OPERATOR, self.org["id"], "PERSON-404", "EXP-404", LINES)

    def test_amount_types_rejected(self):
        for bad in (1.5, False, "50"):
            lines = [{"category_label": "X", "amount_cents": bad}]
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.create_expense_report(
                    OPERATOR, self.org["id"], PERSON_REF, "EXP-BAD", lines)


if __name__ == "__main__":
    unittest.main()
