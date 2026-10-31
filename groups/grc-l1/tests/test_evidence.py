"""Evidence registry tests.

Traces to: Core function 4 (evidence registry — artifacts as metadata
records plus a SHA-256 checksum of supplied content, verify-by-content
supported, each artifact linked to controls/systems; validation status
is a recorded field set by an authorized reviewer, never computed);
control families CA-2 / AU-9.
"""

import hashlib
import unittest

from grc_helpers import ADMIN, MEMBER, VIEWER, SYSTEM_REF, make_store
from grc.errors import NotFoundError, PermissionDenied, ValidationError

CONTENT = "the quarterly access review worksheet, final"
CONTENT_SHA256 = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class TestEvidenceRegistry(unittest.TestCase):
    """Core 4: evidence metadata records and checksums."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()

    def _evidence(self, **kwargs):
        kwargs.setdefault("actor", MEMBER)
        return self.store.create_evidence(
            "access review worksheet", CONTENT, ["AC-2"], [SYSTEM_REF], **kwargs
        )

    def test_create_evidence_shape(self):
        """Core 4. The record carries metadata, the SHA-256 of the
        supplied content, its byte size, control/system links, an
        initial recorded validation status of "unvalidated", and
        provenance — and no content itself."""
        evidence = self._evidence()
        self.assertEqual(evidence["id"], "ev-1")
        self.assertEqual(evidence["sha256"], CONTENT_SHA256)
        self.assertEqual(evidence["size_bytes"], len(CONTENT.encode("utf-8")))
        self.assertEqual(evidence["control_ids"], ["AC-2"])
        self.assertEqual(evidence["system_refs"], [SYSTEM_REF])
        self.assertEqual(evidence["validation_status"], "unvalidated")
        self.assertIsNone(evidence["validated_by"])
        self.assertEqual(evidence["created_by"], "bob")
        self.assertNotIn("content", evidence)

    def test_verify_by_content_original_true_tampered_false(self):
        """Core 4. Verify-by-content: the original content verifies
        True; tampered content verifies False; so does content that
        differs only by a trailing newline."""
        evidence = self._evidence()
        self.assertTrue(
            self.store.verify_evidence(evidence["id"], CONTENT, actor=VIEWER)
        )
        self.assertFalse(
            self.store.verify_evidence(evidence["id"], CONTENT + "x", actor=VIEWER)
        )
        self.assertFalse(
            self.store.verify_evidence(evidence["id"], CONTENT + "\n", actor=VIEWER)
        )
        self.assertFalse(
            self.store.verify_evidence(evidence["id"], "", actor=VIEWER)
        )

    def test_verify_accepts_bytes_content(self):
        """Core 4. Content supplied as bytes hashes identically to the
        same text supplied as a string."""
        evidence = self._evidence()
        self.assertTrue(
            self.store.verify_evidence(
                evidence["id"], CONTENT.encode("utf-8"), actor=ADMIN
            )
        )
        created = self.store.create_evidence(
            "bytes artifact", CONTENT.encode("utf-8"), [], [], actor=MEMBER
        )
        self.assertEqual(created["sha256"], CONTENT_SHA256)

    def test_verify_unknown_evidence_404(self):
        """Core 4. Verifying an unknown artifact is a NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.verify_evidence("ev-404", CONTENT, actor=ADMIN)

    def test_create_evidence_link_validation(self):
        """Core 4. Unknown control ids or system refs are
        ValidationError, and a failed creation consumes no id."""
        with self.assertRaises(ValidationError):
            self.store.create_evidence("bad", CONTENT, ["ZZ-9"], [], actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.store.create_evidence("bad", CONTENT, [], ["NOPE"], actor=MEMBER)
        evidence = self._evidence()
        self.assertEqual(evidence["id"], "ev-1")

    def test_create_evidence_bad_content_type_rejected(self):
        """Core 4. Content that is neither string nor bytes is a
        ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_evidence("bad", 12345, [], [], actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.store.create_evidence("bad", None, [], [], actor=MEMBER)

    def test_list_evidence_filters(self):
        """Core 4. list_evidence filters by linked system and by
        linked control."""
        first = self._evidence()
        second = self.store.create_evidence(
            "config baseline", "baseline text", ["CM-6"], [], actor=MEMBER
        )
        by_system = self.store.list_evidence(actor=ADMIN, system_ref=SYSTEM_REF)
        self.assertEqual([e["id"] for e in by_system], [first["id"]])
        by_control = self.store.list_evidence(actor=ADMIN, control_id="CM-6")
        self.assertEqual([e["id"] for e in by_control], [second["id"]])
        self.assertEqual(len(self.store.list_evidence(actor=VIEWER)), 2)


class TestEvidenceReview(unittest.TestCase):
    """Core 4: validation status is a recorded reviewer field."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()
        self.evidence = self.store.create_evidence(
            "worksheet", CONTENT, ["AC-2"], [SYSTEM_REF], actor=MEMBER
        )

    def test_review_sets_status_verbatim_with_reviewer(self):
        """Core 4. An authorized reviewer sets the validation status;
        it is stored verbatim (reviewer wording untouched) with the
        reviewer's identity and a UTC timestamp."""
        reviewed = self.store.review_evidence(
            self.evidence["id"],
            "Accepted as-is (reviewer wording)",
            actor=ADMIN,
            note="matches the worksheet on file",
        )
        self.assertEqual(
            reviewed["validation_status"], "Accepted as-is (reviewer wording)"
        )
        self.assertEqual(reviewed["validated_by"], "alice")
        self.assertTrue(reviewed["validated_utc"].endswith("+00:00"))
        self.assertEqual(reviewed["review_note"], "matches the worksheet on file")
        stored = self.store.get_evidence(self.evidence["id"], actor=VIEWER)
        self.assertEqual(stored["validation_status"], "Accepted as-is (reviewer wording)")

    def test_review_requires_review_permission(self):
        """Core 4 + Core 9 RBAC. The member who filed the evidence may
        not review it (review_evidence is admin-only), and neither may
        a viewer; the recorded status is unchanged after the denials."""
        with self.assertRaises(PermissionDenied):
            self.store.review_evidence(self.evidence["id"], "ok", actor=MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.review_evidence(self.evidence["id"], "ok", actor=VIEWER)
        stored = self.store.get_evidence(self.evidence["id"], actor=ADMIN)
        self.assertEqual(stored["validation_status"], "unvalidated")

    def test_review_empty_status_rejected_and_unknown_404(self):
        """Core 4. An empty validation status is a ValidationError;
        reviewing a missing artifact is a NotFoundError."""
        with self.assertRaises(ValidationError):
            self.store.review_evidence(self.evidence["id"], "", actor=ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.review_evidence("ev-404", "ok", actor=ADMIN)

    def test_verify_does_not_change_validation_status(self):
        """Core 4. Verification by content is a checksum comparison
        only: a successful verify never flips the recorded validation
        status — only a reviewer's recorded decision does."""
        self.assertTrue(
            self.store.verify_evidence(self.evidence["id"], CONTENT, actor=ADMIN)
        )
        stored = self.store.get_evidence(self.evidence["id"], actor=ADMIN)
        self.assertEqual(stored["validation_status"], "unvalidated")
        self.assertIsNone(stored["validated_by"])


if __name__ == "__main__":
    unittest.main()
