"""Access-control tests.

Traces to: Core function -- Access control (RBAC) / sibling claim
family access_administration; contract for ``cms/access.py``;
control families AC-2/AC-3/AC-5/AC-6, IA-2.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, fresh_store, make_item, make_store
from cms.access import ACTIONS, PERMISSIONS, ROLES, User, can, permissions_for, require
from cms.errors import PermissionDenied

READS = {"site_read", "section_read", "type_read", "item_read", "asset_read",
         "tag_read", "search", "report_read"}
PUBLISHER_SET = READS | {"site_write", "section_write", "type_write", "item_create",
                         "item_edit", "item_submit", "item_review", "item_publish",
                         "item_archive", "asset_write", "tag_write"}
EDITOR_SET = READS | {"section_write", "item_create", "item_edit", "item_submit",
                      "item_review", "asset_write", "tag_write"}
AUTHOR_SET = READS | {"item_create", "item_edit", "item_submit", "asset_write"}
VIEWER_SET = set(READS)
ADMIN_SET = set(ACTIONS)


class TestMatrix(unittest.TestCase):
    """Core: RBAC -- exact permission matrix (access_administration)."""

    def test_roles_exact(self):
        """Core: RBAC. Roles are admin/publisher/editor/author/viewer."""
        self.assertEqual(set(ROLES), {"admin", "publisher", "editor", "author", "viewer"})
        self.assertEqual(set(PERMISSIONS.keys()), set(ROLES))

    def test_admin_exact(self):
        """Core: RBAC. Admin has all actions including audit_read."""
        self.assertEqual(set(PERMISSIONS["admin"]), ADMIN_SET)
        self.assertIn("audit_read", PERMISSIONS["admin"])

    def test_publisher_exact(self):
        """Core: RBAC. Publisher = reads + all writes, no audit_read."""
        self.assertEqual(set(PERMISSIONS["publisher"]), PUBLISHER_SET)
        self.assertNotIn("audit_read", PERMISSIONS["publisher"])

    def test_editor_exact(self):
        """Core: RBAC. Editor lacks site_write/type_write/publish/archive."""
        self.assertEqual(set(PERMISSIONS["editor"]), EDITOR_SET)

    def test_author_exact(self):
        """Core: RBAC. Author = reads + item_create/edit/submit + asset_write."""
        self.assertEqual(set(PERMISSIONS["author"]), AUTHOR_SET)

    def test_viewer_exact(self):
        """Core: RBAC (AC-6). Viewer = reads only, no audit_read."""
        self.assertEqual(set(PERMISSIONS["viewer"]), VIEWER_SET)

    def test_audit_read_admin_only(self):
        """Core: RBAC (AU-6). audit_read belongs to admin alone."""
        for role in ("publisher", "editor", "author", "viewer"):
            self.assertNotIn("audit_read", PERMISSIONS[role])

    def test_permissions_for_and_can(self):
        """Core: RBAC. permissions_for()/can() follow the matrix exactly."""
        for user, allowed in ((ADMIN, ADMIN_SET), (PUBLISHER, PUBLISHER_SET),
                              (EDITOR, EDITOR_SET), (AUTHOR, AUTHOR_SET), (VIEWER, VIEWER_SET)):
            self.assertEqual(set(permissions_for(user.role)), allowed)
            for action in ACTIONS:
                with self.subTest(role=user.role, action=action):
                    self.assertEqual(can(user, action), action in allowed)

    def test_unknown_role_and_none_denied(self):
        """Core: RBAC. Unknown role / None user -> denied."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(None, "item_read"))
        self.assertFalse(can(User("mallory", "superuser"), "item_read"))
        with self.assertRaises(PermissionDenied):
            require(None, "item_read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "item_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "item_create")
        self.assertTrue(require(ADMIN, "audit_read"))


class TestAuthorOwnership(unittest.TestCase):
    """Core: RBAC -- author may edit/submit OWN items only (access_administration)."""

    def test_author_edits_own(self):
        """Core: RBAC / authoring_editing. Author edits own draft."""
        store, site, _ = make_store()
        item = make_item(store, site)
        updated = store.update_item(AUTHOR, item["id"], title="Mine v2")
        self.assertEqual(updated["title"], "Mine v2")

    def test_author_cannot_edit_others(self):
        """Core: RBAC. Author editing another author's item -> PermissionDenied, unchanged, no revision consumed."""
        store, site, _ = make_store()
        item = store.create_item(EDITOR, site["id"], "ct-page", "Carol Page", "carol-page")
        with self.assertRaises(PermissionDenied):
            store.update_item(AUTHOR, item["id"], title="Hijack")
        self.assertEqual(store.get_item(item["id"], EDITOR)["title"], "Carol Page")
        self.assertEqual(len(store.list_revisions(item["id"], EDITOR)), 1)

    def test_author_cannot_submit_others(self):
        """Core: RBAC. Author submitting another's item -> PermissionDenied."""
        store, site, _ = make_store()
        item = store.create_item(EDITOR, site["id"], "ct-page", "Carol Page", "carol-page")
        with self.assertRaises(PermissionDenied):
            store.submit_item(AUTHOR, item["id"])
        self.assertEqual(store.get_item(item["id"], EDITOR)["status"], "draft")

    def test_plain_string_actor_carries_identity_no_role(self):
        """Core: RBAC. Plain-string actor: identity recorded, no store-level role enforcement (service enforces)."""
        store = fresh_store()
        site = store.create_site("bob", "String Site", "string-site")
        self.assertEqual(site["created_by"], "bob")
        item = store.create_item("dave", site["id"], "ct-page", "T", "t-slug")
        self.assertEqual(item["author"], "dave")


if __name__ == "__main__":
    unittest.main()
