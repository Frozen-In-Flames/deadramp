"""Tags & metadata tests.

Traces to: Core function 7 -- Tags (and item metadata) / sibling
claim family metadata_taxonomy; AC-3, SI-10.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, make_item, make_store
from cms.errors import NotFoundError, PermissionDenied, ValidationError


class TestTags(unittest.TestCase):
    """Core: Tags (metadata_taxonomy)."""

    def test_create_tag_shape_ids(self):
        """Core: Tags. create_tag -> tag-{n} with name/slug/created_by."""
        store, site, _ = make_store()
        t1 = store.create_tag(EDITOR, "Breaking", "breaking")
        t2 = store.create_tag(PUBLISHER, "Guides", "guides")
        self.assertEqual((t1["id"], t2["id"]), ("tag-1", "tag-2"))
        self.assertEqual([t["id"] for t in store.list_tags(VIEWER)], ["tag-1", "tag-2"])
        self.assertEqual(store.get_tag("tag-1", VIEWER)["name"], "Breaking")

    def test_tag_slug_globally_unique_and_valid(self):
        """Core: Tags (SI-10). Duplicate slug globally and bad slug -> ValidationError, no id consumed."""
        store, site, _ = make_store()
        store.create_tag(EDITOR, "One", "one")
        with self.assertRaises(ValidationError):
            store.create_tag(PUBLISHER, "Uno", "one")
        with self.assertRaises(ValidationError):
            store.create_tag(EDITOR, "Bad", "Bad Slug")
        self.assertEqual(store.create_tag(EDITOR, "Two", "two")["id"], "tag-2")

    def test_tag_write_roles(self):
        """Core: Tags (AC-3). tag_write: admin/publisher/editor; author/viewer denied."""
        store, site, _ = make_store()
        for user in (AUTHOR, VIEWER):
            with self.assertRaises(PermissionDenied):
                store.create_tag(user, "X", "x-%s" % user.name)

    def test_get_tag_unknown(self):
        """Core: Tags. Unknown tag -> NotFoundError."""
        store, site, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.get_tag("tag-999", ADMIN)

    def test_items_link_tags_at_create_and_update(self):
        """Core: Tags / metadata_taxonomy. Items link tags at create and at update; links appear on the item and its revision."""
        store, site, _ = make_store()
        t1 = store.create_tag(EDITOR, "One", "one")
        t2 = store.create_tag(EDITOR, "Two", "two")
        item = make_item(store, site, tag_ids=[t1["id"]])
        self.assertEqual(item["tag_ids"], ["tag-1"])
        updated = store.update_item(AUTHOR, item["id"], tag_ids=[t1["id"], t2["id"]])
        self.assertEqual(updated["tag_ids"], ["tag-1", "tag-2"])
        revs = store.list_revisions(item["id"], AUTHOR)
        self.assertEqual(revs[-1]["tag_ids"], ["tag-1", "tag-2"])


class TestMetadata(unittest.TestCase):
    """Core: Item metadata (metadata_taxonomy)."""

    def test_metadata_round_trip_and_default(self):
        """Core: Metadata. Metadata dict is stored on create, defaults to {}, and is replaced on update."""
        store, site, _ = make_store()
        plain = make_item(store, site, slug="plain")
        self.assertEqual(plain["metadata"], {})
        rich = make_item(store, site, slug="rich", metadata={"author_note": "x", "priority": 3})
        self.assertEqual(rich["metadata"], {"author_note": "x", "priority": 3})
        updated = store.update_item(AUTHOR, rich["id"], metadata={"priority": 5})
        self.assertEqual(updated["metadata"], {"priority": 5})

    def test_metadata_is_a_copy(self):
        """Core: Metadata. Mutating the caller's dict or the returned dict does not mutate the store."""
        store, site, _ = make_store()
        meta = {"k": "v"}
        item = make_item(store, site, metadata=meta)
        meta["k"] = "mutated"
        item["metadata"]["k"] = "also-mutated"
        self.assertEqual(store.get_item(item["id"], ADMIN)["metadata"], {"k": "v"})


if __name__ == "__main__":
    unittest.main()
