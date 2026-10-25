"""Case tests: lifecycle and SLA breach derivation.

Traces to: Core function 3 -- Cases; contract for
``ContactStore.create_case/assign_case/transition_case/get_case/
list_cases`` and the derived ``breached`` field (derived at read
time, never stored; education-training derived-status pattern).
"""

import unittest
from datetime import datetime, timezone

from contact_helpers import OPERATOR, VIEWER, fresh_store, make_store
from contact.errors import NotFoundError, PermissionDenied, ValidationError

PAST = "2020-01-01T00:00:00Z"
FUTURE = "2030-01-01T00:00:00Z"
NOW = "2025-06-01T00:00:00Z"


class TestCaseCreate(unittest.TestCase):
    """Core 3: Cases -- creation and validation."""

    def test_create_case_shape(self):
        """Core 3: Cases. create_case returns case- id, status open, breached False, links stored."""
        store, agent, contact, queue = make_store()
        case = store.create_case(
            OPERATOR, "claim", "Broken widget", contact_id=contact["id"],
            queue_id=queue["id"], agent_id=agent["id"], priority="high", due_at=FUTURE,
        )
        self.assertEqual(case["id"], "case-1")
        self.assertEqual(case["status"], "open")
        self.assertEqual(case["case_type"], "claim")
        self.assertEqual(case["priority"], "high")
        self.assertFalse(case["breached"])
        self.assertEqual(case["contact_id"], contact["id"])

    def test_create_case_defaults(self):
        """Core 3: Cases. priority defaults to normal; links/due_at default to None."""
        store = fresh_store()
        case = store.create_case(OPERATOR, "general", "Hello")
        self.assertEqual(case["priority"], "normal")
        self.assertIsNone(case["due_at"])
        self.assertIsNone(case["queue_id"])

    def test_all_case_types_accepted(self):
        """Core 3: Cases. case_type in {claim, callback, activity, inquiry, general} all accepted."""
        store = fresh_store()
        for i, case_type in enumerate(("claim", "callback", "activity", "inquiry", "general"), 1):
            case = store.create_case(OPERATOR, case_type, "s%d" % i)
            self.assertEqual(case["case_type"], case_type)

    def test_create_case_validation_no_id_on_failure(self):
        """Core 3: Cases (SI-10). Bad type/priority/subject/due_at -> ValidationError; unknown link -> NotFoundError; no id consumed."""
        store, agent, contact, queue = make_store()
        with self.assertRaises(ValidationError):
            store.create_case(OPERATOR, "bogus", "s")
        with self.assertRaises(ValidationError):
            store.create_case(OPERATOR, "claim", "")
        with self.assertRaises(ValidationError):
            store.create_case(OPERATOR, "claim", "s", priority="urgent")
        with self.assertRaises(ValidationError):
            store.create_case(OPERATOR, "claim", "s", due_at="not-a-date")
        with self.assertRaises(NotFoundError):
            store.create_case(OPERATOR, "claim", "s", contact_id="ct-999")
        with self.assertRaises(NotFoundError):
            store.create_case(OPERATOR, "claim", "s", queue_id="que-999")
        with self.assertRaises(NotFoundError):
            store.create_case(OPERATOR, "claim", "s", agent_id="agt-999")
        case = store.create_case(OPERATOR, "claim", "ok")
        self.assertEqual(case["id"], "case-1")

    def test_viewer_cannot_create_case(self):
        """Core 3/11: Cases/RBAC. Viewer create_case -> PermissionDenied, no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_case(VIEWER, "claim", "s")
        self.assertEqual(store.create_case(OPERATOR, "claim", "s")["id"], "case-1")


class TestCaseAssignTransition(unittest.TestCase):
    """Core 3: Cases -- assignment and lifecycle transitions."""

    def test_assign_case(self):
        """Core 3: Cases. assign_case sets agent and/or queue; at least one is required."""
        store, agent, contact, queue = make_store()
        case = store.create_case(OPERATOR, "inquiry", "s")
        updated = store.assign_case(case["id"], OPERATOR, agent_id=agent["id"])
        self.assertEqual(updated["agent_id"], agent["id"])
        updated = store.assign_case(case["id"], OPERATOR, queue_id=queue["id"])
        self.assertEqual(updated["queue_id"], queue["id"])
        self.assertEqual(updated["agent_id"], agent["id"])
        with self.assertRaises(ValidationError):
            store.assign_case(case["id"], OPERATOR)
        with self.assertRaises(NotFoundError):
            store.assign_case(case["id"], OPERATOR, agent_id="agt-999")
        with self.assertRaises(NotFoundError):
            store.assign_case("case-999", OPERATOR, agent_id=agent["id"])

    def test_full_lifecycle_and_reopen(self):
        """Core 3: Cases. open->in_progress->resolved->in_progress (reopen)->resolved->closed."""
        store = fresh_store()
        case = store.create_case(OPERATOR, "general", "s")
        cid = case["id"]
        self.assertEqual(store.transition_case(cid, OPERATOR, "in_progress")["status"], "in_progress")
        self.assertEqual(store.transition_case(cid, OPERATOR, "resolved")["status"], "resolved")
        self.assertEqual(store.transition_case(cid, OPERATOR, "in_progress")["status"], "in_progress")
        self.assertEqual(store.transition_case(cid, OPERATOR, "resolved")["status"], "resolved")
        self.assertEqual(store.transition_case(cid, OPERATOR, "closed")["status"], "closed")

    def test_cancel_paths(self):
        """Core 3: Cases. open->cancelled and in_progress->open/cancelled are valid."""
        store = fresh_store()
        c1 = store.create_case(OPERATOR, "general", "a")
        self.assertEqual(store.transition_case(c1["id"], OPERATOR, "cancelled")["status"], "cancelled")
        c2 = store.create_case(OPERATOR, "general", "b")
        store.transition_case(c2["id"], OPERATOR, "in_progress")
        self.assertEqual(store.transition_case(c2["id"], OPERATOR, "open")["status"], "open")
        store.transition_case(c2["id"], OPERATOR, "in_progress")
        self.assertEqual(store.transition_case(c2["id"], OPERATOR, "cancelled")["status"], "cancelled")

    def test_invalid_transitions(self):
        """Core 3: Cases. Invalid transitions -> ValidationError and status unchanged; terminal states have no exits."""
        store = fresh_store()
        case = store.create_case(OPERATOR, "general", "s")
        cid = case["id"]
        for bad in ("resolved", "closed", "open", "bogus"):
            with self.assertRaises(ValidationError):
                store.transition_case(cid, OPERATOR, bad)
        self.assertEqual(store.get_case(cid, OPERATOR)["status"], "open")
        store.transition_case(cid, OPERATOR, "cancelled")
        with self.assertRaises(ValidationError):
            store.transition_case(cid, OPERATOR, "open")
        with self.assertRaises(NotFoundError):
            store.transition_case("case-999", OPERATOR, "open")


class TestBreachDerivation(unittest.TestCase):
    """Core 3: Cases -- SLA breach is derived at read time, never stored."""

    def test_overdue_open_case_breached(self):
        """Core 3: Cases (derived status). Past-due open case reads breached=True at a later now."""
        store = fresh_store()
        case = store.create_case(OPERATOR, "claim", "s", due_at=PAST)
        self.assertTrue(store.get_case(case["id"], OPERATOR, now=NOW)["breached"])
        self.assertTrue(store.list_cases(OPERATOR, now=NOW)[0]["breached"])

    def test_not_yet_due_and_no_due_at_not_breached(self):
        """Core 3: Cases (derived status). Future due_at, exactly-at due_at, and no due_at read breached=False."""
        store = fresh_store()
        future = store.create_case(OPERATOR, "claim", "f", due_at=FUTURE)
        nodue = store.create_case(OPERATOR, "claim", "n")
        exact = store.create_case(OPERATOR, "claim", "e", due_at=NOW)
        self.assertFalse(store.get_case(future["id"], OPERATOR, now=NOW)["breached"])
        self.assertFalse(store.get_case(nodue["id"], OPERATOR, now=NOW)["breached"])
        self.assertFalse(store.get_case(exact["id"], OPERATOR, now=NOW)["breached"])

    def test_terminal_statuses_not_breached(self):
        """Core 3: Cases (derived status). Past-due resolved/closed/cancelled cases read breached=False."""
        store = fresh_store()
        resolved = store.create_case(OPERATOR, "claim", "r", due_at=PAST)
        store.transition_case(resolved["id"], OPERATOR, "in_progress")
        store.transition_case(resolved["id"], OPERATOR, "resolved")
        self.assertFalse(store.get_case(resolved["id"], OPERATOR, now=NOW)["breached"])
        store.transition_case(resolved["id"], OPERATOR, "closed")
        self.assertFalse(store.get_case(resolved["id"], OPERATOR, now=NOW)["breached"])
        cancelled = store.create_case(OPERATOR, "claim", "c", due_at=PAST)
        store.transition_case(cancelled["id"], OPERATOR, "cancelled")
        self.assertFalse(store.get_case(cancelled["id"], OPERATOR, now=NOW)["breached"])

    def test_in_progress_past_due_breached(self):
        """Core 3: Cases (derived status). Past-due in_progress case reads breached=True."""
        store = fresh_store()
        case = store.create_case(OPERATOR, "claim", "s", due_at=PAST)
        store.transition_case(case["id"], OPERATOR, "in_progress")
        self.assertTrue(store.get_case(case["id"], OPERATOR, now=NOW)["breached"])

    def test_now_forms(self):
        """Core 3: Cases (derived status). now accepts ISO string, datetime, and None (current UTC)."""
        store = fresh_store()
        case = store.create_case(OPERATOR, "claim", "s", due_at=PAST)
        self.assertTrue(store.get_case(
            case["id"], OPERATOR, now=datetime(2025, 6, 1, tzinfo=timezone.utc))["breached"])
        self.assertTrue(store.get_case(case["id"], OPERATOR, now=NOW)["breached"])
        self.assertTrue(store.get_case(case["id"], OPERATOR)["breached"])
        with self.assertRaises(ValidationError):
            store.get_case(case["id"], OPERATOR, now="junk")
        with self.assertRaises(ValidationError):
            store.get_case(case["id"], OPERATOR, now=12345)

    def test_breach_is_derived_not_stored(self):
        """Core 3: Cases (derived status). Same stored case reads breached False before due and True after -- derivation, not storage."""
        store = fresh_store()
        case = store.create_case(OPERATOR, "claim", "s", due_at="2025-01-01T00:00:00Z")
        self.assertFalse(store.get_case(case["id"], OPERATOR, now="2024-06-01T00:00:00Z")["breached"])
        self.assertTrue(store.get_case(case["id"], OPERATOR, now="2026-06-01T00:00:00Z")["breached"])
        self.assertNotIn("breached", store._cases[case["id"]])

    def test_list_filters(self):
        """Core 3: Cases. list_cases filters by status, queue_id, and case_type."""
        store, agent, contact, queue = make_store()
        c1 = store.create_case(OPERATOR, "claim", "a", queue_id=queue["id"])
        c2 = store.create_case(OPERATOR, "inquiry", "b")
        store.transition_case(c2["id"], OPERATOR, "in_progress")
        self.assertEqual([c["id"] for c in store.list_cases(OPERATOR, status="open")], [c1["id"]])
        self.assertEqual([c["id"] for c in store.list_cases(OPERATOR, queue_id=queue["id"])], [c1["id"]])
        self.assertEqual([c["id"] for c in store.list_cases(OPERATOR, case_type="inquiry")], [c2["id"]])
        self.assertEqual(len(store.list_cases(VIEWER)), 2)


if __name__ == "__main__":
    unittest.main()
