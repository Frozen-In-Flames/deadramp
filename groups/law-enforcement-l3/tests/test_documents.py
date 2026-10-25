"""Document registry & verify-by-content.

Traces to: Core 3 (Document registry) and Core 4 (Verify-by-content),
claim family ``document_management`` (2 of 2), and the SI-7 integrity
mapping in UNION-SPEC.md -- documents are metadata + SHA-256
checksums, never content; the review lifecycle is guarded; integrity
is proven by re-hashing caller-supplied bytes.
"""

import unittest

from lawenf.errors import ValidationError
from lawenf_helpers import (DOC_CONTENT, DOC_SHA256, MEMBER, VIEWER,
                            make_store)

DOC_KEYS = {"id", "matter_id", "doc_ref", "sha256", "size_bytes", "status",
            "created_by", "created_utc"}


class TestDocuments(unittest.TestCase):
    """Core 3: registration validates the checksum, never sees content."""

    def setUp(self):
        self.store, _audit, self.matter = make_store()
        self.mid = self.matter["id"]

    def test_shape_and_defaults(self):
        doc = self.store.register_document(
            self.mid, "DOC-1", DOC_SHA256, len(DOC_CONTENT), MEMBER)
        self.assertEqual(set(doc.keys()), DOC_KEYS)
        self.assertEqual(doc["status"], "registered")
        self.assertEqual(doc["size_bytes"], len(DOC_CONTENT))

    def test_checksum_must_be_64_lowercase_hex(self):
        for bad in ("xyz", "A" * 64, "a" * 63, "a" * 65, 12345, None):
            with self.assertRaises(ValidationError):
                self.store.register_document(self.mid, "DOC-1", bad, 1, MEMBER)

    def test_size_must_be_a_non_negative_int(self):
        for bad in (-1, 1.5, True, "10", None):
            with self.assertRaises(ValidationError):
                self.store.register_document(
                    self.mid, "DOC-1", DOC_SHA256, bad, MEMBER)
        doc = self.store.register_document(self.mid, "DOC-1", DOC_SHA256, 0, MEMBER)
        self.assertEqual(doc["size_bytes"], 0)

    def test_duplicate_ref_rejected(self):
        self.store.register_document(self.mid, "DOC-1", DOC_SHA256, 1, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_document(self.mid, "DOC-1", DOC_SHA256, 1, MEMBER)


class TestReviewLifecycle(unittest.TestCase):
    """Core 3: registered -> in_review -> reviewed, nothing else."""

    def setUp(self):
        self.store, _audit, self.matter = make_store()
        self.mid = self.matter["id"]
        self.doc = self.store.register_document(
            self.mid, "DOC-1", DOC_SHA256, len(DOC_CONTENT), MEMBER)

    def test_full_lifecycle(self):
        doc = self.store.begin_review(self.mid, self.doc["id"], MEMBER)
        self.assertEqual(doc["status"], "in_review")
        doc = self.store.complete_review(self.mid, self.doc["id"], MEMBER)
        self.assertEqual(doc["status"], "reviewed")

    def test_skipping_a_state_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.complete_review(self.mid, self.doc["id"], MEMBER)

    def test_terminal_state_is_terminal(self):
        self.store.begin_review(self.mid, self.doc["id"], MEMBER)
        self.store.complete_review(self.mid, self.doc["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.store.begin_review(self.mid, self.doc["id"], MEMBER)

    def test_viewer_cannot_review(self):
        from lawenf.errors import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.store.begin_review(self.mid, self.doc["id"], VIEWER)

    def test_list_filter_by_status(self):
        self.store.register_document(self.mid, "DOC-2", DOC_SHA256, 1, MEMBER)
        self.store.begin_review(self.mid, self.doc["id"], MEMBER)
        in_review = self.store.list_documents(self.mid, MEMBER, status="in_review")
        self.assertEqual([d["doc_ref"] for d in in_review], ["DOC-1"])
        with self.assertRaises(ValidationError):
            self.store.list_documents(self.mid, MEMBER, status="archived")


class TestVerifyByContent(unittest.TestCase):
    """Core 4 + SI-7: re-hashing proves integrity; nothing is stored."""

    def setUp(self):
        self.store, self.audit, self.matter = make_store()
        self.mid = self.matter["id"]
        self.doc = self.store.register_document(
            self.mid, "DOC-1", DOC_SHA256, len(DOC_CONTENT), MEMBER)

    def test_matching_content_verifies(self):
        result = self.store.verify_document(self.mid, self.doc["id"], DOC_CONTENT, VIEWER)
        self.assertTrue(result["matches"])
        self.assertEqual(result["computed_sha256"], DOC_SHA256)
        self.assertEqual(result["sha256"], DOC_SHA256)

    def test_str_content_is_encoded_utf8(self):
        text = "brief"
        import hashlib
        doc = self.store.register_document(
            self.mid, "DOC-T", hashlib.sha256(text.encode()).hexdigest(), 5, MEMBER)
        self.assertTrue(
            self.store.verify_document(self.mid, doc["id"], text, MEMBER)["matches"])

    def test_tampered_content_does_not_verify(self):
        result = self.store.verify_document(
            self.mid, self.doc["id"], DOC_CONTENT + b" ", MEMBER)
        self.assertFalse(result["matches"])

    def test_verify_is_non_mutating(self):
        before = len(self.audit.entries())
        self.store.verify_document(self.mid, self.doc["id"], DOC_CONTENT, MEMBER)
        self.assertEqual(len(self.audit.entries()), before)
        self.assertEqual(
            self.store.get_document(self.mid, self.doc["id"], MEMBER)["status"],
            "registered")


if __name__ == "__main__":
    unittest.main()
