"""Publishing tests.

Traces to: Core function 5 -- Publishing / sibling claim family
delivery_publishing; AC-3, SI-10.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, drive_to_approved, make_item, make_store
from cms.errors import PermissionDenied, ValidationError
from cms.store import window_state

NOW = "2026-06-15T12:00:00+00:00"


class TestPublishing(unittest.TestCase):
    """Core: Publishing (delivery_publishing)."""

    def test_publish_record_minted(self):
        """Core: Publishing. publish_item: approved -> published, mints pub-{n} with publisher and timestamps."""
        store, site, _ = make_store()
        item = make_item(store, site)
        drive_to_approved(store, item)
        published = store.publish_item(PUBLISHER, item["id"])
        self.assertEqual(published["status"], "published")
        records = store.list_publish_records(actor=ADMIN)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["id"], "pub-1")
        self.assertEqual(rec["item_id"], item["id"])
        self.assertEqual(rec["published_by"], "bob")
        self.assertIn("published_utc", rec)
        self.assertEqual(store.get_publish_record("pub-1", VIEWER)["item_id"], item["id"])

    def test_publish_requires_approved(self):
        """Core: Publishing (SI-10). Publishing draft/in_review -> ValidationError, no pub id consumed."""
        store, site, _ = make_store()
        item = make_item(store, site)
        with self.assertRaises(ValidationError):
            store.publish_item(PUBLISHER, item["id"])
        store.submit_item(AUTHOR, item["id"])
        with self.assertRaises(ValidationError):
            store.publish_item(PUBLISHER, item["id"])
        self.assertEqual(store.list_publish_records(actor=ADMIN), [])

    def test_publish_roles(self):
        """Core: Publishing (AC-3). item_publish is admin/publisher only."""
        store, site, _ = make_store()
        item = make_item(store, site)
        drive_to_approved(store, item)
        for user in (EDITOR, AUTHOR, VIEWER):
            with self.assertRaises(PermissionDenied):
                store.publish_item(user, item["id"])

    def test_archive_published_only(self):
        """Core: Publishing. archive_item: published -> archived; archiving a draft -> ValidationError."""
        store, site, _ = make_store()
        item = make_item(store, site)
        with self.assertRaises(ValidationError):
            store.archive_item(PUBLISHER, item["id"])
        drive_to_approved(store, item)
        store.publish_item(PUBLISHER, item["id"])
        archived = store.archive_item(ADMIN, item["id"])
        self.assertEqual(archived["status"], "archived")
        self.assertIsNone(archived["window_state"])
        self.assertFalse(archived["is_live"])
        with self.assertRaises(ValidationError):
            store.archive_item(PUBLISHER, item["id"])


class TestWindowState(unittest.TestCase):
    """Core: Publishing -- derived window state (delivery_publishing)."""

    def _published(self, store, site, slug, **kw):
        item = make_item(store, site, slug=slug)
        drive_to_approved(store, item)
        return store.publish_item(PUBLISHER, item["id"], **kw)

    def test_scheduled_live_expired_with_pinned_now(self):
        """Core: Publishing. window_state is scheduled before publish_at, live inside the window, expired at/after expire_at -- all at pinned now values."""
        store, site, _ = make_store()
        published = self._published(
            store, site, "windowed",
            publish_at="2026-06-10T00:00:00+00:00",
            expire_at="2026-06-20T00:00:00+00:00")
        item_id = published["id"]
        self.assertEqual(store.get_item(item_id, ADMIN, now="2026-06-09T00:00:00+00:00")["window_state"], "scheduled")
        self.assertFalse(store.get_item(item_id, ADMIN, now="2026-06-09T00:00:00+00:00")["is_live"])
        self.assertEqual(store.get_item(item_id, ADMIN, now=NOW)["window_state"], "live")
        self.assertTrue(store.get_item(item_id, ADMIN, now=NOW)["is_live"])
        self.assertEqual(store.get_item(item_id, ADMIN, now="2026-06-20T00:00:00+00:00")["window_state"], "expired")
        self.assertEqual(store.get_item(item_id, ADMIN, now="2026-07-01T00:00:00+00:00")["window_state"], "expired")

    def test_live_without_window_and_none_when_not_published(self):
        """Core: Publishing. No publish_at/expire_at -> live at any now >= publication; draft -> window_state None."""
        store, site, _ = make_store()
        item = make_item(store, site, slug="plain-live")
        self.assertIsNone(store.get_item(item["id"], ADMIN, now=NOW)["window_state"])
        drive_to_approved(store, item)
        store.publish_item(PUBLISHER, item["id"])
        got = store.get_item(item["id"], ADMIN, now="2030-01-01T00:00:00+00:00")
        self.assertEqual(got["window_state"], "live")
        self.assertTrue(got["is_live"])

    def test_module_window_state_function(self):
        """Core: Publishing. Module-level window_state(item, record, now) computes from stored facts only."""
        item = {"status": "published"}
        rec = {"publish_at": "2026-06-10T00:00:00+00:00", "expire_at": "2026-06-20T00:00:00+00:00",
               "published_utc": "2026-06-01T00:00:00+00:00"}
        self.assertEqual(window_state(item, rec, now="2026-06-05T00:00:00+00:00"), "scheduled")
        self.assertEqual(window_state(item, rec, now=NOW), "live")
        self.assertEqual(window_state(item, rec, now="2026-06-25T00:00:00+00:00"), "expired")
        self.assertIsNone(window_state({"status": "draft"}, rec, now=NOW))
        self.assertIsNone(window_state(item, None, now=NOW))

    def test_expire_not_after_publish_rejected(self):
        """Core: Publishing (SI-10). expire_at <= publish_at -> ValidationError, item stays approved, no pub record."""
        store, site, _ = make_store()
        item = make_item(store, site)
        drive_to_approved(store, item)
        for pub_at, exp_at in (("2026-06-10T00:00:00+00:00", "2026-06-10T00:00:00+00:00"),
                               ("2026-06-10T00:00:00+00:00", "2026-06-01T00:00:00+00:00")):
            with self.subTest(publish_at=pub_at, expire_at=exp_at):
                with self.assertRaises(ValidationError):
                    store.publish_item(PUBLISHER, item["id"], publish_at=pub_at, expire_at=exp_at)
        self.assertEqual(store.get_item(item["id"], ADMIN)["status"], "approved")
        self.assertEqual(store.list_publish_records(actor=ADMIN), [])

    def test_list_items_derived_window(self):
        """Core: Publishing. list_items carries window_state/is_live derived against its now parameter."""
        store, site, _ = make_store()
        self._published(store, site, "listed-window",
                        publish_at="2026-06-10T00:00:00+00:00",
                        expire_at="2026-06-20T00:00:00+00:00")
        listed = store.list_items(actor=ADMIN, now=NOW)
        self.assertEqual(listed[0]["window_state"], "live")
        self.assertTrue(listed[0]["is_live"])


if __name__ == "__main__":
    unittest.main()
