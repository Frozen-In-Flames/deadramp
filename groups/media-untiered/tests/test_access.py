"""Access control (core function 11): the role/permission matrix."""

import unittest

from media_helpers import ADMIN, OPERATOR, VIEWER, make_org, make_store

from media.access import PERMISSIONS, User, can, permissions_for, require
from media.errors import PermissionDenied


class AccessTests(unittest.TestCase):
    def test_admin_has_every_action(self):
        for action in ("read", "register", "routes", "sessions",
                       "devices", "control", "optimize", "monitor",
                       "audit_read", "admin"):
            self.assertTrue(can(ADMIN, action), action)

    def test_operator_lacks_audit_read_and_admin(self):
        self.assertFalse(can(OPERATOR, "audit_read"))
        self.assertFalse(can(OPERATOR, "admin"))
        for action in ("read", "register", "routes", "sessions",
                       "devices", "control", "optimize", "monitor"):
            self.assertTrue(can(OPERATOR, action), action)

    def test_viewer_is_read_only(self):
        self.assertEqual(permissions_for("viewer"), {"read"})
        self.assertEqual(PERMISSIONS["viewer"], {"read"})

    def test_unknown_role_and_user_denied(self):
        self.assertEqual(permissions_for("nobody"), set())
        self.assertFalse(can(None, "read"))
        self.assertFalse(can(User("mallory", "superuser"), "read"))
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "read")

    def test_store_enforces_roles_on_writes(self):
        store, _audit = make_store()
        org = make_org(store)
        with self.assertRaises(PermissionDenied):
            store.create_endpoint(VIEWER, org["id"], "NET-X", "x",
                                  "agency_network")
        with self.assertRaises(PermissionDenied):
            store.audit_read(OPERATOR)
        # The denied write consumed no id.
        endpoint = store.create_endpoint(OPERATOR, org["id"], "NET-X",
                                         "x", "agency_network")
        self.assertEqual(endpoint["id"], "end-1")

    def test_string_actor_carries_identity_without_role(self):
        store, audit = make_store()
        org = store.create_organization("system-import", "ORG-STR",
                                        "Imported office")
        self.assertEqual(org["created_by"], "system-import")


if __name__ == "__main__":
    unittest.main()
