"""Core: Append-only audit log. Traces to UNION-SPEC core function
13 and control families AU-2/AU-3/AU-6/AU-9: every mutation is
recorded with actor, action, target, and UTC timestamp; there is no
update or delete API."""

import json
import os
import tempfile
import unittest

import grants_helpers as H
from grants.audit import AuditLog


class TestAuditLog(unittest.TestCase):
    def test_mutations_are_recorded(self):
        audit = AuditLog()
        store, program, org = H.make_store(audit=audit)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("program_create", actions)
        self.assertIn("member_add", actions)
        self.assertIn("organization_create", actions)
        entry = audit.entries()[0]
        self.assertEqual(set(entry.keys()),
                         {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "bob")

    def test_entries_returns_copies(self):
        audit = AuditLog()
        audit.record("bob", "x", "y")
        audit.entries()[0]["actor"] = "mallory"
        self.assertEqual(audit.entries()[0]["actor"], "bob")

    def test_jsonl_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            first = AuditLog(path=path)
            first.record("bob", "program_create", "gp-1", {"name": "x"})
            second = AuditLog(path=path)
            self.assertEqual(len(second.entries()), 1)
            self.assertEqual(second.entries()[0]["target"], "gp-1")
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(lines[0]["action"], "program_create")

    def test_no_mutation_api(self):
        audit = AuditLog()
        for name in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(audit, name), name)


if __name__ == "__main__":
    unittest.main()
