"""Service case tests.

Traces to: Core 2 (Service case records & lifecycle) -- claim basis
case_service_records (Oracle) -- and control families AU-2, CM-6.
Breach is derived at read time, never stored.
"""

import unittest

import crm_helpers as H
from crm.errors import NotFoundError, PermissionDenied, ValidationError

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"
FUTURE = "2030-01-01T00:00:00Z"


class TestCaseCreate(unittest.TestCase):
    """Core 2: case creation and validation."""

    def setUp(self):
        self.store, self.account, self.contact = H.make_store()

    def test_create_shape(self):
        """Core 2: case shape/defaults (status open, priority normal)."""
        case = self.store.create_case(H.OPERATOR, "inquiry", "How do I reset?")
        self.assertEqual(case["id"], "case-1")
        self.assertEqual(case["status"], "open")
        self.assertEqual(case["priority"], "normal")
        self.assertFalse(case["breached"])

    def test_all_types(self):
        """Core 2: all five case types are accepted."""
        for case_type in ("inquiry", "problem", "request", "feedback", "general"):
            case = self.store.create_case(H.OPERATOR, case_type, "s")
            self.assertEqual(case["case_type"], case_type)

    def test_bad_type_and_priority(self):
        """Core 2 (SI-10): unknown type/priority -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_case(H.OPERATOR, "ticket", "s")
        with self.assertRaises(ValidationError):
            self.store.create_case(H.OPERATOR, "inquiry", "s", priority="urgent")

    def test_empty_subject(self):
        """Core 2 (SI-10): empty subject -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_case(H.OPERATOR, "inquiry", "  ")

    def test_bad_due_at(self):
        """Core 2 (SI-10): unparseable due_at -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_case(H.OPERATOR, "inquiry", "s", due_at="next week")

    def test_unknown_links(self):
        """Core 2: unknown account/contact ids -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.create_case(H.OPERATOR, "inquiry", "s", account_id="acct-99")
        with self.assertRaises(NotFoundError):
            self.store.create_case(H.OPERATOR, "inquiry", "s", contact_id="ct-99")

    def test_contact_account_mismatch(self):
        """Core 2: a contact linked with an account it does not
        belong to -> ValidationError (referential consistency)."""
        other = self.store.create_account(H.ADMIN, "ACCT-2")
        with self.assertRaises(ValidationError):
            self.store.create_case(H.OPERATOR, "inquiry", "s",
                                   account_id=other["id"],
                                   contact_id=self.contact["id"])

    def test_failed_create_consumes_no_id(self):
        """Core 2 (SI-10): failed creation consumes no id."""
        with self.assertRaises(ValidationError):
            self.store.create_case(H.OPERATOR, "ticket", "s")
        case = self.store.create_case(H.OPERATOR, "inquiry", "s")
        self.assertEqual(case["id"], "case-1")

    def test_viewer_write_denied(self):
        """Core 2/10 (AC-3): viewer may not create cases."""
        with self.assertRaises(PermissionDenied):
            self.store.create_case(H.VIEWER, "inquiry", "s")


