"""Append-only audit log tests.

Traces to: Core function 14 (Audit log) -- ``lms/audit.py``:
record(actor, action, target, details=None) -> {ts, actor, action,
target, details}; entries() returns copies; optional JSONL path
persists entries across construction. The store records each
successful mutation and records nothing for failed operations.
"""

import os
import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, fresh_store, make_store
from lms.audit import AuditLog
from lms.errors import PermissionDenied, ValidationError

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRATCH = os.path.join(_GROUP_ROOT, "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 14: audit entry shape and append-only behaviour."""

    def test_entry_keys_and_actor_normalisation(self):
        """Core 14: entries carry exactly ts/actor/action/target/details; a User actor is normalised to its name; a string actor is kept verbatim."""
        log = AuditLog()
        entry = log.record(ADMIN, "course_create", "crs-1", details={"title": "X"})
        self.assertEqual(set(entry), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["details"], {"title": "X"})
        plain = log.record("system", "boot", "svc")
        self.assertEqual(plain["actor"], "system")
        self.assertIsNone(plain["details"])
        self.assertEqual(log.entries()[0]["action"], "course_create")

    def test_append_only_copies(self):
        """Core 14: entries() returns copies; mutating a returned entry does not alter the log, and there is no mutation API."""
        log = AuditLog()
        log.record("alice", "a", "t")
        copied = log.entries()
        copied[0]["action"] = "tampered"
        copied.append({"ts": "x", "actor": "mallory", "action": "fake",
                       "target": "t", "details": None})
        self.assertEqual(len(log.entries()), 1)
        self.assertEqual(log.entries()[0]["action"], "a")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))
        self.assertFalse(hasattr(log, "clear"))
        returned = log.record("alice", "b", "t")
        returned["action"] = "tampered"
        self.assertEqual(log.entries()[1]["action"], "b")

    def test_jsonl_persistence_reload(self):
        """Core 14: JSONL persistence in group scratch/ reloads on construction; the scratch file is cleaned up afterwards."""
        path = os.path.join(_SCRATCH, "audit-test-lms.jsonl")
        if os.path.exists(path):
            os.remove(path)
        try:
            log = AuditLog(path=path)
            log.record("alice", "course_create", "crs-1")
            log.record("bob", "registration_create", "reg-1")
            reloaded = AuditLog(path=path)
            self.assertEqual(len(reloaded.entries()), 2)
            self.assertEqual(reloaded.entries()[1]["actor"], "bob")
            self.assertEqual(reloaded.entries()[1]["target"], "reg-1")
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_store_records_mutations(self):
        """Core 14: the store records each successful mutation action, targeted at the created record."""
        audit = AuditLog()
        store, learner, course = make_store(audit=audit)
        event = store.create_event("Briefing", "2026-07-01T09:00:00Z", INSTRUCTOR,
                                   course_id=course["id"])
        registration = store.register_learner(event["id"], "carol", INSTRUCTOR)
        store.record_progress("carol", course["id"], "in_progress", INSTRUCTOR)
        targets = [e["target"] for e in audit.entries()]
        for record in (learner, course, event, registration):
            self.assertIn(record["id"], targets)
        actions = [e["action"] for e in audit.entries()]
        self.assertGreaterEqual(len(actions), 4)
        self.assertTrue(all(isinstance(a, str) and a for a in actions))
        actors = {e["actor"] for e in audit.entries()}
        self.assertIn("alice", actors)
        self.assertIn("bob", actors)

    def test_failed_ops_record_nothing(self):
        """Core 14: a denied or invalid store op records no audit entry and changes nothing."""
        audit = AuditLog()
        store, learner, course = make_store(audit=audit)
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            store.create_course("Nope", LEARNER)
        with self.assertRaises(ValidationError):
            store.create_learner("carol", "Duplicate Carol", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_course("", ADMIN)
        self.assertEqual(len(audit.entries()), before)


if __name__ == "__main__":
    unittest.main()
