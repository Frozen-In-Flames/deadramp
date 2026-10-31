"""Audit log: append-only, records every successful mutation with
actor/action/target, and persists to JSONL when a path is given
(union spec, core function 15)."""

import os
import tempfile
import unittest

from marketsales_helpers import ADMIN, OPERATOR, make_org, make_store

from marketsales.audit import AuditLog


class AuditTests(unittest.TestCase):
    def test_mutations_are_recorded(self):
        store, audit = make_store()
        make_org(store)
        store.create_opportunity(OPERATOR, "org-1", "OPP-1", "Agency",
                                 "Title", "2026-01-05")
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions,
                         ["create_organization", "create_opportunity"])
        entry = audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["target"], "org-1")
        self.assertIn("ts", entry)

    def test_entries_are_copies(self):
        audit = AuditLog()
        audit.record("alice", "act", "tgt", {"k": "v"})
        entries = audit.entries()
        entries[0]["action"] = "tampered"
        entries[0]["details"]["k"] = "tampered"
        fresh = audit.entries()
        self.assertEqual(fresh[0]["action"], "act")
        self.assertEqual(fresh[0]["details"]["k"], "v")

    def test_jsonl_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            audit.record("alice", "act", "tgt")
            audit.record("bob", "act2", "tgt2")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 2)
            self.assertEqual(reloaded.entries()[1]["actor"], "bob")


if __name__ == "__main__":
    unittest.main()
