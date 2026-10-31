"""Content types tests.

Traces to: Core function 2 -- Content types / sibling claim family
content_registry; control families AC-3, SI-10.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, fresh_store
from cms.errors import NotFoundError, PermissionDenied, ValidationError


class TestTypes(unittest.TestCase):
    """Core: Content types (content_registry)."""

    def test_builtins_preregistered_fixed_ids(self):
        """Core: Types. Built-ins page/article/document/collection use fixed ct-* ids, created_by system."""
        store = fresh_store()
        types = store.list_types(VIEWER)
        self.assertEqual([t["id"] for t in types],
                         ["ct-page", "ct-article", "ct-document", "ct-collection"])
        self.assertEqual([t["name"] for t in types],
                         ["page", "article", "document", "collection"])
        for t in types:
            self.assertTrue(t["builtin"])
            self.assertEqual(t["created_by"], "system")

    def test_get_type_builtin_and_unknown(self):
        """Core: Types. get_type returns a built-in; unknown -> NotFoundError."""
        store = fresh_store()
        self.assertEqual(store.get_type("ct-page", VIEWER)["name"], "page")
        with self.assertRaises(NotFoundError):
            store.get_type("ct-nope", ADMIN)

    def test_create_custom_type_ids_start_at_1(self):
        """Core: Types. Custom types get ct-{n} from 1 (built-ins consume no counter)."""
        store = fresh_store()
        t1 = store.create_type(PUBLISHER, "release-note", "A release note")
        t2 = store.create_type(ADMIN, "faq")
        self.assertEqual((t1["id"], t2["id"]), ("ct-1", "ct-2"))
        self.assertFalse(t1["builtin"])
        self.assertEqual(t1["created_by"], "bob")
        ids = [t["id"] for t in store.list_types(ADMIN)]
        self.assertEqual(ids[-2:], ["ct-1", "ct-2"])

    def test_type_write_admin_publisher_only(self):
        """Core: Types (AC-3). type_write denied for editor/author/viewer, no id consumed."""
        store = fresh_store()
        for user in (EDITOR, AUTHOR, VIEWER):
            with self.assertRaises(PermissionDenied):
                store.create_type(user, "x-%s" % user.name)
        self.assertEqual(store.create_type(PUBLISHER, "ok")["id"], "ct-1")

    def test_type_name_required(self):
        """Core: Types (SI-10). Empty name -> ValidationError."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_type(PUBLISHER, "")


if __name__ == "__main__":
    unittest.main()
