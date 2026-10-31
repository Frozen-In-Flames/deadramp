"""Core function 14 (audit half): the append-only audit log --
mutations recorded, failures not recorded, denied attempts the
service layer's responsibility, ``audit_read`` gated on the
``audit_read`` permission (AU-2/AU-3/AU-6/AU-9 at the High
baseline; the hash chain itself is exercised in
test_audit_chain.py).
"""

import json
import os
import tempfile
import unittest

from storage.audit import AuditLog
from storage.errors import PermissionDenied, ValidationError

from storage_helpers import (ADMIN, AUDITOR, OPERATOR, VIEWER,
                             make_archive, make_message, make_store)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def test_mutations_are_recorded(self):
        org, policy, collection = make_archive(self.store)
        make_message(self.store, collection)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertEqual(actions, ["organization_create", "policy_create",
                                   "collection_create", "message_archive"])
        entry = self.audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["target"], org["id"])
        self.assertIn("ts", entry)

    def test_failures_record_nothing(self):
        with self.assertRaises(ValidationError):
            self.store.create_policy(ADMIN, "bad", -1)
        with self.assertRaises(PermissionDenied):
            self.store.create_policy(VIEWER, "nope", 30)
        self.assertEqual(self.audit.entries(), [])

    def test_audit_read_requires_audit_read_permission(self):
        """AU-6 / AC-5 [L3]: admin and the separated auditor role
        hold ``audit_read``; operator and viewer do not."""
        make_archive(self.store)
        result = self.store.audit_read(ADMIN)
        self.assertEqual(result["count"], 3)
        result = self.store.audit_read(AUDITOR)
        self.assertEqual(result["count"], 3)
        with self.assertRaises(PermissionDenied):
            self.store.audit_read(OPERATOR)
        with self.assertRaises(PermissionDenied):
            self.store.audit_read(VIEWER)

    def test_log_is_append_only_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "organization_create", "org-1")
            log.record("bob", "message_archive", "msg-1")
            reloaded = AuditLog(path)
            entries = reloaded.entries()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[1]["action"], "message_archive")
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(lines), 2)
            # there is no mutation API on the log
            self.assertFalse(hasattr(log, "delete"))
            self.assertFalse(hasattr(log, "update"))
            self.assertFalse(hasattr(log, "clear"))

    def test_entries_are_copies(self):
        self.audit.record("alice", "x", "y", {"k": "v"})
        entries = self.audit.entries()
        entries[0]["action"] = "tampered"
        entries[0]["details"]["k"] = "tampered"
        fresh = self.audit.entries()
        self.assertEqual(fresh[0]["action"], "x")
        self.assertEqual(fresh[0]["details"]["k"], "v")


if __name__ == "__main__":
    unittest.main()
