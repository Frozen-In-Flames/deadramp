"""Access ladder and audit log behavior (substrate).

The TestAccess / TestAudit classes are carried verbatim from the
founding L2 build; TestAuditorRole pins the High-tier uplift [L3].
"""

import os
import tempfile
import unittest

import cloudinfra_helpers as H
from cloudinfra.access import ROLE_PERMISSIONS, User, require
from cloudinfra.audit import AuditLog
from cloudinfra.errors import PermissionDenied


class TestAccess(unittest.TestCase):
    def test_admin_has_every_action(self):
        self.assertEqual(len(ROLE_PERMISSIONS["admin"]), 11)

    def test_member_lacks_org_write_and_audit_read(self):
        member = ROLE_PERMISSIONS["member"]
        self.assertNotIn("org_write", member)
        self.assertNotIn("audit_read", member)
        self.assertIn("deployment_write", member)
        self.assertIn("operations_write", member)

    def test_viewer_is_read_only(self):
        self.assertEqual(
            ROLE_PERMISSIONS["viewer"], frozenset({"org_read", "report_read"}))

    def test_require_rejects_unknown_action(self):
        with self.assertRaises(ValueError):
            require(H.ADMIN, "teleport")

    def test_require_rejects_unpermitted_role(self):
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "deployment_write")

    def test_user_rejects_unknown_role(self):
        with self.assertRaises(ValueError):
            User("x", "superuser")


class TestAudit(unittest.TestCase):
    def test_record_and_entries(self):
        log = AuditLog()
        entry = log.record("alice", "tenancy_create", "ten-1", {"x": 1})
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "tenancy_create")
        entries = log.entries()
        self.assertEqual(len(entries), 1)
        entries[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "tenancy_create")

    def test_audit_jsonl_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path=path)
            log.record(H.ADMIN, "organization_create", "org-1")
            log.record("bob", "deployment_status", "dep-1")
            reloaded = AuditLog(path=path)
            actions = [e["action"] for e in reloaded.entries()]
            self.assertEqual(actions, ["organization_create", "deployment_status"])
            self.assertEqual(reloaded.entries()[0]["actor"], "alice")


class TestAuditorRole(unittest.TestCase):
    """[L3] AC-5 (technical slice): the auditor role holds
    audit_read and nothing else — audit review is a duty separable
    from administration. Arises at this tier only; the founding
    build has no auditor role and no AC-5 claim is back-ported."""

    def test_auditor_holds_audit_read_only(self):
        from cloudinfra.access import ROLE_PERMISSIONS
        self.assertEqual(
            ROLE_PERMISSIONS["auditor"], frozenset({"audit_read"}))

    def test_auditor_cannot_do_anything_else(self):
        for action in ("org_read", "org_write", "tenancy_write",
                       "deployment_write", "operations_write",
                       "report_read"):
            with self.assertRaises(PermissionDenied):
                require(H.AUDITOR, action)

    def test_auditor_can_require_audit_read(self):
        require(H.AUDITOR, "audit_read")  # must not raise

    def test_admin_still_holds_all_eleven_actions(self):
        self.assertEqual(len(ROLE_PERMISSIONS["admin"]), 11)
        self.assertIn("audit_read", ROLE_PERMISSIONS["admin"])


if __name__ == "__main__":
    unittest.main()
