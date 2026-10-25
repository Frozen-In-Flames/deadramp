"""Access-control tests.

Traces to: Core function -- Access control (RBAC); contract for
``datamgmt/access.py``; control families AC-2/AC-3/AC-5/AC-6, IA-2.

Pinned matrix: admin has every action; steward has every action
except ``audit_read``; viewer has every read except ``audit_read``
plus ``access_request`` only; auditor (High-baseline uplift, AC-5)
has ``audit_read`` and nothing else. The write actions named in the contract
are dataset_write, source_write, ingest_record, quality_write,
quality_run, access_request, access_decide, retention_write and
export. Read actions are the actions ending in ``_read`` (audit_read
among them). The exact-matrix assertions below are therefore stated
both as the named write sets and as exact set relations over
``PERMISSIONS`` / ``ACTIONS`` so the matrix is pinned completely
without inventing read-action names the contract does not spell out.
"""

import unittest

from datamgmt_helpers import ADMIN, AUDITOR, STEWARD, VIEWER
from datamgmt.access import ACTIONS, PERMISSIONS, User, can, permissions_for, require
from datamgmt.errors import DataMgmtError, PermissionDenied

WRITES = {
    "dataset_write", "source_write", "ingest_record", "quality_write",
    "quality_run", "access_request", "access_decide", "retention_write",
    "export",
}
STEWARD_SET = None  # computed below from the imported matrix
ADMIN_SET = set(ACTIONS)


def _reads(action_set):
    """Core: Access control. Read actions are the *_read actions."""
    return {a for a in action_set if a.endswith("_read")}


READS = _reads(ADMIN_SET)
STEWARD_SET = ADMIN_SET - {"audit_read"}
VIEWER_SET = (READS - {"audit_read"}) | {"access_request"}


class TestMatrix(unittest.TestCase):
    """Core: Access control -- exact permission matrix."""

    def test_roles_exact(self):
        """Core: Access control. Roles are admin/steward/viewer/auditor (auditor added by the High uplift, AC-5)."""
        self.assertEqual(
            set(PERMISSIONS.keys()), {"admin", "steward", "viewer", "auditor"}
        )

    def test_actions_include_named_writes_and_audit_read(self):
        """Core: Access control. ACTIONS names every contract write plus audit_read."""
        self.assertTrue(WRITES.issubset(set(ACTIONS)))
        self.assertIn("audit_read", ACTIONS)
        # At least one non-audit read must exist.
        self.assertTrue(READS - {"audit_read"})

    def test_admin_permissions_exact(self):
        """Core: Access control. Admin has all actions (admin = all)."""
        self.assertEqual(set(PERMISSIONS["admin"]), ADMIN_SET)
        self.assertEqual(set(permissions_for("admin")), set(ACTIONS))

    def test_steward_permissions_exact(self):
        """Core: Access control. Steward = all actions except audit_read."""
        self.assertEqual(set(PERMISSIONS["steward"]), STEWARD_SET)
        self.assertEqual(set(permissions_for("steward")), ADMIN_SET - {"audit_read"})

    def test_viewer_permissions_exact(self):
        """Core: Access control. Viewer = reads except audit_read, plus access_request only."""
        self.assertEqual(set(PERMISSIONS["viewer"]), VIEWER_SET)
        self.assertEqual(set(permissions_for("viewer")), VIEWER_SET)

    def test_steward_has_every_named_write(self):
        """Core: Access control. Steward carries all nine contract writes."""
        for action in WRITES:
            with self.subTest(action=action):
                self.assertIn(action, PERMISSIONS["steward"])

    def test_viewer_has_no_write_except_access_request(self):
        """Core: Access control (AC-6 least privilege). Viewer writes = {access_request}."""
        for action in WRITES - {"access_request"}:
            with self.subTest(action=action):
                self.assertNotIn(action, PERMISSIONS["viewer"])
        self.assertIn("access_request", PERMISSIONS["viewer"])

    def test_audit_read_holders(self):
        """Core: Access control (AU-6 / AC-5). audit_read belongs to admin and the auditor role alone; steward and viewer do not hold it."""
        self.assertIn("audit_read", PERMISSIONS["admin"])
        self.assertIn("audit_read", PERMISSIONS["auditor"])
        self.assertNotIn("audit_read", PERMISSIONS["steward"])
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])

    def test_auditor_permissions_exact(self):
        """Core: Access control (AC-5, High uplift). Auditor = {audit_read} and nothing else: no operational read or write."""
        self.assertEqual(set(PERMISSIONS["auditor"]), {"audit_read"})
        self.assertEqual(set(permissions_for("auditor")), {"audit_read"})

    def test_permissions_for_matches_matrix(self):
        """Core: Access control. permissions_for(role) returns the matrix set."""
        self.assertEqual(set(permissions_for("admin")), ADMIN_SET)
        self.assertEqual(set(permissions_for("steward")), STEWARD_SET)
        self.assertEqual(set(permissions_for("viewer")), VIEWER_SET)
        self.assertEqual(set(permissions_for("auditor")), {"audit_read"})

    def test_unknown_role_empty_permissions(self):
        """Core: Access control. Unknown role -> empty permissions, can() False."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(User("mallory", "superuser"), "dataset_write"))
        self.assertFalse(can(User("mallory", "superuser"), "access_request"))


class TestCanRequire(unittest.TestCase):
    """Core: Access control -- can()/require()."""

    def test_user_fields(self):
        """Core: Access control. User(name, role) stores both."""
        u = User("dana", "steward")
        self.assertEqual((u.name, u.role), ("dana", "steward"))

    def test_can_matrix(self):
        """Core: Access control. can() is true exactly on the matrix."""
        for user, allowed in ((ADMIN, ADMIN_SET), (STEWARD, STEWARD_SET), (VIEWER, VIEWER_SET), (AUDITOR, {"audit_read"})):
            for action in ACTIONS:
                with self.subTest(role=user.role, action=action):
                    self.assertEqual(can(user, action), action in allowed)

    def test_require_allows_on_matrix(self):
        """Core: Access control. require() passes for on-matrix actions."""
        require(ADMIN, "audit_read")
        require(ADMIN, "dataset_write")
        require(STEWARD, "dataset_write")
        require(STEWARD, "access_decide")
        require(STEWARD, "export")
        require(VIEWER, "access_request")
        for action in VIEWER_SET:
            require(VIEWER, action)

    def test_require_denies_off_matrix(self):
        """Core: Access control (AC-3). require() raises PermissionDenied off-matrix."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "dataset_write")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "export")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "access_decide")
        with self.assertRaises(PermissionDenied):
            require(STEWARD, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "dataset_read")
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "dataset_write")
        require(AUDITOR, "audit_read")

    def test_require_unknown_role_and_action(self):
        """Core: Access control. Unknown role/action denied, even for admin."""
        with self.assertRaises(PermissionDenied):
            require(User("x", "nope"), "access_request")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        with self.assertRaises(DataMgmtError):
            require(VIEWER, "dataset_write")

    def test_none_user_denied(self):
        """Core: Access control (IA-2). None user: can() False, require() PermissionDenied."""
        self.assertFalse(can(None, "access_request"))
        self.assertFalse(can(None, "audit_read"))
        with self.assertRaises(PermissionDenied):
            require(None, "access_request")


if __name__ == "__main__":
    unittest.main()
