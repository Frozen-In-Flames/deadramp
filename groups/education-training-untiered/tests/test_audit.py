"""Append-only audit log tests.

Traces to: Core function 10 (Audit log, AU-2/AU-3/AU-9) -- a baseline
hook with 0/8 descriptive claims in the union spec, included because
the L2/Moderate baseline requires it.
"""

import os
import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, fresh_store, make_store
from learn.audit import AuditLog
from learn.errors import PermissionDenied

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRATCH = os.path.join(_GROUP_ROOT, "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 10 (AU-2/AU-3): audit entry shape and append-only behaviour."""

    def test_entry_keys_and_actor_normalisation(self):
        """Core 10 (AU-3): entries carry ts/actor/action/target/details; a User actor is normalised to its name."""
        log = AuditLog()
        entry = log.record(ADMIN, "course_create", "crs-1", details={"title": "X"})
        self.assertEqual(set(entry), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(log.entries()[0]["action"], "course_create")

    def test_append_only_copies(self):
        """Core 10 (AU-9): entries() returns copies; mutating them does not alter the log, and there is no mutation API."""
        log = AuditLog()
        log.record("alice", "a", "t")
        copied = log.entries()
        copied[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "a")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))
        self.assertFalse(hasattr(log, "clear"))

    def test_jsonl_persistence_reload(self):
        """Core 10 (AU-2): JSONL persistence in group scratch/ reloads on construction."""
        path = os.path.join(_SCRATCH, "audit-test.jsonl")
        if os.path.exists(path):
            os.remove(path)
        log = AuditLog(path=path)
        log.record("alice", "course_create", "crs-1")
        log.record("bob", "enrollment_create", "enr-1")
        reloaded = AuditLog(path=path)
        self.assertEqual(len(reloaded.entries()), 2)
        self.assertEqual(reloaded.entries()[1]["actor"], "bob")
        os.remove(path)

    def test_store_records_mutations(self):
        """Core 10 (AU-2): the store records each successful mutation action."""
        audit = AuditLog()
        store, course = make_store(audit=audit)
        store.create_enrollment("carol", course["id"], INSTRUCTOR)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("course_create", actions)
        self.assertIn("enrollment_create", actions)

    def test_failed_ops_record_nothing(self):
        """Core 10 / SI-10: a denied store op records no mutation entry."""
        audit = AuditLog()
        store, course = make_store(audit=audit)
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            store.create_course("Nope", LEARNER)
        self.assertEqual(len(audit.entries()), before)


if __name__ == "__main__":
    unittest.main()
