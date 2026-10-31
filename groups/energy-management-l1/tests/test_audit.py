"""Core function 12 (audit half): the append-only audit log.

Every successful mutation is recorded; audit_read is admin-only at
this tier (traced to AC-3; FAR 52.204-21 has no audit practice, so
no audit claim is made on the CMMC side -- UNION-SPEC precision
notes). The log has no update or delete API.
"""

import tempfile
import unittest
from pathlib import Path

from energy.audit import AuditLog
from energy.errors import PermissionDenied

from energy_helpers import (IN_WINDOW, MEMBER, VIEWER, make_customer,
                            make_open_auction, make_store, ADMIN)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def test_mutations_recorded(self):
        customer = make_customer(self.store)
        auction = make_open_auction(self.store, customer)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertEqual(actions, ["customer_create", "auction_create"])
        entry = self.audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["target"], customer["id"])
        self.assertIn("ts", entry)

    def test_failed_operations_record_nothing(self):
        with self.assertRaises(Exception):
            self.store.create_customer(ADMIN, "", "label")
        self.assertEqual(self.audit.entries(), [])

    def test_audit_read_admin_only(self):
        make_customer(self.store)
        result = self.store.audit_read(ADMIN)
        self.assertEqual(result["count"], 1)
        for user in (MEMBER, VIEWER):
            with self.assertRaises(PermissionDenied):
                self.store.audit_read(user)

    def test_log_is_append_only(self):
        log = AuditLog()
        log.record("alice", "x", "y")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))
        entries = log.entries()
        entries[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "x")

    def test_jsonl_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "customer_create", "cust-1", {"ref": "R"})
            log.record("bob", "bid_record", "bid-1")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 2)
            self.assertEqual(reloaded.entries()[1]["actor"], "bob")

    def test_bid_and_close_recorded(self):
        from energy_helpers import make_providers
        customer = make_customer(self.store)
        pa, _ = make_providers(self.store)
        auction = make_open_auction(self.store, customer)
        self.store.record_bid(ADMIN, auction["id"], pa["id"], 500,
                              at=IN_WINDOW)
        self.store.close_auction(ADMIN, auction["id"], closed_at=IN_WINDOW)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("bid_record", actions)
        self.assertIn("auction_close", actions)


if __name__ == "__main__":
    unittest.main()
