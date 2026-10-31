"""Content items & revisions tests.

Traces to: Core function 3 -- Content items & authoring / sibling
claim families content_registry, authoring_editing; AC-3, SI-10.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, fresh_store, make_item, make_store
from cms.errors import NotFoundError, PermissionDenied, ValidationError


class TestCreateItem(unittest.TestCase):
    """Core: Items (content_registry / authoring_editing)."""

    def test_create_shape_revision1(self):
        """Core: Items. create_item -> ci-{n}, draft, author=actor, revision 1 minting rev-{n} snapshot."""
        store, site, section = make_store()
        item = make_item(store, site, section_id=section["id"],
                         metadata={"k": "v"})
        self.assertEqual(item["id"], "ci-1")
        self.assertEqual(item["status"], "draft")
        self.assertEqual(item["author"], "dave")
        self.assertEqual(item["revision"], 1)
        self.assertEqual(item["window_state"], None)
        self.assertFalse(item["is_live"])
        revs = store.list_revisions(item["id"], AUTHOR)
        self.assertEqual(len(revs), 1)
        self.assertEqual(revs[0]["id"], "rev-1")
        self.assertEqual(revs[0]["revision"], 1)
        self.assertEqual(revs[0]["title"], "Hello World")
        self.assertEqual(revs[0]["body"], "First body")
        self.assertEqual(revs[0]["metadata"], {"k": "v"})

    def test_create_unknown_site_type_section_tag(self):
        """Core: Items. Unknown site/type/section/tag -> NotFoundError, no id consumed."""
        store, site, _ = make_store()
        for kwargs in ({"site_id": "site-999"}, {"type_id": "ct-nope"},
                       {"section_id": "sec-999"}, {"tag_ids": ["tag-999"]}):
            with self.subTest(kwargs=kwargs):
                args = dict(site_id=site["id"], type_id="ct-page")
                args.update(kwargs)
                with self.assertRaises(NotFoundError):
                    store.create_item(AUTHOR, args["site_id"], args["type_id"], "T", "t-x",
                                      section_id=args.get("section_id"),
                                      tag_ids=args.get("tag_ids"))
        self.assertEqual(make_item(store, site, slug="ok-one")["id"], "ci-1")

    def test_section_must_belong_to_site(self):
        """Core: Items (SI-10). Section from another site -> ValidationError."""
        store, site, section = make_store()
        other = store.create_site(ADMIN, "Other", "other")
        with self.assertRaises(ValidationError):
            make_item(store, other, section_id=section["id"])

    def test_item_slug_unique_per_site(self):
        """Core: Items. Slug duplicate in same site denied; same slug in another site allowed."""
        store, site, _ = make_store()
        make_item(store, site)
        with self.assertRaises(ValidationError):
            make_item(store, site, title="Copy")
        other = store.create_site(ADMIN, "Other", "other")
        self.assertEqual(make_item(store, other)["site_id"], other["id"])

    def test_item_create_roles_and_metadata_validation(self):
        """Core: Items (AC-3/SI-10). Viewer cannot create; non-dict metadata -> ValidationError."""
        store, site, _ = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_item(VIEWER, site["id"], "ct-page", "T", "t-viewer")
        with self.assertRaises(ValidationError):
            store.create_item(AUTHOR, site["id"], "ct-page", "T", "t-bad", metadata=["x"])
        self.assertEqual(store.list_items(actor=ADMIN), [])

    def test_get_and_list_items_filters(self):
        """Core: Items. get_item / list_items with site and status filters; unknown -> NotFound."""
        store, site, _ = make_store()
        i1 = make_item(store, site, slug="a-one")
        i2 = make_item(store, site, slug="a-two", title="Second")
        self.assertEqual(store.get_item(i1["id"], VIEWER)["slug"], "a-one")
        self.assertEqual(len(store.list_items(site_id=site["id"], actor=VIEWER)), 2)
        self.assertEqual(len(store.list_items(status="draft", actor=VIEWER)), 2)
        self.assertEqual(store.list_items(status="published", actor=VIEWER), [])
        with self.assertRaises(NotFoundError):
            store.get_item("ci-999", ADMIN)
        with self.assertRaises(ValidationError):
            store.list_items(status="bogus", actor=ADMIN)


class TestUpdateItem(unittest.TestCase):
    """Core: Item editing & revisions (authoring_editing)."""

    def test_edit_mints_revision_snapshot(self):
        """Core: Revisions. Each edit mints rev-{n} capturing the new title/body/metadata snapshot; old revisions unchanged."""
        store, site, _ = make_store()
        item = make_item(store, site)
        updated = store.update_item(AUTHOR, item["id"], title="V2", body="Body2",
                                    metadata={"n": 2})
        self.assertEqual(updated["revision"], 2)
        revs = store.list_revisions(item["id"], AUTHOR)
        self.assertEqual([r["id"] for r in revs], ["rev-1", "rev-2"])
        self.assertEqual(revs[0]["title"], "Hello World")
        self.assertEqual(revs[1]["title"], "V2")
        self.assertEqual(revs[1]["metadata"], {"n": 2})
        self.assertEqual(revs[1]["edited_by"], "dave")

    def test_edit_approved_or_published_denied_validation(self):
        """Core: Revisions. Editing approved/published items -> ValidationError."""
        from cms_helpers import drive_to_approved, drive_to_published
        store, site, _ = make_store()
        item = make_item(store, site, slug="to-approve")
        drive_to_approved(store, item)
        with self.assertRaises(ValidationError):
            store.update_item(EDITOR, item["id"], title="Late")
        item2 = make_item(store, site, slug="to-publish")
        drive_to_published(store, item2)
        with self.assertRaises(ValidationError):
            store.update_item(PUBLISHER, item2["id"], title="Late")

    def test_editor_may_edit_in_review_author_may_not(self):
        """Core: Revisions. In in_review, editor/publisher may edit; the author may not."""
        store, site, _ = make_store()
        item = make_item(store, site)
        store.submit_item(AUTHOR, item["id"])
        edited = store.update_item(EDITOR, item["id"], body="Editor pass")
        self.assertEqual(edited["body"], "Editor pass")
        self.assertEqual(edited["status"], "in_review")
        with self.assertRaises(PermissionDenied):
            store.update_item(AUTHOR, item["id"], body="Author pass")

    def test_edit_unknown_tag_no_revision_consumed(self):
        """Core: Revisions (SI-10). Edit with unknown tag -> NotFoundError and no new revision."""
        store, site, _ = make_store()
        item = make_item(store, site)
        with self.assertRaises(NotFoundError):
            store.update_item(AUTHOR, item["id"], tag_ids=["tag-999"])
        self.assertEqual(len(store.list_revisions(item["id"], AUTHOR)), 1)


if __name__ == "__main__":
    unittest.main()
