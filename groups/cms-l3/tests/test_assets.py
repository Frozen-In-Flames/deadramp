"""Assets tests.

Traces to: Core function 6 -- Assets / sibling claim families
media_assets, ingestion_repository; AC-3, SI-10.
"""

import hashlib
import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, make_store
from cms.errors import NotFoundError, PermissionDenied, ValidationError

DATA = b"hello cms asset"
SHA = hashlib.sha256(DATA).hexdigest()


class TestAssets(unittest.TestCase):
    """Core: Assets (media_assets / ingestion_repository)."""

    def test_register_shape_and_kinds(self):
        """Core: Assets. register_asset -> asset-{n} with metadata; all pinned kinds accepted."""
        store, site, _ = make_store()
        for i, kind in enumerate(("document", "image", "video", "audio", "dataset", "other")):
            asset = store.register_asset(EDITOR, site["id"], "f-%s" % kind, kind, 100 + i,
                                         mime_type="application/octet-stream")
            self.assertEqual(asset["id"], "asset-%d" % (i + 1))
            self.assertEqual(asset["kind"], kind)
        self.assertEqual(len(store.list_assets(site_id=site["id"], actor=VIEWER)), 6)

    def test_checksum_computed_from_data(self):
        """Core: Assets. Supplying data (bytes) computes and stores its SHA-256."""
        store, site, _ = make_store()
        asset = store.register_asset(AUTHOR, site["id"], "note.txt", "document",
                                     len(DATA), data=DATA)
        self.assertEqual(asset["content_sha256"], SHA)

    def test_checksum_supplied_without_data_stored(self):
        """Core: Assets. A supplied checksum without data is stored as the checksum."""
        store, site, _ = make_store()
        asset = store.register_asset(PUBLISHER, site["id"], "img.png", "image", 5,
                                     content_sha256=SHA)
        self.assertEqual(asset["content_sha256"], SHA)

    def test_checksum_mismatch_rejected_no_id(self):
        """Core: Assets (SI-10). data whose SHA-256 differs from content_sha256 -> ValidationError, no id consumed."""
        store, site, _ = make_store()
        wrong = hashlib.sha256(b"other").hexdigest()
        with self.assertRaises(ValidationError):
            store.register_asset(AUTHOR, site["id"], "x.bin", "other", len(DATA),
                                 content_sha256=wrong, data=DATA)
        ok = store.register_asset(AUTHOR, site["id"], "x.bin", "other", len(DATA), data=DATA)
        self.assertEqual(ok["id"], "asset-1")

    def test_bytes_not_retained(self):
        """Core: Assets. The asset record carries checksum+metadata only -- no data/bytes field anywhere."""
        store, site, _ = make_store()
        asset = store.register_asset(AUTHOR, site["id"], "note.txt", "document",
                                     len(DATA), data=DATA)
        self.assertNotIn("data", asset)
        for value in asset.values():
            self.assertNotEqual(value, DATA)
            self.assertNotIsInstance(value, (bytes, bytearray))
        fetched = store.get_asset(asset["id"], VIEWER)
        self.assertNotIn("data", fetched)

    def test_asset_validation(self):
        """Core: Assets (SI-10). Bad kind / negative or bool byte_size / bad checksum / unknown site rejected."""
        store, site, _ = make_store()
        with self.assertRaises(ValidationError):
            store.register_asset(EDITOR, site["id"], "f", "executable", 1)
        with self.assertRaises(ValidationError):
            store.register_asset(EDITOR, site["id"], "f", "image", -1)
        with self.assertRaises(ValidationError):
            store.register_asset(EDITOR, site["id"], "f", "image", True)
        with self.assertRaises(ValidationError):
            store.register_asset(EDITOR, site["id"], "f", "image", 1, content_sha256="xyz")
        with self.assertRaises(NotFoundError):
            store.register_asset(EDITOR, "site-999", "f", "image", 1)

    def test_asset_write_roles(self):
        """Core: Assets (AC-3). asset_write: admin/publisher/editor/author; viewer denied."""
        store, site, _ = make_store()
        with self.assertRaises(PermissionDenied):
            store.register_asset(VIEWER, site["id"], "f", "image", 1)
        self.assertEqual(store.register_asset(AUTHOR, site["id"], "f", "image", 1)["id"], "asset-1")

    def test_get_asset_unknown(self):
        """Core: Assets. Unknown asset -> NotFoundError."""
        store, site, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.get_asset("asset-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
