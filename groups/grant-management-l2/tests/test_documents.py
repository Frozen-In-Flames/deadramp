"""Core: Document & signature records. Traces to UNION-SPEC core
function 7 (document_management, e_signature). Records hold metadata
and a caller-supplied checksum only; no content is stored, and a
signature is a recorded event, not a signing engine."""

import unittest

import grants_helpers as H
from grants.errors import NotFoundError, ValidationError


class TestDocuments(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()
        self.app = H.make_application(self.store, self.program, self.org)

    def _create(self, **overrides):
        kwargs = {
            "target_type": "application",
            "target_id": self.app["id"],
            "name": "proposal.pdf",
            "kind": "proposal",
            "sha256": H.SHA256_A,
            "size_bytes": 2048,
        }
        kwargs.update(overrides)
        return self.store.create_document(H.MEMBER, **kwargs)

    def test_create_shape(self):
        doc = self._create()
        self.assertTrue(doc["id"].startswith("doc-"))
        self.assertEqual(doc["sha256"], H.SHA256_A)
        self.assertIsNone(doc["signed_by"])
        self.assertEqual(doc["program_id"], self.program["id"])

    def test_checksum_normalized_lowercase(self):
        doc = self._create(sha256="A" * 64)
        self.assertEqual(doc["sha256"], "a" * 64)

    def test_bad_inputs_rejected(self):
        for overrides in (
            {"sha256": "abc"},
            {"sha256": "g" * 64},
            {"kind": "video"},
            {"size_bytes": -1},
            {"size_bytes": 1.5},
            {"size_bytes": True},
            {"target_type": "person"},
        ):
            with self.assertRaises(ValidationError, msg=repr(overrides)):
                self._create(**overrides)

    def test_unknown_target_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self._create(target_id="app-99")

    def test_sign_records_the_event(self):
        doc = self._create(kind="agreement")
        signed = self.store.sign_document(H.STAFF, doc["id"])
        self.assertEqual(signed["signed_by"], "erin")
        self.assertIsNotNone(signed["signed_at"])
        with self.assertRaises(ValidationError):
            self.store.sign_document(H.STAFF, doc["id"])

    def test_list_documents_by_target(self):
        self._create()
        self._create(name="budget.xlsx", kind="budget", sha256=H.SHA256_B)
        docs = self.store.list_documents(H.MEMBER, "application", self.app["id"])
        self.assertEqual(len(docs), 2)
        self.assertEqual(
            self.store.list_documents(H.MEMBER, "program", self.program["id"]),
            [])


if __name__ == "__main__":
    unittest.main()
