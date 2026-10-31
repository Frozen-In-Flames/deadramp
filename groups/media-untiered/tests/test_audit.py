"""Audit log (core function 11): append-only, copies, JSONL."""

import json
import os
import tempfile
import unittest

from media_helpers import ADMIN, OPERATOR, make_org, make_store

from media.audit import AuditLog


class AuditTests(unittest.TestCase):
    def test_mutations_are_recorded_with_actor_action_target(self):
        store, audit = make_store()
        org = make_org(store)
        store.create_endpoint(OPERATOR, org["id"], "NET-1", "n",
                              "agency_network")
        entries = audit.entries()
        self.assertEqual([e["action"] for e in entries],
                         ["create_organization", "create_endpoint"])
        self.assertEqual(entries[0]["actor"], "alice")
        self.assertEqual(entries[1]["actor"], "bob")
        self.assertEqual(entries[1]["target"], "end-1")
        self.assertEqual(entries[1]["details"]["kind"], "agency_network")

    def test_entries_are_copies(self):
        audit = AuditLog()
        audit.record("alice", "act", "tgt", {"k": "v"})
        entries = audit.entries()
        entries[0]["action"] = "tampered"
        entries[0]["details"]["k"] = "tampered"
        self.assertEqual(audit.entries()[0]["action"], "act")
        self.assertEqual(audit.entries()[0]["details"]["k"], "v")

    def test_no_update_or_delete_api(self):
        audit = AuditLog()
        for name in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(audit, name), name)

    def test_jsonl_persistence_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            first = AuditLog(path)
            first.record("alice", "create_organization", "org-1",
                         {"ref": "ORG-1"})
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(lines), 1)
            second = AuditLog(path)
            self.assertEqual(len(second.entries()), 1)
            self.assertEqual(second.entries()[0]["target"], "org-1")

    def test_audit_read_returns_entries_for_admin(self):
        store, audit = make_store()
        make_org(store)
        result = store.audit_read(ADMIN)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["entries"][0]["action"],
                         "create_organization")


if __name__ == "__main__":
    unittest.main()
