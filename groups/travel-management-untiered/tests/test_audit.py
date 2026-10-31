import os
import tempfile
import unittest

from travel.audit import AuditLog

from travel_helpers import MEMBER, fresh_store, make_store, make_traveler


class TestAudit(unittest.TestCase):
    def test_mutations_are_recorded(self):
        store, org = make_store()
        make_traveler(store, org)
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("organization_create", actions)
        self.assertIn("member_add", actions)
        self.assertIn("traveler_create", actions)

    def test_entry_shape(self):
        audit = AuditLog()
        audit.record(MEMBER, "something", "target-1", {"k": "v"})
        (entry,) = audit.entries()
        self.assertEqual(set(entry.keys()),
                         {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "bob")

    def test_append_only_no_mutation_api(self):
        audit = AuditLog()
        for name in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(audit, name), name)

    def test_entries_returns_copies(self):
        audit = AuditLog()
        audit.record(MEMBER, "x", "t")
        audit.entries()[0]["action"] = "tampered"
        self.assertEqual(audit.entries()[0]["action"], "x")

    def test_jsonl_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path=path)
            audit.record(MEMBER, "one", "t1")
            audit.record(MEMBER, "two", "t2")
            reloaded = AuditLog(path=path)
            self.assertEqual([e["action"] for e in reloaded.entries()],
                             ["one", "two"])

    def test_store_without_audit_still_works(self):
        store = fresh_store(audit=None)
        store.audit = None
        org = store.create_organization(MEMBER, "ORG-1", "Solo")
        self.assertEqual(org["ref"], "ORG-1")


if __name__ == "__main__":
    unittest.main()
