"""Source registry.

Traces to: Core 2 (Source registry) and claim families
``legal_research`` (2 of 2) and ``practice_guidance`` (1 of 2) in
UNION-SPEC.md -- legal sources as metadata records: opaque refs, a
closed kind set spanning primary law, secondary sources, guidance,
and standard documents. No content is, or can be, stored.
"""

import unittest

from lawenf.errors import NotFoundError, PermissionDenied, ValidationError
from lawenf_helpers import MEMBER, OUTSIDER, make_store

SOURCE_KEYS = {"id", "matter_id", "source_ref", "kind", "jurisdiction_ref",
               "citation_ref", "created_by", "created_utc"}
ALL_KINDS = ("statute", "case_law", "regulation", "secondary",
             "guidance", "standard_document")


class TestSources(unittest.TestCase):
    """Core 2: source records are metadata keyed by opaque refs."""

    def setUp(self):
        self.store, _audit, self.matter = make_store()
        self.mid = self.matter["id"]

    def test_shape_and_defaults(self):
        src = self.store.create_source(self.mid, "SRC-1", "statute", MEMBER)
        self.assertEqual(set(src.keys()), SOURCE_KEYS)
        self.assertEqual(src["id"], "src-1")
        self.assertIsNone(src["jurisdiction_ref"])
        self.assertIsNone(src["citation_ref"])

    def test_every_kind_accepted(self):
        for i, kind in enumerate(ALL_KINDS):
            src = self.store.create_source(
                self.mid, "SRC-%s" % kind, kind, MEMBER,
                jurisdiction_ref="JUR-1", citation_ref="CIT-1")
            self.assertEqual(src["kind"], kind)

    def test_unknown_kind_rejected_and_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.store.create_source(self.mid, "SRC-1", "blog_post", MEMBER)
        src = self.store.create_source(self.mid, "SRC-1", "statute", MEMBER)
        self.assertEqual(src["id"], "src-1")

    def test_duplicate_ref_within_matter_rejected(self):
        self.store.create_source(self.mid, "SRC-1", "statute", MEMBER)
        with self.assertRaises(ValidationError):
            self.store.create_source(self.mid, "SRC-1", "case_law", MEMBER)

    def test_same_ref_allowed_in_another_matter(self):
        other = self.store.create_matter("OTHER-REF", MEMBER)
        self.store.create_source(self.mid, "SRC-1", "statute", MEMBER)
        src = self.store.create_source(other["id"], "SRC-1", "statute", MEMBER)
        self.assertEqual(src["matter_id"], other["id"])

    def test_list_filter_by_kind(self):
        self.store.create_source(self.mid, "S-1", "statute", MEMBER)
        self.store.create_source(self.mid, "S-2", "guidance", MEMBER)
        self.assertEqual(len(self.store.list_sources(self.mid, MEMBER)), 2)
        only = self.store.list_sources(self.mid, MEMBER, kind="guidance")
        self.assertEqual([s["source_ref"] for s in only], ["S-2"])
        with self.assertRaises(ValidationError):
            self.store.list_sources(self.mid, MEMBER, kind="blog_post")

    def test_cross_matter_get_is_not_found(self):
        src = self.store.create_source(self.mid, "SRC-1", "statute", MEMBER)
        other = self.store.create_matter("OTHER-REF", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_source(other["id"], src["id"], MEMBER)

    def test_outsider_cannot_list(self):
        with self.assertRaises(PermissionDenied):
            self.store.list_sources(self.mid, OUTSIDER)


if __name__ == "__main__":
    unittest.main()
