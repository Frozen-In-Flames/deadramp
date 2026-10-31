"""Core function 12 (audit half): the append-only audit log.

Every successful mutation is recorded with actor, action, and
target; failed operations record nothing; reads are not recorded
by the store. ``audit_read`` is admin-only (AU-2/AU-3, claimed on
the FedRAMP Low side only; AC-3 for the admin-only read).
"""

import json
import unittest
from pathlib import Path

from events.audit import AuditLog
from events.errors import PermissionDenied, ValidationError

from events_helpers import (ADMIN, MEMBER, VIEWER, make_organizer,
                            make_store)

SCRATCH = Path(__file__).resolve().parents[1] / "scratch"


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def test_mutations_are_recorded(self):
        organizer = make_organizer(self.store)
        entries = self.audit.entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "organizer_create")
        self.assertEqual(entry["target"], organizer["id"])
        self.assertEqual(set(entry),
                         {"ts", "actor", "action", "target", "details"})

    def test_failed_operations_record_nothing(self):
        with self.assertRaises(ValidationError):
            self.store.create_organizer(ADMIN, "", "Label")
        self.assertEqual(self.audit.entries(), [])

    def test_reads_are_not_recorded_by_the_store(self):
        organizer = make_organizer(self.store)
        self.store.list_organizers(VIEWER)
        self.store.get_organizer(VIEWER, organizer["id"])
        self.assertEqual(len(self.audit.entries()), 1)

    def test_entries_are_copies(self):
        make_organizer(self.store)
        entries = self.audit.entries()
        entries[0]["action"] = "forged"
        entries.append({"action": "forged"})
        fresh = self.audit.entries()
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh[0]["action"], "organizer_create")

    def test_audit_read_is_admin_only(self):
        make_organizer(self.store)
        result = self.store.audit_read(ADMIN)
        self.assertEqual(result["count"], 1)
        with self.assertRaises(PermissionDenied):
            self.store.audit_read(MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.audit_read(VIEWER)

    def test_jsonl_persistence_round_trip(self):
        path = SCRATCH / "test-audit.jsonl"
        if path.exists():
            path.unlink()
        try:
            log = AuditLog(str(path))
            log.record("alice", "organizer_create", "org-1", {"ref": "X"})
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["action"],
                             "organizer_create")
            reloaded = AuditLog(str(path))
            self.assertEqual(len(reloaded.entries()), 1)
        finally:
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
