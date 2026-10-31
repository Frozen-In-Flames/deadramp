"""Document registry; verify-by-content.

Traces to: Core functions 7 (Document generation, as the registry)
and 8 (Verify-by-content) in UNION-SPEC.md, and SI-7 (information
integrity) — documents are registry metadata + a SHA-256 checksum
(validated lowercase hex) and a byte count; content is never stored.
Verify-by-content recomputes the hash of caller-supplied bytes and
compares; it stores nothing.
"""

import unittest

import legalpol_helpers as H
from legalpol.errors import NotFoundError, PermissionDenied, ValidationError


class DocumentFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)
        self.wid = self.workspace["id"]


class TestDocuments(DocumentFixture):
    """Core 7: document registry records."""

    def test_register_document_shape_and_defaults(self):
        """Core 7: document shape is pinned; kind defaults to generated."""
        doc = self.store.register_document(
            self.aid, self.wid, "DOC-REF-1", H.DOC_SHA256,
            len(H.DOC_CONTENT), H.MEMBER)
        self.assertEqual(set(doc.keys()), {
            "id", "agency_id", "workspace_id", "session_id", "doc_ref",
            "kind", "sha256", "size_bytes", "created_by", "created_utc"})
        self.assertEqual(doc["id"], "doc-1")
        self.assertEqual(doc["kind"], "generated")
        self.assertIsNone(doc["session_id"])

    def test_checksum_must_be_lowercase_hex(self):
        """Core 7 / SI-7 + SI-10: uppercase, short, and non-hex
        checksums are rejected whole."""
        for bad in ("A" * 64, H.DOC_SHA256.upper(), "a" * 63, "z" * 64):
            with self.assertRaises(ValidationError, msg=bad[:8]):
                self.store.register_document(self.aid, self.wid, "DOC-BAD",
                                             bad, 1, H.MEMBER)

    def test_size_and_kind_validation(self):
        """Core 7 / SI-10: size_bytes is an int >= 0 (bool/float
        rejected); kind is generated or uploaded."""
        for bad in (True, 2.5, -1, "10"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.register_document(self.aid, self.wid, "DOC-BAD",
                                             H.DOC_SHA256, bad, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_document(self.aid, self.wid, "DOC-BAD",
                                         H.DOC_SHA256, 1, H.MEMBER,
                                         kind="scanned")
        doc = self.store.register_document(self.aid, self.wid, "DOC-UP",
                                           H.DOC_SHA256, 0, H.MEMBER,
                                           kind="uploaded")
        self.assertEqual(doc["size_bytes"], 0)

    def test_doc_ref_unique_within_workspace(self):
        """Core 7: doc_ref is unique within the workspace, free in
        another workspace of the same agency."""
        self.store.register_document(self.aid, self.wid, "DOC-1",
                                     H.DOC_SHA256, 1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_document(self.aid, self.wid, "DOC-1",
                                         H.SHA256_A, 2, H.MEMBER)
        other_ws = H.make_workspace(self.store, self.agency,
                                    workspace_ref="WSP-REF-002", title="Two")
        twin = self.store.register_document(self.aid, other_ws["id"], "DOC-1",
                                            H.DOC_SHA256, 1, H.MEMBER)
        self.assertEqual(twin["doc_ref"], "DOC-1")

    def test_session_link_must_be_in_the_workspace(self):
        """Core 7: session_id, when given, must name a session in
        this workspace — a session elsewhere is NotFound."""
        session = H.make_session(self.store, self.agency, self.workspace)
        doc = self.store.register_document(
            self.aid, self.wid, "DOC-1", H.DOC_SHA256, 1, H.MEMBER,
            session_id=session["id"])
        self.assertEqual(doc["session_id"], session["id"])
        other_ws = H.make_workspace(self.store, self.agency,
                                    workspace_ref="WSP-REF-002", title="Two")
        with self.assertRaises(NotFoundError):
            self.store.register_document(
                self.aid, other_ws["id"], "DOC-2", H.DOC_SHA256, 1, H.MEMBER,
                session_id=session["id"])

    def test_list_and_get_documents(self):
        """Core 7: listing filters by workspace; cross-agency gets
        are NotFound; the viewer reads but cannot register."""
        doc = self.store.register_document(self.aid, self.wid, "DOC-1",
                                           H.DOC_SHA256, 1, H.MEMBER)
        self.assertEqual(
            self.store.get_document(self.aid, doc["id"], H.VIEWER)["id"],
            doc["id"])
        self.assertEqual(
            len(self.store.list_documents(self.aid, H.MEMBER,
                                          workspace_id=self.wid)), 1)
        other = self.store.create_agency("AGY-REF-002", "Second", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_document(other["id"], doc["id"], H.ADMIN)
        with self.assertRaises(PermissionDenied):
            self.store.register_document(self.aid, self.wid, "DOC-2",
                                         H.DOC_SHA256, 1, H.VIEWER)


class TestVerifyByContent(DocumentFixture):
    """Core 8: verify-by-content (SI-7)."""

    def setUp(self):
        super().setUp()
        self.doc = self.store.register_document(
            self.aid, self.wid, "DOC-1", H.DOC_SHA256,
            len(H.DOC_CONTENT), H.MEMBER)

    def test_verify_exact_bytes_match(self):
        """Core 8: the registered bytes verify; the result shape is
        exactly {document_id, sha256, computed_sha256, matches}."""
        result = self.store.verify_document(self.aid, self.doc["id"],
                                            H.DOC_CONTENT, H.VIEWER)
        self.assertEqual(set(result.keys()), {
            "document_id", "sha256", "computed_sha256", "matches"})
        self.assertTrue(result["matches"])
        self.assertEqual(result["computed_sha256"], H.DOC_SHA256)

    def test_verify_altered_bytes_do_not_match(self):
        """Core 8 / SI-7: altered bytes do not verify."""
        result = self.store.verify_document(
            self.aid, self.doc["id"], H.DOC_CONTENT + b" -- altered", H.MEMBER)
        self.assertFalse(result["matches"])
        self.assertNotEqual(result["computed_sha256"], H.DOC_SHA256)

    def test_verify_accepts_str_content_as_utf8(self):
        """Core 8: a str is encoded as UTF-8 before hashing."""
        result = self.store.verify_document(
            self.aid, self.doc["id"], H.DOC_CONTENT.decode("utf-8"), H.MEMBER)
        self.assertTrue(result["matches"])

    def test_verify_stores_nothing(self):
        """Core 8: verification is non-mutating — no new records, no
        new audit entries."""
        docs_before = len(self.store.list_documents(self.aid, H.MEMBER))
        audit_before = len(self.audit.entries())
        self.store.verify_document(self.aid, self.doc["id"], H.DOC_CONTENT,
                                   H.MEMBER)
        self.assertEqual(len(self.store.list_documents(self.aid, H.MEMBER)),
                         docs_before)
        self.assertEqual(len(self.audit.entries()), audit_before)


if __name__ == "__main__":
    unittest.main()
