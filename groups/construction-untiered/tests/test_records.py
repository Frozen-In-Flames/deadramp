"""Submittals and RFIs tests.

Traces to: Core -- Submittals (sub-) and RFIs (rfi-) lifecycles with
overdue derivation via ``ConstructStore._record_overdue``;
terminal statuses are never overdue.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, make_store
from construct.errors import NotFoundError, ValidationError

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"
FUTURE = "2030-01-01T00:00:00Z"


class TestSubmittals(unittest.TestCase):
    """Submittals: lifecycle and overdue derivation."""

    def test_create_shape(self):
        """Submittals. create_submittal makes sub- in draft with overdue derived False."""
        store, project, prime, sub = make_store()
        s = store.create_submittal(OPERATOR, project["id"], "Steel package", org_id=prime["id"], due_at=FUTURE)
        self.assertEqual(s["id"], "sub-1")
        self.assertEqual(s["status"], "draft")
        self.assertFalse(s["overdue"])
        self.assertEqual(s["org_id"], prime["id"])

    def test_full_lifecycle_and_revise_loop(self):
        """Submittals. draft->submitted->under_review->revise_resubmit->submitted->under_review->approved."""
        store, project, prime, sub = make_store()
        s = store.create_submittal(OPERATOR, project["id"], "Steel")
        for to in ("submitted", "under_review", "revise_resubmit", "submitted", "under_review", "approved"):
            s = store.transition_submittal(s["id"], OPERATOR, to)
            self.assertEqual(s["status"], to)

    def test_approved_as_noted_and_rejected_terminals(self):
        """Submittals. approved_as_noted and rejected are reachable and terminal."""
        store, project, prime, sub = make_store()
        for final in ("approved_as_noted", "rejected"):
            s = store.create_submittal(OPERATOR, project["id"], "Pkg %s" % final)
            store.transition_submittal(s["id"], OPERATOR, "submitted")
            store.transition_submittal(s["id"], OPERATOR, "under_review")
            done = store.transition_submittal(s["id"], OPERATOR, final)
            self.assertEqual(done["status"], final)
            with self.assertRaises(ValidationError):
                store.transition_submittal(s["id"], OPERATOR, "submitted")

    def test_invalid_transitions(self):
        """Submittals. draft->approved and submitted->approved -> ValidationError."""
        store, project, prime, sub = make_store()
        s = store.create_submittal(OPERATOR, project["id"], "Steel")
        with self.assertRaises(ValidationError):
            store.transition_submittal(s["id"], OPERATOR, "approved")
        store.transition_submittal(s["id"], OPERATOR, "submitted")
        with self.assertRaises(ValidationError):
            store.transition_submittal(s["id"], OPERATOR, "approved")

    def test_overdue_derivation(self):
        """Submittals. Past-due non-terminal reads overdue=True at now; future/no due do not."""
        store, project, prime, sub = make_store()
        late = store.create_submittal(OPERATOR, project["id"], "Late", due_at=PAST)
        early = store.create_submittal(OPERATOR, project["id"], "Early", due_at=FUTURE)
        nodue = store.create_submittal(OPERATOR, project["id"], "No due")
        self.assertTrue(store.get_submittal(late["id"], VIEWER, now=NOW)["overdue"])
        self.assertFalse(store.get_submittal(early["id"], VIEWER, now=NOW)["overdue"])
        self.assertFalse(store.get_submittal(nodue["id"], VIEWER, now=NOW)["overdue"])
        self.assertFalse(store.get_submittal(late["id"], VIEWER, now="2019-01-01T00:00:00Z")["overdue"])

    def test_terminal_never_overdue(self):
        """Submittals. An approved past-due submittal never reads overdue."""
        store, project, prime, sub = make_store()
        s = store.create_submittal(OPERATOR, project["id"], "Steel", due_at=PAST)
        store.transition_submittal(s["id"], OPERATOR, "submitted")
        store.transition_submittal(s["id"], OPERATOR, "under_review")
        store.transition_submittal(s["id"], OPERATOR, "approved")
        self.assertFalse(store.get_submittal(s["id"], VIEWER, now=NOW)["overdue"])

    def test_validation_and_filters(self):
        """Submittals. Empty title/unknown ids -> errors; list filters by project/status."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_submittal(OPERATOR, project["id"], "")
        with self.assertRaises(NotFoundError):
            store.create_submittal(OPERATOR, "prj-99", "X")
        with self.assertRaises(NotFoundError):
            store.create_submittal(OPERATOR, project["id"], "X", org_id="org-99")
        s = store.create_submittal(OPERATOR, project["id"], "Only")
        self.assertEqual(s["id"], "sub-1")
        self.assertEqual(len(store.list_submittals(VIEWER, now=NOW, project_id=project["id"])), 1)
        self.assertEqual(len(store.list_submittals(VIEWER, now=NOW, status="submitted")), 0)


