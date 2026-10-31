"""Milestones and dispatches tests.

Traces to: Core -- Milestones (ms-) due-state derivation via
``ConstructStore._milestone_due_state`` and Dispatches (dsp-)
lifecycle.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, make_store
from construct.errors import NotFoundError, ValidationError

NOW = "2025-06-01T00:00:00Z"


class TestMilestones(unittest.TestCase):
    """Milestones: due_state derivation and completion guards."""

    def test_create_shape_and_due_required(self):
        """Milestones. create makes ms- incomplete; missing/bad due_at -> ValidationError."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_milestone(OPERATOR, project["id"], "No due", None)
        with self.assertRaises(ValidationError):
            store.create_milestone(OPERATOR, project["id"], "Bad due", "junk")
        with self.assertRaises(ValidationError):
            store.create_milestone(OPERATOR, project["id"], "", "2030-01-01T00:00:00Z")
        with self.assertRaises(NotFoundError):
            store.create_milestone(OPERATOR, "prj-99", "X", "2030-01-01T00:00:00Z")
        m = store.create_milestone(OPERATOR, project["id"], "Topping out", "2030-01-01T00:00:00Z")
        self.assertEqual(m["id"], "ms-1")
        self.assertFalse(m["completed"])
        self.assertIsNone(m["completed_at"])
        self.assertEqual(m["due_state"], "upcoming")

    def test_due_state_upcoming(self):
        """Milestones. Due >7 days after now reads upcoming."""
        store, project, prime, sub = make_store()
        m = store.create_milestone(OPERATOR, project["id"], "Far", "2025-07-01T00:00:00Z")
        self.assertEqual(store.get_milestone(m["id"], VIEWER, now=NOW)["due_state"], "upcoming")

    def test_due_state_due_soon(self):
        """Milestones. Due within 7 days (incl. exactly 7) reads due_soon."""
        store, project, prime, sub = make_store()
        m = store.create_milestone(OPERATOR, project["id"], "Soon", "2025-06-05T00:00:00Z")
        self.assertEqual(store.get_milestone(m["id"], VIEWER, now=NOW)["due_state"], "due_soon")
        edge = store.create_milestone(OPERATOR, project["id"], "Edge", "2025-06-08T00:00:00Z")
        self.assertEqual(store.get_milestone(edge["id"], VIEWER, now=NOW)["due_state"], "due_soon")
        at_now = store.create_milestone(OPERATOR, project["id"], "Now", NOW)
        self.assertEqual(store.get_milestone(at_now["id"], VIEWER, now=NOW)["due_state"], "due_soon")

    def test_due_state_overdue(self):
        """Milestones. Due before now reads overdue."""
        store, project, prime, sub = make_store()
        m = store.create_milestone(OPERATOR, project["id"], "Late", "2025-05-01T00:00:00Z")
        self.assertEqual(store.get_milestone(m["id"], VIEWER, now=NOW)["due_state"], "overdue")

    def test_due_state_completed_wins(self):
        """Milestones. A completed past-due milestone reads completed, not overdue."""
        store, project, prime, sub = make_store()
        m = store.create_milestone(OPERATOR, project["id"], "Done late", "2020-01-01T00:00:00Z")
        store.complete_milestone(m["id"], OPERATOR, completed_at="2025-05-02T00:00:00Z")
        view = store.get_milestone(m["id"], VIEWER, now=NOW)
        self.assertEqual(view["due_state"], "completed")
        self.assertTrue(view["completed"])
        self.assertEqual(view["completed_at"], "2025-05-02T00:00:00Z")

    def test_complete_defaults_and_double_complete_guard(self):
        """Milestones. complete defaults completed_at to now; second complete -> ValidationError."""
        store, project, prime, sub = make_store()
        m = store.create_milestone(OPERATOR, project["id"], "M", "2030-01-01T00:00:00Z")
        done = store.complete_milestone(m["id"], OPERATOR)
        self.assertTrue(done["completed"])
        self.assertIsNotNone(done["completed_at"])
        with self.assertRaises(ValidationError):
            store.complete_milestone(m["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.complete_milestone(m["id"], OPERATOR, completed_at="junk")
        with self.assertRaises(NotFoundError):
            store.complete_milestone("ms-99", OPERATOR)

    def test_derived_not_stored_and_list_filter(self):
        """Milestones. Stored record has no due_state key; list filters by project."""
        store, project, prime, sub = make_store()
        m = store.create_milestone(OPERATOR, project["id"], "M", "2030-01-01T00:00:00Z")
        self.assertNotIn("due_state", store._milestones[m["id"]])
        self.assertEqual(len(store.list_milestones(VIEWER, now=NOW, project_id=project["id"])), 1)
        self.assertEqual(len(store.list_milestones(VIEWER, now=NOW, project_id="prj-99")), 0)


class TestDispatches(unittest.TestCase):
    """Dispatches: lifecycle."""

    def test_create_shape(self):
        """Dispatches. create_dispatch makes dsp- in assigned."""
        store, project, prime, sub = make_store()
        d = store.create_dispatch(OPERATOR, project["id"], "Pour deck", org_id=prime["id"],
                                  worker_ref="W-1", scheduled_for="2025-06-02T00:00:00Z")
        self.assertEqual(d["id"], "dsp-1")
        self.assertEqual(d["status"], "assigned")
        self.assertEqual(d["worker_ref"], "W-1")

    def test_lifecycle(self):
        """Dispatches. assigned->in_progress->completed succeeds; assigned->cancelled succeeds."""
        store, project, prime, sub = make_store()
        d = store.create_dispatch(OPERATOR, project["id"], "Task A")
        d = store.transition_dispatch(d["id"], OPERATOR, "in_progress")
        self.assertEqual(d["status"], "in_progress")
        d = store.transition_dispatch(d["id"], OPERATOR, "completed")
        self.assertEqual(d["status"], "completed")
        d2 = store.create_dispatch(OPERATOR, project["id"], "Task B")
        self.assertEqual(store.transition_dispatch(d2["id"], OPERATOR, "cancelled")["status"], "cancelled")
        d3 = store.create_dispatch(OPERATOR, project["id"], "Task C")
        store.transition_dispatch(d3["id"], OPERATOR, "in_progress")
        self.assertEqual(store.transition_dispatch(d3["id"], OPERATOR, "cancelled")["status"], "cancelled")

    def test_invalid_transitions_and_validation(self):
        """Dispatches. assigned->completed, completed->cancelled -> ValidationError; bad inputs error."""
        store, project, prime, sub = make_store()
        d = store.create_dispatch(OPERATOR, project["id"], "Task A")
        with self.assertRaises(ValidationError):
            store.transition_dispatch(d["id"], OPERATOR, "completed")
        store.transition_dispatch(d["id"], OPERATOR, "in_progress")
        store.transition_dispatch(d["id"], OPERATOR, "completed")
        with self.assertRaises(ValidationError):
            store.transition_dispatch(d["id"], OPERATOR, "cancelled")
        with self.assertRaises(ValidationError):
            store.create_dispatch(OPERATOR, project["id"], "")
        with self.assertRaises(NotFoundError):
            store.create_dispatch(OPERATOR, project["id"], "X", org_id="org-99")
        self.assertEqual(len(store.list_dispatches(VIEWER, project_id=project["id"])), 1)


if __name__ == "__main__":
    unittest.main()
