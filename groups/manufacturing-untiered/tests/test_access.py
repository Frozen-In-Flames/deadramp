"""Access control — core function 7 (UNION-SPEC.md).

The three-role permission matrix: admin holds every action;
operator holds read/register/intents/decisions; viewer holds read
only. Unknown roles and unknown users are denied.
"""

import unittest

from manufacturing import access
from manufacturing.errors import PermissionDenied

import manufacturing_helpers as H


class TestAccessMatrix(unittest.TestCase):
    def test_admin_holds_every_action(self):
        self.assertEqual(access.permissions_for("admin"),
                         set(access.ACTIONS))

    def test_operator_matrix(self):
        self.assertEqual(access.permissions_for("operator"),
                         {"read", "register", "intents", "decisions"})

    def test_viewer_is_read_only(self):
        self.assertEqual(access.permissions_for("viewer"), {"read"})

    def test_unknown_role_has_no_permissions(self):
        self.assertEqual(access.permissions_for("superuser"), set())
        self.assertFalse(access.can(H.OUTSIDER, "read"))

    def test_can_and_require(self):
        self.assertTrue(access.can(H.OPERATOR, "intents"))
        self.assertFalse(access.can(H.VIEWER, "intents"))
        self.assertTrue(access.require(H.ADMIN, "audit_read"))
        with self.assertRaises(PermissionDenied):
            access.require(H.VIEWER, "decisions")
        with self.assertRaises(PermissionDenied):
            access.require(None, "read")
        with self.assertRaises(PermissionDenied):
            access.require(H.OUTSIDER, "read")

    def test_store_enforces_roles_for_user_actors(self):
        store, audit, org = H.make_store()
        with self.assertRaises(PermissionDenied):
            store.record_intent(H.VIEWER, org["id"], "L", "S", "eng-1")
        with self.assertRaises(PermissionDenied):
            store.audit_read(H.OPERATOR)


if __name__ == "__main__":
    unittest.main()
