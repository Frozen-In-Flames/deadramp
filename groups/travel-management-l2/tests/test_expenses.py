import unittest

from travel.errors import PermissionDenied, ValidationError

from travel_helpers import (DECIDER, MEMBER, make_approved_authorization,
                            make_approved_report, make_authorization,
                            make_report, make_report_with_items, make_store,
                            make_traveler)


class TestExpenseReports(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.traveler = make_traveler(self.store, self.org)
        self.auth = make_approved_authorization(self.store, self.org,
                                                self.traveler)

    def test_report_requires_approved_authorization(self):
        draft = make_authorization(self.store, self.org, self.traveler,
                                   purpose="Second trip")
        with self.assertRaises(ValidationError):
            self.store.create_expense_report(MEMBER, draft["id"], "Nope")

    def test_items_and_derived_total(self):
        report = make_report_with_items(self.store, self.auth)
        self.assertEqual(report["total_cents"], 150_000)
        self.assertEqual(report["reimbursed_cents"], 0)
        self.assertEqual(report["remaining_cents"], 150_000)

    def test_total_never_stored(self):
        report = make_report_with_items(self.store, self.auth)
        raw = self.store._expense_reports[report["id"]]
        self.assertNotIn("total_cents", raw)
        self.assertNotIn("reimbursed_cents", raw)
        self.assertNotIn("remaining_cents", raw)

    def test_bad_category_rejected(self):
        report = make_report(self.store, self.auth)
        with self.assertRaises(ValidationError):
            self.store.add_expense_item(MEMBER, report["id"], "gifts",
                                        100, "2026-06-10")

    def test_float_amount_rejected(self):
        report = make_report(self.store, self.auth)
        with self.assertRaises(ValidationError):
            self.store.add_expense_item(MEMBER, report["id"], "meals",
                                        10.5, "2026-06-10")

    def test_items_only_on_draft(self):
        report = make_approved_report(self.store, self.auth)
        with self.assertRaises(ValidationError):
            self.store.add_expense_item(MEMBER, report["id"], "meals",
                                        100, "2026-06-10")

    def test_empty_report_cannot_submit(self):
        report = make_report(self.store, self.auth)
        with self.assertRaises(ValidationError):
            self.store.submit_expense_report(MEMBER, report["id"])

    def test_submit_and_decide_flow(self):
        report = make_approved_report(self.store, self.auth)
        self.assertEqual(report["status"], "approved")
        decisions = self.store.list_decisions(MEMBER, self.org["id"],
                                              target_id=report["id"])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["target_kind"], "expense_report")

    def test_creator_cannot_decide_own_report(self):
        report = make_report_with_items(self.store, self.auth)
        self.store.submit_expense_report(MEMBER, report["id"])
        with self.assertRaises(PermissionDenied):
            self.store.decide_expense_report(MEMBER, report["id"], True)

    def test_declined_report(self):
        report = make_report_with_items(self.store, self.auth)
        self.store.submit_expense_report(MEMBER, report["id"])
        result = self.store.decide_expense_report(DECIDER, report["id"],
                                                  False)
        self.assertEqual(result["expense_report"]["status"], "declined")


class TestAuthorizationCap(unittest.TestCase):
    """At submission, cumulative submitted+approved report totals
    against an authorization never exceed its authorized amount."""

    def setUp(self):
        self.store, self.org = make_store()
        self.traveler = make_traveler(self.store, self.org)
        self.auth = make_approved_authorization(
            self.store, self.org, self.traveler, authorized_cents=200_000)

    def test_reports_up_to_cap_submit(self):
        report = make_report_with_items(self.store, self.auth)
        view = self.store.submit_expense_report(MEMBER, report["id"])
        self.assertEqual(view["status"], "submitted")

    def test_report_over_cap_rejected_at_submit(self):
        first = make_report_with_items(self.store, self.auth)
        self.store.submit_expense_report(MEMBER, first["id"])
        second = make_report_with_items(
            self.store, self.auth, items=(("lodging", 60_000),))
        with self.assertRaises(ValidationError):
            self.store.submit_expense_report(MEMBER, second["id"])
        # The rejected submission changed nothing.
        self.assertEqual(
            self.store.get_expense_report(MEMBER, second["id"])["status"],
            "draft")

    def test_draft_reports_do_not_commit_cap(self):
        make_report_with_items(self.store, self.auth)  # stays draft
        second = make_report_with_items(
            self.store, self.auth, items=(("lodging", 190_000),))
        view = self.store.submit_expense_report(MEMBER, second["id"])
        self.assertEqual(view["status"], "submitted")


if __name__ == "__main__":
    unittest.main()
