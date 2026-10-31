"""Audit log — core function 8 (UNION-SPEC.md).

Append-only entries with actor/action/target/details; entries are
returned as copies; JSONL persistence round-trips; every store
mutation is recorded.
"""

import os
import tempfile
import unittest

from manufacturing.audit import AuditLog

import manufacturing_helpers as H


class TestAuditLog(unittest.TestCase):
    def test_mutations_are_recorded(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        H.make_decision(store, org, intent)
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions, ["create_organization",
                                   "record_intent", "record_decision"])
        entry = audit.entries()[1]
        self.assertEqual(entry["actor"], "bob")
        self.assertEqual(entry["target"], intent["id"])
        self.assertEqual(set(entry),
                         {"ts", "actor", "action", "target", "details"})

    def test_entries_are_copies(self):
        audit = AuditLog()
        audit.record("alice", "act", "tgt", {"k": "v"})
        entries = audit.entries()
        entries[0]["action"] = "tampered"
        entries[0]["details"]["k"] = "tampered"
        fresh = audit.entries()
        self.assertEqual(fresh[0]["action"], "act")
        self.assertEqual(fresh[0]["details"]["k"], "v")

    def test_jsonl_persistence_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            first = AuditLog(path)
            first.record("alice", "create_organization", "org-1")
            first.record("bob", "record_intent", "int-1")
            second = AuditLog(path)
            self.assertEqual([e["action"] for e in second.entries()],
                             ["create_organization", "record_intent"])

    def test_no_update_or_delete_api(self):
        audit = AuditLog()
        for name in ("update", "delete", "remove", "clear"):
            self.assertFalse(hasattr(audit, name), name)


if __name__ == "__main__":
    unittest.main()