class TestCaseLifecycle(unittest.TestCase):
    """Core 2: the stage lifecycle."""

    def setUp(self):
        self.store = H.fresh_store()
        self.case = self.store.create_case(H.OPERATOR, "problem", "Broken widget")

    def _move(self, *statuses):
        for status in statuses:
            self.case = self.store.transition_case(self.case["id"], H.OPERATOR, status)

    def test_happy_path(self):
        """Core 2: open -> in_progress -> resolved -> closed."""
        self._move("in_progress", "resolved", "closed")
        self.assertEqual(self.case["status"], "closed")

    def test_reopen_from_resolved(self):
        """Core 2: resolved may reopen to in_progress."""
        self._move("in_progress", "resolved", "in_progress")
        self.assertEqual(self.case["status"], "in_progress")

    def test_send_back_to_open(self):
        """Core 2: in_progress may return to open."""
        self._move("in_progress", "open")
        self.assertEqual(self.case["status"], "open")

    def test_cancel_paths(self):
        """Core 2: open and in_progress may be cancelled."""
        self._move("cancelled")
        self.assertEqual(self.case["status"], "cancelled")
        case2 = self.store.create_case(H.OPERATOR, "request", "x")
        self.store.transition_case(case2["id"], H.OPERATOR, "in_progress")
        out = self.store.transition_case(case2["id"], H.OPERATOR, "cancelled")
        self.assertEqual(out["status"], "cancelled")

    def test_invalid_transitions(self):
        """Core 2: skipping stages and leaving terminal states ->
        ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.transition_case(self.case["id"], H.OPERATOR, "resolved")
        with self.assertRaises(ValidationError):
            self.store.transition_case(self.case["id"], H.OPERATOR, "closed")
        self._move("in_progress", "resolved", "closed")
        with self.assertRaises(ValidationError):
            self.store.transition_case(self.case["id"], H.OPERATOR, "open")

    def test_assign(self):
        """Core 2: assign sets the opaque assignee reference;
        empty reference -> ValidationError."""
        out = self.store.assign_case(self.case["id"], H.OPERATOR, "STAFF-7")
        self.assertEqual(out["assignee_ref"], "STAFF-7")
        with self.assertRaises(ValidationError):
            self.store.assign_case(self.case["id"], H.OPERATOR, "")


class TestBreachDerivation(unittest.TestCase):
    """Core 2: breach derived at read, never stored (AU-6, CM-6)."""

    def setUp(self):
        self.store = H.fresh_store()

    def test_overdue_open_case_breached(self):
        """Core 2: past-due open case reads breached=True at now."""
        case = self.store.create_case(H.OPERATOR, "problem", "late", due_at=PAST)
        self.assertTrue(self.store.get_case(case["id"], H.OPERATOR, now=NOW)["breached"])

    def test_in_progress_past_due_breached(self):
        """Core 2: past-due in_progress case is breached."""
        case = self.store.create_case(H.OPERATOR, "problem", "late", due_at=PAST)
        self.store.transition_case(case["id"], H.OPERATOR, "in_progress")
        self.assertTrue(self.store.get_case(case["id"], H.OPERATOR, now=NOW)["breached"])

    def test_future_and_no_due_not_breached(self):
        """Core 2: future due date and no due date are not breached."""
        c1 = self.store.create_case(H.OPERATOR, "problem", "a", due_at=FUTURE)
        c2 = self.store.create_case(H.OPERATOR, "problem", "b")
        self.assertFalse(self.store.get_case(c1["id"], H.OPERATOR, now=NOW)["breached"])
        self.assertFalse(self.store.get_case(c2["id"], H.OPERATOR, now=NOW)["breached"])

    def test_terminal_statuses_never_breached(self):
        """Core 2: resolved/closed/cancelled never read breached."""
        for path in (("in_progress", "resolved"),
                     ("in_progress", "resolved", "closed"),
                     ("cancelled",)):
            case = self.store.create_case(H.OPERATOR, "problem", "t", due_at=PAST)
            for status in path:
                self.store.transition_case(case["id"], H.OPERATOR, status)
            self.assertFalse(
                self.store.get_case(case["id"], H.OPERATOR, now=NOW)["breached"])

    def test_breach_is_derived_not_stored(self):
        """Core 2: the stored record has no 'breached' key; the same
        case reads differently at different 'now' values."""
        case = self.store.create_case(H.OPERATOR, "problem", "t", due_at=PAST)
        stored = self.store._cases[case["id"]]
        self.assertNotIn("breached", stored)
        early = self.store.get_case(case["id"], H.OPERATOR, now="2019-01-01T00:00:00Z")
        self.assertFalse(early["breached"])

    def test_now_forms(self):
        """Core 2: now accepted as string, datetime, or None."""
        from datetime import datetime, timezone
        case = self.store.create_case(H.OPERATOR, "problem", "t", due_at=PAST)
        self.assertTrue(self.store.get_case(case["id"], H.OPERATOR, now=NOW)["breached"])
        self.assertTrue(self.store.get_case(
            case["id"], H.OPERATOR,
            now=datetime(2025, 6, 1, tzinfo=timezone.utc))["breached"])
        self.assertIn("breached", self.store.get_case(case["id"], H.OPERATOR))


class TestCaseListFilters(unittest.TestCase):
    """Core 2: list filters."""

    def test_filters(self):
        """Core 2: list_cases filters by status/type/account."""
        store, account, contact = H.make_store()
        store.create_case(H.OPERATOR, "inquiry", "a", account_id=account["id"])
        c2 = store.create_case(H.OPERATOR, "problem", "b")
        store.transition_case(c2["id"], H.OPERATOR, "in_progress")
        self.assertEqual(len(store.list_cases(H.VIEWER, status="open")), 1)
        self.assertEqual(len(store.list_cases(H.VIEWER, case_type="problem")), 1)
        self.assertEqual(len(store.list_cases(H.VIEWER, account_id=account["id"])), 1)
        self.assertEqual(len(store.list_cases(H.VIEWER)), 2)


if __name__ == "__main__":
    unittest.main()
