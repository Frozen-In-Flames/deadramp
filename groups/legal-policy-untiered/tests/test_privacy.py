"""Privacy discipline: entity shapes are pinned, content cannot enter.

Traces to: the hard privacy rule in UNION-SPEC.md — records hold
metadata and digests, not content; search queries are stored as
SHA-256 digests only; no entity shape can hold a real identifier of
a person or a matter's substance; nothing is scored. These tests pin
the exact key set of every entity the build can produce (including
the session's derived read view and the report), and show that
smuggled fields are rejected by the store's signatures themselves.
"""

import unittest

import legalpol_helpers as H

EXPECTED_SHAPES = {
    "agency": {"id", "agency_ref", "label", "members", "created_by",
               "created_utc"},
    "workspace": {"id", "agency_id", "workspace_ref", "title",
                  "created_by", "created_utc"},
    "session": {"id", "agency_id", "workspace_id", "session_ref",
                "purpose", "sandbox", "status", "expires_at",
                "created_by", "created_utc"},
    "session_view": {"id", "agency_id", "workspace_id", "session_ref",
                     "purpose", "sandbox", "status", "expires_at",
                     "created_by", "created_utc", "expired",
                     "sandbox_consumed"},
    "execution": {"id", "agency_id", "session_id", "execution_ref",
                  "kind", "language", "created_by", "created_utc"},
    "library_source": {"id", "source_ref", "kind", "title",
                       "jurisdiction_ref", "created_by", "created_utc"},
    "search": {"id", "agency_id", "workspace_id", "search_ref",
               "query_sha256", "result_count", "created_by",
               "created_utc"},
    "document": {"id", "agency_id", "workspace_id", "session_id",
                 "doc_ref", "kind", "sha256", "size_bytes",
                 "created_by", "created_utc"},
    "usage": {"id", "agency_id", "workspace_id", "session_id",
              "usage_ref", "kind", "quantity", "created_by",
              "created_utc"},
    "export": {"id", "agency_id", "export_ref", "since", "until",
               "record_count", "total_quantity", "checksum",
               "created_by", "created_utc"},
    "report": {"agency_id", "workspace_count", "session_count",
               "sessions_by_status", "sandbox_sessions",
               "sandbox_sessions_consumed", "execution_count",
               "search_count", "document_count", "export_count",
               "usage_by_kind"},
    "verify": {"document_id", "sha256", "computed_sha256", "matches"},
}

FORBIDDEN_FIELD_WORDS = ("ssn", "dob", "address", "phone", "email",
                         "content", "body", "defendant", "suspect",
                         "victim", "score", "rating")


class TestPrivacyShapes(unittest.TestCase):
    """Privacy rule: every entity's key set is exactly the contract's."""

    def setUp(self):
        self.store, _audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)
        self.wid = self.workspace["id"]
        self.session = H.make_session(self.store, self.agency, self.workspace,
                                      sandbox=True)
        self.execution = self.store.record_execution(
            self.aid, self.session["id"], "EXE-1", H.MEMBER)
        self.source = self.store.register_library_source(
            "LIB-1", "statute", H.MEMBER)
        self.search = self.store.save_search(
            self.aid, "SEA-1", H.QUERY_SHA256, 2, H.MEMBER)
        self.doc = self.store.register_document(
            self.aid, self.wid, "DOC-1", H.DOC_SHA256, 5, H.MEMBER)
        self.usage = self.store.record_usage(
            self.aid, "USE-1", "search", 2, H.MEMBER)
        self.export = self.store.export_usage(self.aid, "EXP-1", H.MEMBER)

    def test_all_entity_shapes_exact(self):
        """Privacy: agency, workspace, session (stored + derived
        view), execution, library source, search, document, usage,
        export, report, and verify shapes are all exact."""
        entities = {
            "agency": self.store.get_agency(self.aid, H.ADMIN),
            "workspace": self.workspace,
            "session": self.session,
            "session_view": self.store.get_session(
                self.aid, self.session["id"], H.MEMBER),
            "execution": self.execution,
            "library_source": self.source,
            "search": self.search,
            "document": self.doc,
            "usage": self.usage,
            "export": self.export,
            "report": self.store.agency_report(self.aid, H.MEMBER),
            "verify": self.store.verify_document(
                self.aid, self.doc["id"], H.DOC_CONTENT, H.MEMBER),
        }
        for kind, entity in entities.items():
            self.assertEqual(set(entity.keys()), EXPECTED_SHAPES[kind], kind)

    def test_no_field_can_hold_person_content_or_score(self):
        """Privacy: no key in any shape is a person identifier, a
        content field, or a score/rating field."""
        for kind, keys in EXPECTED_SHAPES.items():
            for key in keys:
                for word in FORBIDDEN_FIELD_WORDS:
                    self.assertNotEqual(key, word, (kind, key))
                    self.assertFalse(key.endswith("_" + word), (kind, key))
        # The sole content-adjacent fields are one-way digests:
        self.assertEqual(len(self.search["query_sha256"]), 64)
        self.assertEqual(len(self.doc["sha256"]), 64)
        self.assertEqual(len(self.export["checksum"]), 64)

    def test_smuggled_fields_are_rejected_by_signature(self):
        """Privacy: the store's methods have fixed signatures; an
        attempt to pass a content/name/query field fails with
        TypeError before any record exists."""
        with self.assertRaises(TypeError):
            self.store.create_agency("REF-X", "Label", H.ADMIN,
                                     subject_name="Jane Doe")
        with self.assertRaises(TypeError):
            self.store.register_document(
                self.aid, self.wid, "DOC-X", H.DOC_SHA256, 1, H.MEMBER,
                content=b"the document itself")
        with self.assertRaises(TypeError):
            self.store.save_search(
                self.aid, "SEA-X", H.QUERY_SHA256, 1, H.MEMBER,
                query_text="the actual question")
        with self.assertRaises(TypeError):
            self.store.record_usage(
                self.aid, "USE-X", "search", 1, H.MEMBER, score=99)
        with self.assertRaises(TypeError):
            self.store.record_execution(
                self.aid, self.session["id"], "EXE-X", H.MEMBER,
                code="print('hello')")
        with self.assertRaises(TypeError):
            self.store.create_session(
                self.aid, self.wid, "SES-X", H.MEMBER, transcript="...")

    def test_query_text_appears_nowhere_in_the_search_record(self):
        """Privacy: the stored search record holds the digest; the
        query text appears in no field of it."""
        for value in self.search.values():
            self.assertNotEqual(value, H.QUERY_TEXT)
            if isinstance(value, str):
                self.assertNotIn(H.QUERY_TEXT, value)


if __name__ == "__main__":
    unittest.main()
