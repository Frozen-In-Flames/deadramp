"""Registry reporting & registry search.

Traces to: Core 8 (Registry reporting) and Core 9 (Registry search)
in UNION-SPEC.md -- reports are counts computed on read from the
records (treatment keys are the verbatim recorded strings); registry
search is a literal substring match over registry metadata only,
scoped to matters the actor may see. Digests are never searchable.
"""

import unittest

from lawenf.errors import ValidationError
from lawenf_helpers import (DOC_SHA256, MEMBER, NOTE_SHA256, OUTSIDER,
                            QUERY_SHA256, VIEWER, make_store)


def _seeded():
    store, _audit, matter = make_store()
    mid = matter["id"]
    store.create_source(mid, "SRC-STATUTE", "statute", MEMBER)
    store.create_source(mid, "SRC-GUIDE", "guidance", MEMBER)
    doc = store.register_document(mid, "DOC-BRIEF", DOC_SHA256, 10, MEMBER)
    store.begin_review(mid, doc["id"], MEMBER)
    store.save_search(mid, "SEA-IMMUNITY", QUERY_SHA256, 12, MEMBER)
    store.add_annotation(mid, "document", doc["id"], "ANN-1", NOTE_SHA256, MEMBER)
    store.record_citation_check(mid, "CIT-1", "followed", MEMBER)
    store.record_citation_check(mid, "CIT-2", "Followed", MEMBER)
    store.record_citation_check(mid, "CIT-3", "followed", MEMBER)
    return store, matter


class TestReports(unittest.TestCase):
    """Core 8: counts on read; treatment keys are verbatim."""

    def test_report_counts(self):
        store, matter = _seeded()
        report = store.matter_report(matter["id"], VIEWER)
        self.assertEqual(report["status"], "open")
        self.assertEqual(report["member_count"], 2)
        self.assertEqual(report["sources_by_kind"], {"statute": 1, "guidance": 1})
        self.assertEqual(report["documents_by_status"], {"in_review": 1})
        self.assertEqual(report["search_count"], 1)
        self.assertEqual(report["annotation_count"], 1)
        self.assertEqual(report["citation_check_count"], 3)
        # "followed" and "Followed" are distinct verbatim keys: the
        # build never normalizes a caller's recorded treatment.
        self.assertEqual(report["citation_checks_by_treatment"],
                         {"followed": 2, "Followed": 1})

    def test_empty_matter_report(self):
        store, _audit, matter = make_store()
        report = store.matter_report(matter["id"], MEMBER)
        self.assertEqual(report["sources_by_kind"], {})
        self.assertEqual(report["citation_check_count"], 0)


class TestRegistrySearch(unittest.TestCase):
    """Core 9: literal metadata search, membership-scoped."""

    def test_matches_refs_kinds_and_treatments(self):
        store, matter = _seeded()
        hits = store.search_registry(MEMBER, "src-")
        self.assertEqual({s["source_ref"] for s in hits["sources"]},
                         {"SRC-STATUTE", "SRC-GUIDE"})
        hits = store.search_registry(MEMBER, "guidance")
        self.assertEqual([s["source_ref"] for s in hits["sources"]], ["SRC-GUIDE"])
        hits = store.search_registry(MEMBER, "followed")
        self.assertEqual(len(hits["citation_checks"]), 3)
        hits = store.search_registry(MEMBER, "immunity")
        self.assertEqual([s["search_ref"] for s in hits["searches"]],
                         ["SEA-IMMUNITY"])

    def test_search_is_literal_not_regex(self):
        store, matter = _seeded()
        hits = store.search_registry(MEMBER, "SRC.*")
        self.assertEqual(hits["sources"], [])

    def test_digests_are_not_searchable(self):
        store, matter = _seeded()
        hits = store.search_registry(MEMBER, QUERY_SHA256[:16])
        self.assertEqual(hits["searches"], [])
        hits = store.search_registry(MEMBER, NOTE_SHA256[:16])
        self.assertEqual(hits["matters"], [])
        self.assertEqual(hits["sources"], [])
        self.assertEqual(hits["documents"], [])

    def test_outsider_sees_nothing(self):
        store, matter = _seeded()
        hits = store.search_registry(OUTSIDER, "SRC")
        for key in ("matters", "sources", "documents", "searches",
                    "citation_checks"):
            self.assertEqual(hits[key], [])

    def test_empty_query_rejected(self):
        store, _matter = _seeded()
        with self.assertRaises(ValidationError):
            store.search_registry(MEMBER, "   ")


if __name__ == "__main__":
    unittest.main()
