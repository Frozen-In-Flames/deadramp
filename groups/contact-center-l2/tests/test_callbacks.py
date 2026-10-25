"""Callback tests: scheduling and derived state.

Traces to: Core function 4 -- Callbacks; contract for
``ContactStore.schedule_callback/complete_callback/cancel_callback/
get_callback/list_callbacks`` and the derived ``state`` field
(stored status kept in ``status``; state derived at read time).
Sibling claim family: Mindful by Medallia callback records.
"""

import unittest

from contact_helpers import OPERATOR, VIEWER, fresh_store, make_store
from contact.errors import NotFoundError, PermissionDenied, ValidationError

PAST = "2020-01-01T00:00:00Z"
FUTURE = "2030-01-01T00:00:00Z"
NOW = "2025-06-01T00:00:00Z"


class TestSchedule(unittest.TestCase):
    """Core 4: Callbacks -- scheduling."""

    def test_schedule_shape(self):
        """Core 4: Callbacks. schedule_callback returns cb- id, stored status scheduled, derived state scheduled."""
        store, agent, contact, queue = make_store()
        cb = store.schedule_callback(OPERATOR, contact["id"], FUTURE, note="call back")
        self.assertEqual(cb["id"], "cb-1")
        self.assertEqual(cb["status"], "scheduled")
        self.assertEqual(cb["state"], "scheduled")
        self.assertEqual(cb["contact_id"], contact["id"])
        self.assertIsNone(cb["outcome"])

    def test_schedule_validation_no_id_on_failure(self):
        """Core 4: Callbacks (SI-10). Bad requested_for -> ValidationError; unknown links -> NotFoundError; no id consumed."""
        store, agent, contact, queue = make_store()
        with self.assertRaises(ValidationError):
            store.schedule_callback(OPERATOR, contact["id"], "not-a-date")
        with self.assertRaises(NotFoundError):
            store.schedule_callback(OPERATOR, "ct-999", FUTURE)
        with self.assertRaises(NotFoundError):
            store.schedule_callback(OPERATOR, contact["id"], FUTURE, case_id="case-999")
        with self.assertRaises(NotFoundError):
            store.schedule_callback(OPERATOR, contact["id"], FUTURE, agent_id="agt-999")
        cb = store.schedule_callback(OPERATOR, contact["id"], FUTURE)
        self.assertEqual(cb["id"], "cb-1")

    def test_viewer_cannot_schedule(self):
        """Core 4/11: Callbacks/RBAC. Viewer schedule_callback -> PermissionDenied."""
        store, agent, contact, queue = make_store()
        with self.assertRaises(PermissionDenied):
            store.schedule_callback(VIEWER, contact["id"], FUTURE)


class TestDerivedState(unittest.TestCase):
    """Core 4: Callbacks -- state derived at read time."""

    def test_overdue_derivation(self):
        """Core 4: Callbacks (derived status). Past requested_for reads state overdue while stored status stays scheduled."""
        store, agent, contact, queue = make_store()
        cb = store.schedule_callback(OPERATOR, contact["id"], PAST)
        got = store.get_callback(cb["id"], OPERATOR, now=NOW)
        self.assertEqual(got["state"], "overdue")
        self.assertEqual(got["status"], "scheduled")
        listed = store.list_callbacks(OPERATOR, now=NOW)
        self.assertEqual(listed[0]["state"], "overdue")
        self.assertNotIn("state", store._callbacks[cb["id"]])

    def test_scheduled_state_and_now_forms(self):
        """Core 4: Callbacks (derived status). Future requested_for reads scheduled; now accepts string/datetime/None."""
        store, agent, contact, queue = make_store()
        cb = store.schedule_callback(OPERATOR, contact["id"], FUTURE)
        self.assertEqual(store.get_callback(cb["id"], OPERATOR, now=NOW)["state"], "scheduled")
        from datetime import datetime, timezone
        self.assertEqual(store.get_callback(
            cb["id"], OPERATOR, now=datetime(2025, 6, 1, tzinfo=timezone.utc))["state"], "scheduled")
        self.assertEqual(store.get_callback(cb["id"], OPERATOR)["state"], "scheduled")

    def test_completed_and_cancelled_states(self):
        """Core 4: Callbacks (derived status). Completed/cancelled callbacks keep that state even when past due."""
        store, agent, contact, queue = make_store()
        cb = store.schedule_callback(OPERATOR, contact["id"], PAST)
        done = store.complete_callback(cb["id"], OPERATOR, outcome="reached")
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["outcome"], "reached")
        self.assertEqual(store.get_callback(cb["id"], OPERATOR, now=NOW)["state"], "completed")
        cb2 = store.schedule_callback(OPERATOR, contact["id"], PAST)
        store.cancel_callback(cb2["id"], OPERATOR)
        got2 = store.get_callback(cb2["id"], OPERATOR, now=NOW)
        self.assertEqual(got2["status"], "cancelled")
        self.assertEqual(got2["state"], "cancelled")


class TestTerminalGuards(unittest.TestCase):
    """Core 4: Callbacks -- terminal transitions only from scheduled."""

    def test_complete_twice_and_cancel_after_complete(self):
        """Core 4: Callbacks. Completing/cancelling a completed callback -> ValidationError."""
        store, agent, contact, queue = make_store()
        cb = store.schedule_callback(OPERATOR, contact["id"], FUTURE)
        store.complete_callback(cb["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.complete_callback(cb["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.cancel_callback(cb["id"], OPERATOR)

    def test_transitions_after_cancel(self):
        """Core 4: Callbacks. Completing/cancelling a cancelled callback -> ValidationError."""
        store, agent, contact, queue = make_store()
        cb = store.schedule_callback(OPERATOR, contact["id"], FUTURE)
        store.cancel_callback(cb["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.complete_callback(cb["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.cancel_callback(cb["id"], OPERATOR)

    def test_unknown_callback_not_found(self):
        """Core 4: Callbacks. Unknown callback id -> NotFoundError on get/complete/cancel."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_callback("cb-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            store.complete_callback("cb-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            store.cancel_callback("cb-999", OPERATOR)


if __name__ == "__main__":
    unittest.main()
