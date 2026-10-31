"""Core function 17 (audit half): the append-only audit log
(AU-2/AU-3/AU-6/AU-9 at the Moderate baseline).

Mutations are recorded; refused operations are not recorded by
the store (denied attempts are the service layer's to record, so
nothing is double-counted); audit reads require the admin-only
``audit_read`` permission.
"""

import os
import tempfile
import unittest

from erp.audit import AuditLog
from erp.errors import PermissionDenied, ValidationError

from erp_helpers import (ADMIN, OPERATOR, VIEWER, make_org, make_store)


class AuditTests(unittest.TestCase):
    def test_mutations_are_recorded(self):
        store, audit = make_store()
        org = make_org(store)
        store.create_application(OPERATOR, org["id"], "APP-1", "App",
                                 "Suite")
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions,
                         ["organization_create", "application_create"])
        entry = audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["target"], org["id"])

    def test_refused_operations_are_not_recorded(self):
        store, audit = make_store()
        make_org(store)
        before = len(audit.entries())
        with self.assertRaises(ValidationError):
            store.create_organization(ADMIN, "ORG-0001", "Duplicate")
        self.assertEqual(len(audit.entries()), before)

    def test_audit_read_is_admin_only(self):
        store, _ = make_store()
        make_org(store)
        result = store.audit_read(ADMIN)
        self.assertEqual(result["count"], 1)
        with self.assertRaises(PermissionDenied):
            store.audit_read(OPERATOR)
        with self.assertRaises(PermissionDenied):
            store.audit_read(VIEWER)

    def test_log_is_append_only_and_persists_as_jsonl(self):
        self.assertFalse(hasattr(AuditLog, "update"))
        self.assertFalse(hasattr(AuditLog, "delete"))
        self.assertFalse(hasattr(AuditLog, "clear"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "organization_create", "org-1")
            log.record("bob", "person_create", "per-1")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 2)
            self.assertEqual(reloaded.entries()[1]["actor"], "bob")


if __name__ == "__main__":
    unittest.main()