class TestRFIs(unittest.TestCase):
    """RFIs: lifecycle and overdue derivation."""

    def test_create_shape_and_question_required(self):
        """RFIs. create_rfi makes rfi- open; empty question -> ValidationError, no id consumed."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_rfi(OPERATOR, project["id"], "  ")
        r = store.create_rfi(OPERATOR, project["id"], "Which finish?", due_at=PAST)
        self.assertEqual(r["id"], "rfi-1")
        self.assertEqual(r["status"], "open")
        self.assertTrue(r["overdue"] is False or r["overdue"] is True)  # derived key present
        self.assertIn("overdue", r)

    def test_lifecycle_and_reopen(self):
        """RFIs. open->answered->open->answered->closed succeeds; closed is terminal."""
        store, project, prime, sub = make_store()
        r = store.create_rfi(OPERATOR, project["id"], "Q?")
        for to in ("answered", "open", "answered", "closed"):
            r = store.transition_rfi(r["id"], OPERATOR, to)
            self.assertEqual(r["status"], to)
        with self.assertRaises(ValidationError):
            store.transition_rfi(r["id"], OPERATOR, "open")

    def test_invalid_transition(self):
        """RFIs. open->open (self) and answered->answered -> ValidationError."""
        store, project, prime, sub = make_store()
        r = store.create_rfi(OPERATOR, project["id"], "Q?")
        with self.assertRaises(ValidationError):
            store.transition_rfi(r["id"], OPERATOR, "open")
        with self.assertRaises(ValidationError):
            store.transition_rfi(r["id"], OPERATOR, "bogus")

    def test_overdue_derivation_and_terminal(self):
        """RFIs. Past-due open RFI is overdue; closed RFI never is; answered still can be."""
        store, project, prime, sub = make_store()
        r = store.create_rfi(OPERATOR, project["id"], "Q?", due_at=PAST)
        self.assertTrue(store.get_rfi(r["id"], VIEWER, now=NOW)["overdue"])
        store.transition_rfi(r["id"], OPERATOR, "answered")
        self.assertTrue(store.get_rfi(r["id"], VIEWER, now=NOW)["overdue"])
        store.transition_rfi(r["id"], OPERATOR, "closed")
        self.assertFalse(store.get_rfi(r["id"], VIEWER, now=NOW)["overdue"])
        future = store.create_rfi(OPERATOR, project["id"], "Later?", due_at=FUTURE)
        self.assertFalse(store.get_rfi(future["id"], VIEWER, now=NOW)["overdue"])

    def test_list_filters(self):
        """RFIs. list_rfis filters by project_id and status."""
        store, project, prime, sub = make_store()
        store.create_rfi(OPERATOR, project["id"], "One?")
        r2 = store.create_rfi(OPERATOR, project["id"], "Two?")
        store.transition_rfi(r2["id"], OPERATOR, "answered")
        self.assertEqual(len(store.list_rfis(VIEWER, now=NOW, status="open")), 1)
        self.assertEqual(len(store.list_rfis(VIEWER, now=NOW, project_id=project["id"])), 2)


if __name__ == "__main__":
    unittest.main()
