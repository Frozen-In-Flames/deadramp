"""Artifact registry tests incl. checksum verify.

Traces to: Core function 6 (artifact registry w/ checksums, SI-10) --
``art-`` records hold sha256 + size, NOT content; verify compares hash.
"""

import hashlib
import unittest

from devtools_helpers import ADMIN, make_store
from devtools.errors import NotFoundError, ValidationError


class TestArtifacts(unittest.TestCase):
    """Core 6: artifact registration, checksum computation, verification."""

    def test_register_with_content_computes_sha_and_size(self):
        """Core 6: content (str) -> sha256 via hashlib, size_bytes = len(utf-8 bytes), no content stored."""
        store, project = make_store()
        content = "hello artifact"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        art = store.register_artifact(project["id"], "pkg.bin", ADMIN, version="1.0", content=content)
        self.assertEqual(art["id"], "art-1")
        self.assertEqual(art["sha256"], expected)
        self.assertEqual(art["size_bytes"], len(content.encode("utf-8")))
        self.assertNotIn("content", art)

    def test_register_bytes_content(self):
        """Core 6: bytes content hashes the raw bytes."""
        store, project = make_store()
        art = store.register_artifact(project["id"], "raw", ADMIN, content=b"\x00\x01")
        self.assertEqual(art["sha256"], hashlib.sha256(b"\x00\x01").hexdigest())
        self.assertEqual(art["size_bytes"], 2)

    def test_register_checksum_only(self):
        """Core 6: checksum-only registration is allowed; size_bytes is None."""
        store, project = make_store()
        digest = hashlib.sha256(b"x").hexdigest()
        art = store.register_artifact(project["id"], "ext", ADMIN, checksum=digest)
        self.assertEqual(art["sha256"], digest)
        self.assertIsNone(art["size_bytes"])

    def test_neither_checksum_nor_content_rejected(self):
        """Core 6 (SI-10): neither checksum nor content -> ValidationError, nothing stored."""
        store, project = make_store()
        with self.assertRaises(ValidationError):
            store.register_artifact(project["id"], "empty", ADMIN)
        self.assertEqual(store.list_artifacts(), [])

    def test_mismatched_checksum_and_content_rejected(self):
        """Core 6 checksum-integrity: checksum+content differing -> ValidationError, no id consumed."""
        store, project = make_store()
        wrong = hashlib.sha256(b"other").hexdigest()
        with self.assertRaises(ValidationError):
            store.register_artifact(project["id"], "bad", ADMIN, checksum=wrong, content="real")
        self.assertEqual(store.list_artifacts(), [])
        art = store.register_artifact(project["id"], "good", ADMIN, content="real")
        self.assertEqual(art["id"], "art-1")

    def test_verify_artifact_true_and_tampered_false(self):
        """Core 6 checksum-integrity: verify_artifact True iff sha256(content) equals stored checksum."""
        store, project = make_store()
        art = store.register_artifact(project["id"], "pkg", ADMIN, content="original")
        self.assertTrue(store.verify_artifact(art["id"], "original", ADMIN))
        self.assertTrue(store.verify_artifact(art["id"], b"original", ADMIN))
        self.assertFalse(store.verify_artifact(art["id"], "tampered", ADMIN))
        with self.assertRaises(NotFoundError):
            store.verify_artifact("art-999", "x", ADMIN)


if __name__ == "__main__":
    unittest.main()
