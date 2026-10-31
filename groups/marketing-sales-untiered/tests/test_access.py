"""Access control hooks: the three-role permission matrix is
enforced on store operations for User-like actors, and unknown
roles/users are denied (union spec, core function 15)."""

import unittest

from marketsales_helpers import ADMIN, OPERATOR, VIEWER, make_store

from marketsales.access import User, can, permissions_for, require
from marketsales.errors import PermissionDenied


class AccessTests(unittest.TestCase):
    def test_permission_matrix_shape(self):
        self.assertIn("audit_read", permissions_for("admin"))
        self.assertNotIn("audit_read", permissions_for("operator"))
        self.assertEqual(permissions_for("viewer"), {"read"})
        self.assertEqual(permissions_for("nobody"), set())

    def test_can_and_require(self):
        self.assertTrue(can(ADMIN, "deliver"))
        self.assertFalse(can(VIEWER, "deliver"))
        self.assertFalse(can(None, "read"))
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "suppress")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "read")
        with self.assertRaises(PermissionDenied):
            require(None, "read")

    def test_viewer_cannot_mutate_through_the_store(self):
        store, _audit = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_organization(VIEWER, "ORG-X", "label")
        org = store.create_organization(ADMIN, "ORG-X", "label")
        with self.assertRaises(PermissionDenied):
            store.create_contact_list(VIEWER, org["id"], "lst", 1)
        with self.assertRaises(PermissionDenied):
            store.record_suppression(VIEWER, "lst-1", "CONTACT-REF-1",
                                     "unsubscribe")

    def test_operator_lacks_audit_read(self):
        store, _audit = make_store()
        with self.assertRaises(PermissionDenied):
            store.audit_read(OPERATOR)
        result = store.audit_read(ADMIN)
        self.assertIn("entries", result)


if __name__ == "__main__":
    unittest.main()
