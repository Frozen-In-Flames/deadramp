"""Core: Append-only audit log. Traces to UNION-SPEC core function
11 and control families AU-2/AU-3/AU-6/AU-9: every mutation is
recorded with actor, action, target, and UTC timestamp; there is no
update or delete API."""

import json
import os
import tempfile
import unittest

import research_helpers as H
from research.audit import AuditLog


class TestAuditLog(unittest.TestCase):
    def test_mutations_are_recorded(self):
        audit = AuditLog()
        store, commons, org = H.make_store(audit=audit)
        entries = audit.entries()
        # Commons creation, member addition, organization creation.
        self.assertGreaterEqual(len(entries), 3)
        entry = entries[0]
        self.assertEqual(set(entry.keys()),
                         {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "bob")
        self.assertEqual(entry["target"], commons["id"])
        for recorded in entries:
            self.assertTrue(recorded["action"])
            self.assertTrue(recorded["ts"])

    def test_decision_and_grant_mutations_are_recorded(self):
        audit = AuditLog()
        store, commons, org = H.make_store(audit=audit)
        before = len(audit.entries())
        dataset = H.make_dataset(store, commons)
        request = H.make_access_request(store, dataset)
        result = store.decide_access_request(H.STAFF, request["id"], True,
                                             starts_at=H.T0)
        grant_id = result["grant"]["id"]
        store.revoke_grant(H.STAFF, grant_id)
        entries = audit.entries()
        self.assertGreater(len(entries), before)
        targets = [e["target"] for e in entries]
        self.assertIn(dataset["id"], targets)
        self.assertIn(request["id"], targets)

    def test_entries_returns_copies(self):
        audit = AuditLog()
        audit.record("bob", "x", "y")
        audit.entries()[0]["actor"] = "mallory"
        self.assertEqual(audit.entries()[0]["actor"], "bob")

    def test_jsonl_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            first = AuditLog(path=path)
            first.record("bob", "commons_create", "com-1", {"name": "x"})
            second = AuditLog(path=path)
            self.assertEqual(len(second.entries()), 1)
            self.assertEqual(second.entries()[0]["target"], "com-1")
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(lines[0]["action"], "commons_create")

    def test_no_mutation_api(self):
        audit = AuditLog()
        for name in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(audit, name), name)


if __name__ == "__main__":
    unittest.main()
