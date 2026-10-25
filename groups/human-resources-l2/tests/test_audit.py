"""Append-only audit log tests.

Traces to: Core function 12 (Audit log, AU-2/AU-3/AU-9) -- a baseline
hook included because the L2/Moderate baseline requires it.
"""

import os
import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, fresh_store, make_store
from hr.audit import AuditLog
from hr.errors import PermissionDenied

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRATCH = os.path.join(_GROUP_ROOT, "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 12 (AU-2/AU-3): audit entry shape and append-only behaviour."""

    def test_entry_keys_and_actor_normalisation(self):
        """Core 12 (AU-3): entries carry ts/actor/action/target/details; a User actor is normalised to its name."""
        log = AuditLog()
        entry = log.record(ADMIN, "person_create", "per-1", details={"person_ref": "x"})
        self.assertEqual(set(entry), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(log.entries()[0]["action"], "person_create")

    def test_append_only_copies(self):
        """Core 12 (AU-9): entries() returns copies; mutating them does not alter the log, and there is no mutation API."""
        log = AuditLog()
        log.record("alice", "a", "t")
        copied = log.entries()
        copied[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "a")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))
        self.assertFalse(hasattr(log, "clear"))

    def test_jsonl_persistence_reload(self):
        """Core 12 (AU-2): JSONL persistence in group scratch/ reloads on construction."""
        path = os.path.join(_SCRATCH, "audit-test.jsonl")
        if os.path.exists(path):
            os.remove(path)
        log = AuditLog(path=path)
        log.record("alice", "person_create", "per-1")
        log.record("bob", "position_create", "pos-1")
        reloaded = AuditLog(path=path)
        self.assertEqual(len(reloaded.entries()), 2)
        self.assertEqual(reloaded.entries()[1]["actor"], "bob")
        os.remove(path)

    def test_store_records_mutations(self):
        """Core 12 (AU-2): the store records each successful mutation action."""
        audit = AuditLog()
        store, position, person = make_store(audit=audit)
        store.create_vacancy(position["id"], "Analyst Opening", SPECIALIST)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("position_create", actions)
        self.assertIn("person_create", actions)
        self.assertIn("vacancy_create", actions)

    def test_failed_ops_record_nothing(self):
        """Core 12 / SI-10: a denied store op records no mutation entry."""
        audit = AuditLog()
        store, _, _ = make_store(audit=audit)
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            store.create_position("Nope", EMPLOYEE)
        self.assertEqual(len(audit.entries()), before)


if __name__ == "__main__":
    unittest.main()
