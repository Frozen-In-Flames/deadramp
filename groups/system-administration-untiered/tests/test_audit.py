"""Core 12 (Audit log) / AU-2, AU-3, AU-6, AU-9: mutations are
recorded with actor/action/target, the log is append-only, and
JSONL persistence round-trips.
"""

import os
import tempfile
import unittest

import sysadmin_helpers as H
from sysadmin.audit import AuditLog

ENTRY_KEYS = {"ts", "actor", "action", "target", "details"}


class TestAudit(unittest.TestCase):
    def test_mutations_are_recorded(self):
        audit = AuditLog()
        store = H.fresh_store(audit=audit)
        org = H.make_org(store)
        system = H.make_system(store, org)
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions, ["organization_create", "system_create"])
        entry = audit.entries()[0]
        self.assertEqual(set(entry.keys()), ENTRY_KEYS)
        self.assertEqual(entry["actor"], "bob")
        self.assertEqual(entry["target"], org["id"])

    def test_denied_attempts_are_not_recorded_by_the_store(self):
        audit = AuditLog()
        store = H.fresh_store(audit=audit)
        org = H.make_org(store)
        count = len(audit.entries())
        try:
            store.get_organization(H.OUTSIDER, org["id"])
        except Exception:
            pass
        self.assertEqual(len(audit.entries()), count)

    def test_append_only_no_mutation_api(self):
        audit = AuditLog()
        for forbidden in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(audit, forbidden), forbidden)
        audit.record("bob", "x", "y")
        returned = audit.entries()
        returned.clear()
        self.assertEqual(len(audit.entries()), 1)

    def test_jsonl_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path=path)
            audit.record("alice", "organization_create", "org-1", {"ref": "A"})
            audit.record("bob", "system_create", "sys-1")
            reloaded = AuditLog(path=path)
            entries = reloaded.entries()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["details"], {"ref": "A"})
            self.assertEqual(entries[1]["actor"], "bob")


if __name__ == "__main__":
    unittest.main()
