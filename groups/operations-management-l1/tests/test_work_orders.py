"""Work-order tests: lifecycle and overdue derivation.

Traces to: Core function 4 -- Work orders; contract for
``OpsStore.create_work_order/assign_work_order/transition_work_order/
get_work_order/list_work_orders`` and the derived ``overdue`` field
(derived at read time, never stored); AU-2, CM-6, SI-12 (partial),
AU-6/CA-7 for derivation.
"""

import unittest
from datetime import datetime, timezone

from opsmgmt_helpers import OPERATOR, VIEWER, fresh_store, make_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError

PAST = "2020-01-01T00:00:00Z"
FUTURE = "2030-01-01T00:00:00Z"
NOW = "2025-06-01T00:00:00Z"


class TestWorkOrderCreate(unittest.TestCase):
    """Core 4: Work orders -- creation and validation."""

    def test_create_work_order_shape(self):
        """Core 4: Work orders. create_work_order returns wo- id, status open, overdue False, links stored."""
        store, person, organization, project = make_store()
        asset = store.create_asset("Pump", OPERATOR, project_id=project["id"])
        wo = store.create_work_order(
            OPERATOR, "maintenance", "Fix pump", project_id=project["id"],
            asset_id=asset["id"], person_id=person["id"], priority="high", due_at=FUTURE,
        )
        self.assertEqual(wo["id"], "wo-1")
        self.assertEqual(wo["status"], "open")
        self.assertEqual(wo["work_type"], "maintenance")
        self.assertEqual(wo["subject"], "Fix pump")
        self.assertEqual(wo["priority"], "high")
        self.assertFalse(wo["overdue"])
        self.assertEqual(wo["project_id"], project["id"])
        self.assertEqual(wo["asset_id"], asset["id"])
        self.assertEqual(wo["person_id"], person["id"])
        self.assertEqual(wo["created_by"], "bob")

    def test_create_work_order_defaults(self):
        """Core 4: Work orders. priority defaults to normal; links/due_at default to None."""
        store = fresh_store()
        wo = store.create_work_order(OPERATOR, "general", "Hello")
        self.assertEqual(wo["priority"], "normal")
        self.assertIsNone(wo["due_at"])
        self.assertIsNone(wo["project_id"])
        self.assertIsNone(wo["asset_id"])
        self.assertIsNone(wo["person_id"])

    def test_all_work_types_accepted(self):
        """Core 4: Work orders. work_type in {inspection, maintenance, field_operation, task, general} all accepted."""
        store = fresh_store()
        for i, work_type in enumerate(
                ("inspection", "maintenance", "field_operation", "task", "general"), 1):
            wo = store.create_work_order(OPERATOR, work_type, "s%d" % i)
            self.assertEqual(wo["work_type"], work_type)

    def test_all_priorities_accepted(self):
        """Core 4: Work orders. priority in {low, normal, high, critical} all accepted."""
        store = fresh_store()
        for priority in ("low", "normal", "high", "critical"):
            wo = store.create_work_order(OPERATOR, "task", "s", priority=priority)
            self.assertEqual(wo["priority"], priority)

    def test_create_work_order_validation_no_id_on_failure(self):
        """Core 4: Work orders (SI-10). Bad type/priority/subject/due_at -> ValidationError; unknown link -> NotFoundError; no id consumed."""
        store, person, organization, project = make_store()
        with self.assertRaises(ValidationError):
            store.create_work_order(OPERATOR, "bogus", "s")
        with self.assertRaises(ValidationError):
            store.create_work_order(OPERATOR, "task", "")
        with self.assertRaises(ValidationError):
            store.create_work_order(OPERATOR, "task", "s", priority="urgent")
        with self.assertRaises(ValidationError):
            store.create_work_order(OPERATOR, "task", "s", due_at="not-a-date")
        with self.assertRaises(ValidationError):
            store.create_work_order(OPERATOR, "task", "s", due_at=12345)
        with self.assertRaises(NotFoundError):
            store.create_work_order(OPERATOR, "task", "s", project_id="proj-999")
        with self.assertRaises(NotFoundError):
            store.create_work_order(OPERATOR, "task", "s", asset_id="ast-999")
        with self.assertRaises(NotFoundError):
            store.create_work_order(OPERATOR, "task", "s", person_id="per-999")
        wo = store.create_work_order(OPERATOR, "task", "ok")
        self.assertEqual(wo["id"], "wo-1")

    def test_viewer_cannot_create_work_order(self):
        """Core 4/11: Work orders/RBAC. Viewer create_work_order -> PermissionDenied, no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_work_order(VIEWER, "task", "s")
        self.assertEqual(store.create_work_order(OPERATOR, "task", "s")["id"], "wo-1")


class TestWorkOrderAssignTransition(unittest.TestCase):
    """Core 4: Work orders -- assignment and lifecycle transitions."""

    def test_assign_work_order(self):
        """Core 4: Work orders. assign_work_order sets person and/or project; at least one is required."""
        store, person, organization, project = make_store()
        wo = store.create_work_order(OPERATOR, "task", "s")
        updated = store.assign_work_order(wo["id"], OPERATOR, person_id=person["id"])
        self.assertEqual(updated["person_id"], person["id"])
        updated = store.assign_work_order(wo["id"], OPERATOR, project_id=project["id"])
        self.assertEqual(updated["project_id"], project["id"])
        self.assertEqual(updated["person_id"], person["id"])
        with self.assertRaises(ValidationError):
            store.assign_work_order(wo["id"], OPERATOR)
        with self.assertRaises(NotFoundError):
            store.assign_work_order(wo["id"], OPERATOR, person_id="per-999")
        with self.assertRaises(NotFoundError):
            store.assign_work_order(wo["id"], OPERATOR, project_id="proj-999")
        with self.assertRaises(NotFoundError):
            store.assign_work_order("wo-999", OPERATOR, person_id=person["id"])

    def test_full_lifecycle_and_reopen(self):
        """Core 4: Work orders. open->in_progress->completed->in_progress (reopen)->completed->closed."""
        store = fresh_store()
        wo = store.create_work_order(OPERATOR, "general", "s")
        wid = wo["id"]
        self.assertEqual(store.transition_work_order(wid, OPERATOR, "in_progress")["status"], "in_progress")
        self.assertEqual(store.transition_work_order(wid, OPERATOR, "completed")["status"], "completed")
        self.assertEqual(store.transition_work_order(wid, OPERATOR, "in_progress")["status"], "in_progress")
        self.assertEqual(store.transition_work_order(wid, OPERATOR, "completed")["status"], "completed")
        self.assertEqual(store.transition_work_order(wid, OPERATOR, "closed")["status"], "closed")

    def test_cancel_paths(self):
        """Core 4: Work orders. open->cancelled and in_progress->open/cancelled are valid."""
        store = fresh_store()
        w1 = store.create_work_order(OPERATOR, "general", "a")
        self.assertEqual(store.transition_work_order(w1["id"], OPERATOR, "cancelled")["status"], "cancelled")
        w2 = store.create_work_order(OPERATOR, "general", "b")
        store.transition_work_order(w2["id"], OPERATOR, "in_progress")
        self.assertEqual(store.transition_work_order(w2["id"], OPERATOR, "open")["status"], "open")
        store.transition_work_order(w2["id"], OPERATOR, "in_progress")
        self.assertEqual(store.transition_work_order(w2["id"], OPERATOR, "cancelled")["status"], "cancelled")

    def test_invalid_transitions(self):
        """Core 4: Work orders. Invalid transitions -> ValidationError and status unchanged; terminal states have no exits."""
        store = fresh_store()
        wo = store.create_work_order(OPERATOR, "general", "s")
        wid = wo["id"]
        for bad in ("completed", "closed", "open", "bogus"):
            with self.assertRaises(ValidationError):
                store.transition_work_order(wid, OPERATOR, bad)
        self.assertEqual(store.get_work_order(wid, OPERATOR)["status"], "open")
        store.transition_work_order(wid, OPERATOR, "cancelled")
        with self.assertRaises(ValidationError):
            store.transition_work_order(wid, OPERATOR, "open")
        # closed is terminal too
        w2 = store.create_work_order(OPERATOR, "general", "t")
        store.transition_work_order(w2["id"], OPERATOR, "in_progress")
        store.transition_work_order(w2["id"], OPERATOR, "completed")
        store.transition_work_order(w2["id"], OPERATOR, "closed")
        with self.assertRaises(ValidationError):
            store.transition_work_order(w2["id"], OPERATOR, "in_progress")
        with self.assertRaises(NotFoundError):
            store.transition_work_order("wo-999", OPERATOR, "open")
        with self.assertRaises(NotFoundError):
            store.get_work_order("wo-999", OPERATOR)


class TestOverdueDerivation(unittest.TestCase):
    """Core 4: Work orders -- overdue is derived at read time, never stored."""

    def test_overdue_open_work_order_overdue(self):
        """Core 4: Work orders (derived status, AU-6/CA-7/CM-6). Past-due open work order reads overdue=True at a later now."""
        store = fresh_store()
        wo = store.create_work_order(OPERATOR, "task", "s", due_at=PAST)
        self.assertTrue(store.get_work_order(wo["id"], OPERATOR, now=NOW)["overdue"])
        self.assertTrue(store.list_work_orders(OPERATOR, now=NOW)[0]["overdue"])

    def test_in_progress_past_due_overdue(self):
        """Core 4: Work orders (derived status). Past-due in_progress work order reads overdue=True."""
        store = fresh_store()
        wo = store.create_work_order(OPERATOR, "task", "s", due_at=PAST)
        store.transition_work_order(wo["id"], OPERATOR, "in_progress")
        self.assertTrue(store.get_work_order(wo["id"], OPERATOR, now=NOW)["overdue"])

    def test_not_yet_due_and_no_due_at_not_overdue(self):
        """Core 4: Work orders (derived status). Future due_at, exactly-at due_at, and no due_at read overdue=False."""
        store = fresh_store()
        future = store.create_work_order(OPERATOR, "task", "f", due_at=FUTURE)
        nodue = store.create_work_order(OPERATOR, "task", "n")
        exact = store.create_work_order(OPERATOR, "task", "e", due_at=NOW)
        self.assertFalse(store.get_work_order(future["id"], OPERATOR, now=NOW)["overdue"])
        self.assertFalse(store.get_work_order(nodue["id"], OPERATOR, now=NOW)["overdue"])
        self.assertFalse(store.get_work_order(exact["id"], OPERATOR, now=NOW)["overdue"])

    def test_completed_closed_cancelled_never_overdue(self):
        """Core 4: Work orders (derived status). Past-due completed/closed/cancelled work orders read overdue=False."""
        store = fresh_store()
        completed = store.create_work_order(OPERATOR, "task", "c", due_at=PAST)
        store.transition_work_order(completed["id"], OPERATOR, "in_progress")
        store.transition_work_order(completed["id"], OPERATOR, "completed")
        self.assertFalse(store.get_work_order(completed["id"], OPERATOR, now=NOW)["overdue"])
        store.transition_work_order(completed["id"], OPERATOR, "closed")
        self.assertFalse(store.get_work_order(completed["id"], OPERATOR, now=NOW)["overdue"])
        cancelled = store.create_work_order(OPERATOR, "task", "x", due_at=PAST)
        store.transition_work_order(cancelled["id"], OPERATOR, "cancelled")
        self.assertFalse(store.get_work_order(cancelled["id"], OPERATOR, now=NOW)["overdue"])

    def test_now_forms(self):
        """Core 4: Work orders (derived status). now accepts ISO string, datetime, and None (current UTC); bad now -> ValidationError."""
        store = fresh_store()
        wo = store.create_work_order(OPERATOR, "task", "s", due_at=PAST)
        self.assertTrue(store.get_work_order(
            wo["id"], OPERATOR, now=datetime(2025, 6, 1, tzinfo=timezone.utc))["overdue"])
        # naive datetime is treated as UTC per the implementation
        self.assertTrue(store.get_work_order(
            wo["id"], OPERATOR, now=datetime(2025, 6, 1))["overdue"])
        self.assertTrue(store.get_work_order(wo["id"], OPERATOR, now=NOW)["overdue"])
        self.assertTrue(store.get_work_order(wo["id"], OPERATOR)["overdue"])
        with self.assertRaises(ValidationError):
            store.get_work_order(wo["id"], OPERATOR, now="junk")
        with self.assertRaises(ValidationError):
            store.get_work_order(wo["id"], OPERATOR, now=12345)

    def test_overdue_is_derived_not_stored(self):
        """Core 4: Work orders (derived status). Same stored record reads overdue False before due and True after; stored record has no 'overdue' key."""
        store = fresh_store()
        wo = store.create_work_order(OPERATOR, "task", "s", due_at="2025-01-01T00:00:00Z")
        self.assertFalse(store.get_work_order(wo["id"], OPERATOR, now="2024-06-01T00:00:00Z")["overdue"])
        self.assertTrue(store.get_work_order(wo["id"], OPERATOR, now="2026-06-01T00:00:00Z")["overdue"])
        # Inspect the stored record directly: no 'overdue' key is stored.
        self.assertNotIn("overdue", store._work_orders[wo["id"]])
        # A second read through the view still derives it (not a stored flag).
        self.assertTrue(store.get_work_order(wo["id"], OPERATOR, now=NOW)["overdue"])
        self.assertNotIn("overdue", store._work_orders[wo["id"]])

    def test_list_filters(self):
        """Core 4: Work orders. list_work_orders filters by status, project_id, and work_type."""
        store, person, organization, project = make_store()
        w1 = store.create_work_order(OPERATOR, "task", "a", project_id=project["id"])
        w2 = store.create_work_order(OPERATOR, "maintenance", "b")
        store.transition_work_order(w2["id"], OPERATOR, "in_progress")
        self.assertEqual([w["id"] for w in store.list_work_orders(OPERATOR, status="open")], [w1["id"]])
        self.assertEqual([w["id"] for w in store.list_work_orders(OPERATOR, project_id=project["id"])], [w1["id"]])
        self.assertEqual([w["id"] for w in store.list_work_orders(OPERATOR, work_type="maintenance")], [w2["id"]])
        self.assertEqual(len(store.list_work_orders(VIEWER)), 2)


if __name__ == "__main__":
    unittest.main()
