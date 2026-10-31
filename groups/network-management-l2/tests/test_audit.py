"""Core function 12: append-only audit log (AU-2, AU-3, AU-6, AU-9)."""

import json
import os
import tempfile
import unittest

import netmgmt_helpers as H
from netmgmt.audit import AuditLog


class TestAudit(unittest.TestCase):
    def test_mutations_are_recorded_with_entry_shape(self):
        audit = AuditLog()
        store = H.fresh_store(audit=audit)
        org = H.make_org(store)
        H.make_network(store, org)
        entries = audit.entries()
        actions = [e["action"] for e in entries]
        self.assertIn("organization_create", actions)
        self.assertIn("network_create", actions)
        for entry in entries:
            self.assertEqual(
                set(entry.keys()), {"ts", "actor", "action", "target", "details"})
            self.assertEqual(entry["actor"], "bob")

    def test_entries_are_copies(self):
        audit = AuditLog()
        audit.record("bob", "x", "y")
        audit.entries()[0]["action"] = "tampered"
        self.assertEqual(audit.entries()[0]["action"], "x")

    def test_jsonl_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            first = AuditLog(path=path)
            first.record("bob", "organization_create", "org-1", {"ref": "A"})
            first.record("erin", "change_decide", "chg-1")
            reopened = AuditLog(path=path)
            entries = reopened.entries()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[1]["actor"], "erin")
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(lines), 2)

    def test_no_mutation_api(self):
        audit = AuditLog()
        for name in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(audit, name), name)


if __name__ == "__main__":
    unittest.main()
