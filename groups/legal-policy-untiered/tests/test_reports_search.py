"""Registry reporting; registry search.

Traces to: Core functions 11 (Registry reporting) and 12 (Registry
search) in UNION-SPEC.md — the agency report is computed on read
(counts, sessions by lifecycle status, sandbox sessions consumed as
a derived count, usage sums by kind; no scores); registry search is
a literal case-insensitive substring match over registry metadata,
scoped to agencies the actor belongs to (or all for a platform
admin), plus the platform library. Digests are never matched.
"""

import unittest

import legalpol_helpers as H
from legalpol.errors import PermissionDenied, ValidationError


class ReportFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)
        self.wid = self.workspace["id"]


class TestAgencyReport(ReportFixture):
    """Core 11: the agency report, computed on read."""

    def test_empty_report_shape(self):
        """Core 11: report shape is pinned; an empty agency reports
        zeros and empty sums."""
        report = self.store.agency_report(self.aid, H.MEMBER)
        self.assertEqual(set(report.keys()), {
            "agency_id", "workspace_count", "session_count",
            "sessions_by_status", "sandbox_sessions",
            "sandbox_sessions_consumed", "execution_count",
            "search_count", "document_count", "export_count",
            "usage_by_kind"})
        self.assertEqual(report["workspace_count"], 1)
        self.assertEqual(report["session_count"], 0)
        self.assertEqual(report["sessions_by_status"],
                         {"active": 0, "closed": 0})
        self.assertEqual(report["usage_by_kind"], {})

    def test_report_counts_and_sums(self):
        """Core 11: counts and usage sums are computed from the
        records; sandbox consumption is the derived count."""
        sandbox = H.make_session(self.store, self.agency, self.workspace,
                                 sandbox=True)
        plain = H.make_session(self.store, self.agency, self.workspace,
                               session_ref="SES-REF-002")
        idle_sandbox = H.make_session(self.store, self.agency, self.workspace,
                                      session_ref="SES-REF-003", sandbox=True)
        self.store.record_execution(self.aid, sandbox["id"], "EXE-1", H.MEMBER)
        self.store.record_execution(self.aid, plain["id"], "EXE-1", H.MEMBER)
        self.store.record_execution(self.aid, plain["id"], "EXE-2", H.MEMBER)
        self.store.close_session(self.aid, idle_sandbox["id"], H.MEMBER)
        self.store.save_search(self.aid, "SEA-1", H.QUERY_SHA256, 4, H.MEMBER)
        self.store.register_document(self.aid, self.wid, "DOC-1",
                                     H.DOC_SHA256, 3, H.MEMBER)
        self.store.record_usage(self.aid, "USE-1", "search", 4, H.MEMBER)
        self.store.record_usage(self.aid, "USE-2", "search", 6, H.MEMBER)
        self.store.record_usage(self.aid, "USE-3", "inference", 10, H.MEMBER)
        self.store.export_usage(self.aid, "EXP-1", H.MEMBER)

        report = self.store.agency_report(self.aid, H.VIEWER)
        self.assertEqual(report["session_count"], 3)
        self.assertEqual(report["sessions_by_status"],
                         {"active": 2, "closed": 1})
        self.assertEqual(report["sandbox_sessions"], 2)
        self.assertEqual(report["sandbox_sessions_consumed"], 1)
        self.assertEqual(report["execution_count"], 3)
        self.assertEqual(report["search_count"], 1)
        self.assertEqual(report["document_count"], 1)
        self.assertEqual(report["export_count"], 1)
        self.assertEqual(report["usage_by_kind"],
                         {"search": 10, "inference": 10})

    def test_report_permissions(self):
        """Core 11 / AC: report_read is held by all three roles for
        members; outsiders are denied by the membership boundary."""
        self.assertEqual(
            self.store.agency_report(self.aid, H.VIEWER)["agency_id"],
            self.aid)
        with self.assertRaises(PermissionDenied):
            self.store.agency_report(self.aid, H.OUTSIDER)


class TestRegistrySearch(ReportFixture):
    """Core 12: registry search over metadata, membership-scoped."""

    def setUp(self):
        super().setUp()
        self.session = H.make_session(self.store, self.agency, self.workspace,
                                      purpose="APA rulemaking review")
        self.store.save_search(self.aid, "SEA-1", H.QUERY_SHA256, 4, H.MEMBER)
        self.store.register_document(self.aid, self.wid, "DOC-ALPHA",
                                     H.DOC_SHA256, 3, H.MEMBER)
        self.store.register_library_source("LIB-ALPHA", "statute", H.MEMBER,
                                           title="Alpha Statute")

    def test_search_result_shape_and_hits(self):
        """Core 12: result shape is pinned; refs, titles, labels, and
        kinds all match, case-insensitively."""
        hits = self.store.search_registry(H.MEMBER, "alpha")
        self.assertEqual(set(hits.keys()), {
            "agencies", "workspaces", "sessions", "library_sources",
            "documents"})
        self.assertEqual([d["doc_ref"] for d in hits["documents"]],
                         ["DOC-ALPHA"])
        self.assertEqual([s["source_ref"] for s in hits["library_sources"]],
                         ["LIB-ALPHA"])
        by_kind = self.store.search_registry(H.MEMBER, "STATUTE")
        self.assertEqual([s["source_ref"] for s in by_kind["library_sources"]],
                         ["LIB-ALPHA"])
        by_ref = self.store.search_registry(H.MEMBER, "wsp-ref")
        self.assertEqual([w["id"] for w in by_ref["workspaces"]], [self.wid])
        by_purpose = self.store.search_registry(H.MEMBER, "rulemaking")
        self.assertEqual([s["id"] for s in by_purpose["sessions"]],
                         [self.session["id"]])
        by_label = self.store.search_registry(H.MEMBER, "legal policy")
        self.assertEqual([a["id"] for a in by_label["agencies"]], [self.aid])

    def test_search_scoped_to_membership(self):
        """Core 12 / AC: an outsider sees no agency-scoped content
        but does see the platform library; an admin sees all."""
        hits = self.store.search_registry(H.OUTSIDER, "alpha")
        self.assertEqual(hits["documents"], [])
        self.assertEqual(hits["agencies"], [])
        self.assertEqual([s["source_ref"] for s in hits["library_sources"]],
                         ["LIB-ALPHA"])
        admin_hits = self.store.search_registry(H.ADMIN, "DOC-ALPHA")
        self.assertEqual(len(admin_hits["documents"]), 1)

    def test_digests_are_never_matched(self):
        """Core 12 (privacy discipline): neither a query digest nor a
        document checksum is searchable text."""
        hits = self.store.search_registry(H.MEMBER, H.QUERY_SHA256[:16])
        self.assertEqual(hits["documents"], [])
        self.assertEqual(hits["sessions"], [])
        hits = self.store.search_registry(H.MEMBER, H.DOC_SHA256[:16])
        self.assertEqual(hits["documents"], [])

    def test_empty_query_rejected(self):
        """Core 12 / SI-10: an empty (or whitespace, or non-string)
        query is a validation error."""
        for bad in ("", "   ", None):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.search_registry(H.MEMBER, bad)


if __name__ == "__main__":
    unittest.main()
