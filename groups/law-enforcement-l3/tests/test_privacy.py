"""Privacy discipline: entity shapes are pinned, content cannot enter.

Traces to: the hard privacy rule in UNION-SPEC.md -- records are
keyed by opaque caller-supplied references only; no entity shape can
hold a real name, a case subject, evidence content, or any
person-identifying data; documents are metadata + SHA-256, searches
and annotations are digests only. These tests pin the exact key set
of every entity the build can produce and show that smuggled fields
are rejected by the store's signatures themselves.
"""

import unittest

from lawenf_helpers import (DOC_SHA256, MEMBER, NOTE_SHA256, QUERY_SHA256,
                            make_store)

EXPECTED_SHAPES = {
    "matter": {"id", "matter_ref", "status", "members", "created_by",
               "created_utc"},
    "source": {"id", "matter_id", "source_ref", "kind", "jurisdiction_ref",
               "citation_ref", "created_by", "created_utc"},
    "document": {"id", "matter_id", "doc_ref", "sha256", "size_bytes",
                 "status", "created_by", "created_utc"},
    "search": {"id", "matter_id", "search_ref", "query_sha256",
               "result_count", "created_by", "created_utc"},
    "annotation": {"id", "matter_id", "target_kind", "target_id",
                   "annotation_ref", "note_sha256", "created_by",
                   "created_utc"},
    "citation_check": {"id", "matter_id", "citation_ref", "source_id",
                       "treatment", "created_by", "created_utc"},
}

FORBIDDEN_FIELD_WORDS = ("name", "title", "subject", "ssn", "dob",
                         "address", "phone", "email", "content", "body",
                         "text", "note", "query", "defendant", "suspect",
                         "victim", "officer")


class TestPrivacyShapes(unittest.TestCase):
    """Privacy rule: every entity's key set is exactly the contract's."""

    def setUp(self):
        self.store, _audit, self.matter = make_store()
        self.mid = self.matter["id"]
        self.src = self.store.create_source(self.mid, "SRC-1", "statute", MEMBER)
        self.doc = self.store.register_document(
            self.mid, "DOC-1", DOC_SHA256, 10, MEMBER)
        self.sea = self.store.save_search(self.mid, "SEA-1", QUERY_SHA256, 1, MEMBER)
        self.ann = self.store.add_annotation(
            self.mid, "document", self.doc["id"], "ANN-1", NOTE_SHA256, MEMBER)
        self.cit = self.store.record_citation_check(
            self.mid, "CIT-1", "followed", MEMBER)

    def test_all_entity_shapes_exact(self):
        entities = {
            "matter": self.store.get_matter(self.mid, MEMBER),
            "source": self.src,
            "document": self.doc,
            "search": self.sea,
            "annotation": self.ann,
            "citation_check": self.cit,
        }
        for kind, entity in entities.items():
            self.assertEqual(set(entity.keys()), EXPECTED_SHAPES[kind], kind)

    def test_no_field_can_hold_person_or_content_data(self):
        for kind, keys in EXPECTED_SHAPES.items():
            for key in keys:
                for word in FORBIDDEN_FIELD_WORDS:
                    self.assertNotEqual(key, word, (kind, key))
                    self.assertFalse(key.endswith("_" + word), (kind, key))
        # digests are the sole content-adjacent fields, and they are
        # one-way hashes by construction (64 lowercase hex chars):
        self.assertEqual(len(self.sea["query_sha256"]), 64)
        self.assertEqual(len(self.ann["note_sha256"]), 64)

    def test_smuggled_fields_are_rejected_by_signature(self):
        # The store's methods have fixed signatures; an attempt to
        # pass a name/subject/content field fails before any record
        # exists.
        with self.assertRaises(TypeError):
            self.store.create_matter("REF-X", MEMBER, subject_name="Jane Doe")
        with self.assertRaises(TypeError):
            self.store.register_document(
                self.mid, "DOC-X", DOC_SHA256, 1, MEMBER, content=b"evidence")
        with self.assertRaises(TypeError):
            self.store.save_search(
                self.mid, "SEA-X", QUERY_SHA256, 1, MEMBER,
                query_text="the actual question")
        with self.assertRaises(TypeError):
            self.store.add_annotation(
                self.mid, "document", self.doc["id"], "ANN-X",
                NOTE_SHA256, MEMBER, note_text="the actual note")

    def test_returned_records_are_copies(self):
        got = self.store.get_matter(self.mid, MEMBER)
        got["members"].append("mallory")
        got["status"] = "closed"
        fresh = self.store.get_matter(self.mid, MEMBER)
        self.assertNotIn("mallory", fresh["members"])
        self.assertEqual(fresh["status"], "open")


if __name__ == "__main__":
    unittest.main()
