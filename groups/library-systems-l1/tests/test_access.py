"""Access matrix: traces to AC / IA in the UNION-SPEC baseline."""
import unittest
from librarysys_helpers import ALICE, BOB, CAROL
from librarysys.access import PERMISSIONS, can, permissions_for, require
from librarysys.errors import PermissionDenied

class AccessTests(unittest.TestCase):
    def test_admin_has_all(self):
        self.assertEqual(permissions_for("admin"), set(PERMISSIONS["admin"]))
        self.assertIn("audit_read", permissions_for("admin"))
    def test_member_lacks_lib_write_and_audit(self):
        self.assertNotIn("lib_write", permissions_for("member"))
        self.assertNotIn("audit_read", permissions_for("member"))
        self.assertIn("circulation_write", permissions_for("member"))
    def test_viewer_read_only(self):
        self.assertEqual(permissions_for("viewer"), {"lib_read", "report_read"})
    def test_can_and_require(self):
        self.assertTrue(can(BOB, "catalogue_write")); self.assertFalse(can(CAROL, "catalogue_write"))
        require(ALICE, "audit_read")
        with self.assertRaises(PermissionDenied): require(CAROL, "registry_write")
        with self.assertRaises(PermissionDenied): require(None, "lib_read")
    def test_unknown_role_denied(self):
        self.assertEqual(permissions_for("root"), set())
if __name__ == "__main__": unittest.main()
