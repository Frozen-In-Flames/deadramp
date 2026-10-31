"""Library source registry; saved-search records (digest only).

Traces to: Core functions 5 (Curated legal library, as the registry)
and 6 (Saved-search records) in UNION-SPEC.md. The library is a
platform registry, not agency-scoped: writes require library_write,
reads are open to any actor. A saved search stores the query's
SHA-256 digest and a result count — the store's save_search has no
parameter that could accept query text (privacy discipline, SI-10).
"""

import inspect
import unittest

import legalpol_helpers as H
from legalpol.errors import NotFoundError, PermissionDenied, ValidationError
from legalpol.store import LegalPolStore


class TestLibrarySources(unittest.TestCase):
    """Core 5: library source registry (metadata only, no content)."""

    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()

    def test_register_source_shape(self):
        """Core 5: library source shape is pinned."""
        source = self.store.register_library_source(
            "LIB-REF-001", "statute", H.MEMBER,
            title="Administrative Procedure Act", jurisdiction_ref="JUR-US")
        self.assertEqual(set(source.keys()), {
            "id", "source_ref", "kind", "title", "jurisdiction_ref",
            "created_by", "created_utc"})
        self.assertEqual(source["id"], "lib-1")

    def test_source_kinds(self):
        """Core 5: kinds are statute/regulation/guidance/dataset."""
        for kind in ("statute", "regulation", "guidance", "dataset"):
            source = self.store.register_library_source(
                "LIB-%s" % kind, kind, H.MEMBER)
            self.assertEqual(source["kind"], kind)
        with self.assertRaises(ValidationError):
            self.store.register_library_source("LIB-X", "case_law", H.MEMBER)

    def test_source_ref_unique_across_library(self):
        """Core 5 / SI-10: source_ref is unique across the library."""
        self.store.register_library_source("LIB-1", "statute", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_library_source("LIB-1", "guidance", H.MEMBER)

    def test_library_reads_open_writes_gated(self):
        """Core 5: reads are open to any actor (even a non-member
        outsider and the viewer); writes require library_write, so
        the viewer is denied."""
        source = self.store.register_library_source("LIB-1", "dataset",
                                                    H.MEMBER)
        self.assertEqual(
            self.store.get_library_source(source["id"], H.OUTSIDER)["id"],
            source["id"])
        self.assertEqual(len(self.store.list_library_sources(H.OUTSIDER)), 1)
        with self.assertRaises(PermissionDenied):
            self.store.register_library_source("LIB-2", "statute", H.VIEWER)
        with self.assertRaises(NotFoundError):
            self.store.get_library_source("lib-999", H.MEMBER)

    def test_list_library_sources_kind_filter(self):
        """Core 5: the kind filter is validated and applied."""
        self.store.register_library_source("LIB-1", "statute", H.MEMBER)
        self.store.register_library_source("LIB-2", "guidance", H.MEMBER)
        statutes = self.store.list_library_sources(H.MEMBER, kind="statute")
        self.assertEqual([s["source_ref"] for s in statutes], ["LIB-1"])
        with self.assertRaises(ValidationError):
            self.store.list_library_sources(H.MEMBER, kind="case_law")


class TestSavedSearches(unittest.TestCase):
    """Core 6: saved-search records hold digests, never queries."""

    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)
        self.wid = self.workspace["id"]

    def test_save_search_shape(self):
        """Core 6: saved-search shape is pinned; digest stored as given."""
        search = self.store.save_search(self.aid, "SEA-REF-1", H.QUERY_SHA256,
                                        7, H.MEMBER, workspace_id=self.wid)
        self.assertEqual(set(search.keys()), {
            "id", "agency_id", "workspace_id", "search_ref",
            "query_sha256", "result_count", "created_by", "created_utc"})
        self.assertEqual(search["id"], "sea-1")
        self.assertEqual(search["query_sha256"], H.QUERY_SHA256)

    def test_save_search_signature_has_no_query_text(self):
        """Core 6 (privacy discipline): save_search's parameters are
        exactly the contract's — there is no query-text parameter,
        and a smuggled one raises TypeError."""
        params = list(inspect.signature(
            LegalPolStore.save_search).parameters)
        self.assertEqual(params, ["self", "agency_id", "search_ref",
                                  "query_sha256", "result_count", "actor",
                                  "workspace_id"])
        with self.assertRaises(TypeError):
            self.store.save_search(self.aid, "SEA-X", H.QUERY_SHA256, 1,
                                   H.MEMBER, query_text=H.QUERY_TEXT)

    def test_digest_validation(self):
        """Core 6 / SI-10: the digest must be exactly 64 lowercase
        hex characters — uppercase, short, and non-string values
        are rejected."""
        for bad in ("A" * 64, "a" * 63, "g" * 64, H.QUERY_TEXT, None, 42):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.save_search(self.aid, "SEA-BAD", bad, 1, H.MEMBER)

    def test_result_count_validation(self):
        """Core 6 / SI-10: result_count is an int >= 0; booleans and
        floats are rejected; zero is allowed."""
        for bad in (True, 1.5, -1, "3"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.save_search(self.aid, "SEA-BAD", H.QUERY_SHA256,
                                       bad, H.MEMBER)
        search = self.store.save_search(self.aid, "SEA-ZERO", H.QUERY_SHA256,
                                        0, H.MEMBER)
        self.assertEqual(search["result_count"], 0)

    def test_search_ref_unique_within_agency_and_workspace_link(self):
        """Core 6: search_ref is unique within the agency; a
        workspace_id must name a workspace in this agency."""
        self.store.save_search(self.aid, "SEA-1", H.QUERY_SHA256, 1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.save_search(self.aid, "SEA-1", H.SHA256_A, 2, H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.save_search(self.aid, "SEA-2", H.QUERY_SHA256, 1,
                                   H.MEMBER, workspace_id="wsp-999")

    def test_list_and_get_searches(self):
        """Core 6: listing filters by workspace; cross-agency gets
        are NotFound; outsiders are denied."""
        first = self.store.save_search(self.aid, "SEA-1", H.QUERY_SHA256, 1,
                                       H.MEMBER, workspace_id=self.wid)
        self.store.save_search(self.aid, "SEA-2", H.SHA256_A, 2, H.MEMBER)
        self.assertEqual(
            len(self.store.list_searches(self.aid, H.MEMBER)), 2)
        scoped = self.store.list_searches(self.aid, H.MEMBER,
                                          workspace_id=self.wid)
        self.assertEqual([s["id"] for s in scoped], [first["id"]])
        other = self.store.create_agency("AGY-REF-002", "Second", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_search(other["id"], first["id"], H.ADMIN)
        with self.assertRaises(PermissionDenied):
            self.store.list_searches(self.aid, H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.save_search(self.aid, "SEA-3", H.QUERY_SHA256, 1,
                                   H.VIEWER)


if __name__ == "__main__":
    unittest.main()
