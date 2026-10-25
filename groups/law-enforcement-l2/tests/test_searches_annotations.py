"""Saved-search records & annotation records (digest-only).

Traces to: Core 5 (Saved-search records), Core 6 (Annotation
records), and claim families ``legal_search`` (2 of 2) and
``collaboration`` (1 of 2) in UNION-SPEC.md -- a saved search stores
the query's SHA-256 digest and a result count; an annotation stores
the note's SHA-256 digest. The store has no parameter that can
accept query text or note text.
"""

import hashlib
import inspect
import unittest

from lawenf.errors import NotFoundError, ValidationError
from lawenf.store import LawEnfStore
from lawenf_helpers import (DOC_SHA256, MEMBER, NOTE_SHA256, QUERY_SHA256,
                            make_store)

SEARCH_KEYS = {"id", "matter_id", "search_ref", "query_sha256", "result_count",
               "created_by", "created_utc"}
ANNOTATION_KEYS = {"id", "matter_id", "target_kind", "target_id",
                   "annotation_ref", "note_sha256", "created_by", "created_utc"}


class TestSavedSearches(unittest.TestCase):
    """Core 5: only a digest of the query is ever stored."""

    def setUp(self):
        self.store, _audit, self.matter = make_store()
        self.mid = self.matter["id"]

    def test_shape_is_digest_only(self):
        sea = self.store.save_search(self.mid, "SEA-1", QUERY_SHA256, 42, MEMBER)
        self.assertEqual(set(sea.keys()), SEARCH_KEYS)
        self.assertNotIn("query", sea)
        self.assertNotIn("query_text", sea)
        self.assertEqual(sea["result_count"], 42)

    def test_store_signature_has_no_query_text_parameter(self):
        params = list(inspect.signature(LawEnfStore.save_search).parameters)
        self.assertEqual(
            params,
            ["self", "matter_id", "search_ref", "query_sha256",
             "result_count", "actor"])

    def test_digest_and_count_validation(self):
        with self.assertRaises(ValidationError):
            self.store.save_search(self.mid, "SEA-1", "not-a-digest", 1, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.save_search(self.mid, "SEA-1", QUERY_SHA256, -1, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.save_search(self.mid, "SEA-1", QUERY_SHA256, 1.5, MEMBER)

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        self.store.save_search(self.mid, "SEA-1", QUERY_SHA256, 1, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.save_search(self.mid, "SEA-1", QUERY_SHA256, 2, MEMBER)
        sea = self.store.save_search(self.mid, "SEA-2", QUERY_SHA256, 2, MEMBER)
        self.assertEqual(sea["id"], "sea-2")


class TestAnnotations(unittest.TestCase):
    """Core 6: only a digest of the note is ever stored."""

    def setUp(self):
        self.store, _audit, self.matter = make_store()
        self.mid = self.matter["id"]
        self.doc = self.store.register_document(
            self.mid, "DOC-1", DOC_SHA256, 10, MEMBER)
        self.src = self.store.create_source(self.mid, "SRC-1", "case_law", MEMBER)
        self.sea = self.store.save_search(self.mid, "SEA-1", QUERY_SHA256, 7, MEMBER)

    def test_shape_is_digest_only(self):
        ann = self.store.add_annotation(
            self.mid, "document", self.doc["id"], "ANN-1", NOTE_SHA256, MEMBER)
        self.assertEqual(set(ann.keys()), ANNOTATION_KEYS)
        self.assertNotIn("note", ann)
        self.assertNotIn("note_text", ann)

    def test_store_signature_has_no_note_text_parameter(self):
        params = list(inspect.signature(LawEnfStore.add_annotation).parameters)
        self.assertEqual(
            params,
            ["self", "matter_id", "target_kind", "target_id",
             "annotation_ref", "note_sha256", "actor"])

    def test_all_target_kinds(self):
        a1 = self.store.add_annotation(
            self.mid, "document", self.doc["id"], "A-1", NOTE_SHA256, MEMBER)
        a2 = self.store.add_annotation(
            self.mid, "search", self.sea["id"], "A-2", NOTE_SHA256, MEMBER)
        a3 = self.store.add_annotation(
            self.mid, "source", self.src["id"], "A-3", NOTE_SHA256, MEMBER)
        self.assertEqual([a["target_kind"] for a in (a1, a2, a3)],
                         ["document", "search", "source"])

    def test_unknown_target_kind_and_missing_target(self):
        with self.assertRaises(ValidationError):
            self.store.add_annotation(
                self.mid, "person", self.doc["id"], "A-1", NOTE_SHA256, MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.add_annotation(
                self.mid, "document", "doc-999", "A-1", NOTE_SHA256, MEMBER)

    def test_target_in_another_matter_is_not_found(self):
        other = self.store.create_matter("OTHER-REF", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.add_annotation(
                other["id"], "document", self.doc["id"], "A-1", NOTE_SHA256, MEMBER)

    def test_list_filter_by_target(self):
        self.store.add_annotation(
            self.mid, "document", self.doc["id"], "A-1", NOTE_SHA256, MEMBER)
        self.store.add_annotation(
            self.mid, "source", self.src["id"], "A-2", NOTE_SHA256, MEMBER)
        only = self.store.list_annotations(self.mid, MEMBER,
                                           target_id=self.doc["id"])
        self.assertEqual([a["annotation_ref"] for a in only], ["A-1"])
        self.assertEqual(len(self.store.list_annotations(self.mid, MEMBER)), 2)


if __name__ == "__main__":
    unittest.main()
