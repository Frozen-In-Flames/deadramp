"""Sites & sections tests.

Traces to: Core function 1 -- Sites & sections / sibling claim family
site_structure; control families AC-3, SI-10.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, fresh_store, make_store
from cms.errors import NotFoundError, PermissionDenied, ValidationError


class TestSites(unittest.TestCase):
    """Core: Sites (site_structure)."""

    def test_create_site_shape_and_ids(self):
        """Core: Sites. create_site -> site-{n}, fields, created_by."""
        store = fresh_store()
        s1 = store.create_site(PUBLISHER, "One", "one", "first")
        s2 = store.create_site(ADMIN, "Two", "two")
        self.assertEqual((s1["id"], s2["id"]), ("site-1", "site-2"))
        self.assertEqual(s1["description"], "first")
        self.assertEqual(s2["description"], "")
        self.assertEqual(s1["created_by"], "bob")
        self.assertIn("created_utc", s1)

    def test_slug_validation(self):
        """Core: Sites (SI-10). Empty/uppercase/space/underscore slugs -> ValidationError, no id consumed."""
        store = fresh_store()
        for bad in ("", "Upper", "has space", "under_score", "-lead", "trail-", "a--b"):
            with self.subTest(slug=bad):
                with self.assertRaises(ValidationError):
                    store.create_site(PUBLISHER, "X", bad)
        site = store.create_site(PUBLISHER, "Good", "good-slug-1")
        self.assertEqual(site["id"], "site-1")

    def test_duplicate_site_slug_global(self):
        """Core: Sites. Duplicate slug globally -> ValidationError, no id consumed."""
        store, site, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_site(ADMIN, "Copy", "main-site")
        nxt = store.create_site(ADMIN, "Other", "other")
        self.assertEqual(nxt["id"], "site-2")

    def test_site_write_denied_viewer_author_editor(self):
        """Core: Sites (AC-3). site_write is admin/publisher only; denials consume no id."""
        store = fresh_store()
        for user in (VIEWER, AUTHOR, EDITOR):
            with self.assertRaises(PermissionDenied):
                store.create_site(user, "X", "x-%s" % user.name)
        self.assertEqual(store.create_site(PUBLISHER, "Ok", "ok")["id"], "site-1")

    def test_get_list_sites(self):
        """Core: Sites. get_site / list_sites sorted; unknown -> NotFoundError; all roles may read."""
        store, site, _ = make_store()
        self.assertEqual(store.get_site(site["id"], VIEWER)["slug"], "main-site")
        self.assertEqual([s["id"] for s in store.list_sites(VIEWER)], [site["id"]])
        with self.assertRaises(NotFoundError):
            store.get_site("site-999", ADMIN)


class TestSections(unittest.TestCase):
    """Core: Sections (site_structure)."""

    def test_create_section_shape_ids_parent(self):
        """Core: Sections. create_section -> sec-{n}; parent linkage stored."""
        store, site, section = make_store()
        self.assertEqual(section["id"], "sec-1")
        self.assertEqual(section["site_id"], site["id"])
        self.assertIsNone(section["parent_id"])
        child = store.create_section(PUBLISHER, site["id"], "Sub", "sub", parent_id=section["id"])
        self.assertEqual(child["id"], "sec-2")
        self.assertEqual(child["parent_id"], "sec-1")

    def test_parent_must_belong_to_same_site(self):
        """Core: Sections (SI-10). Parent from another site -> ValidationError, no id consumed."""
        store, site, section = make_store()
        other = store.create_site(ADMIN, "Other", "other-site")
        with self.assertRaises(ValidationError):
            store.create_section(EDITOR, other["id"], "X", "x", parent_id=section["id"])
        ok = store.create_section(EDITOR, other["id"], "Y", "y")
        self.assertEqual(ok["id"], "sec-2")

    def test_unknown_site_and_parent_not_found(self):
        """Core: Sections. Unknown site/parent -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.create_section(EDITOR, "site-999", "X", "x")
        store2, site, _ = make_store()
        with self.assertRaises(NotFoundError):
            store2.create_section(EDITOR, site["id"], "X", "x", parent_id="sec-999")

    def test_section_slug_unique_per_site_not_global(self):
        """Core: Sections. Same section slug allowed in a different site, denied in the same site."""
        store, site, section = make_store()
        with self.assertRaises(ValidationError):
            store.create_section(EDITOR, site["id"], "News2", "news")
        other = store.create_site(ADMIN, "Other", "other-site")
        ok = store.create_section(EDITOR, other["id"], "News", "news")
        self.assertEqual(ok["site_id"], other["id"])

    def test_section_write_roles(self):
        """Core: Sections (AC-3). section_write: admin/publisher/editor; author/viewer denied."""
        store, site, _ = make_store()
        for user in (AUTHOR, VIEWER):
            with self.assertRaises(PermissionDenied):
                store.create_section(user, site["id"], "X", "x-%s" % user.name)

    def test_list_sections(self):
        """Core: Sections. list_sections returns only that site's sections; unknown site 404."""
        store, site, section = make_store()
        self.assertEqual([s["id"] for s in store.list_sections(site["id"], VIEWER)], [section["id"]])
        with self.assertRaises(NotFoundError):
            store.list_sections("site-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
