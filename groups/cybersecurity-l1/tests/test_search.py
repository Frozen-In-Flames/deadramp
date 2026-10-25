"""Search & filtering tests.

Traces to: UNION-SPEC Core function 7 (Search & filtering — findings
filtered by severity/status/asset/source and substring; assets and
risks by substring; one cross-object search); Implementation contract
for ``cyber/store.py`` search and list_findings; control family CA-7.
"""

import unittest

from cyber_helpers import (
    ANALYST,
    VIEWER,
    create_sample_risk,
    fresh_store,
    ingest_sample_finding,
    make_asset,
)

SEARCH_KEYS = {"findings", "assets", "risks"}


class SearchBase(unittest.TestCase):
    """One store whose asset, finding and risk share the term 'vpn'.

    The asset is named for a VPN gateway, the finding's title mentions
    VPN, and the risk's title mentions VPN; each object also carries a
    unique term so per-field matching can be isolated.
    """

    def setUp(self):
        self.store = fresh_store()
        self.asset = make_asset(
            self.store, name="vpn-gateway-01", owner="netops",
            criticality="critical",
        )
        self.finding = ingest_sample_finding(
            self.store, self.asset["id"], title="VPN tunnel misconfigured",
            severity="critical", source="posture-engine",
            description="split tunnel leaks traffic",
        )
        self.other_finding = ingest_sample_finding(
            self.store, self.asset["id"], title="Stale firmware",
            severity="low", source="scanner",
            description="firmware age exceeds policy",
        )
        self.risk = create_sample_risk(
            self.store, title="VPN concentrator risk",
            description="single point of failure",
            finding_ids=[self.finding["id"]],
        )
        self.other_risk = create_sample_risk(
            self.store, title="Printer risk", description="legacy printer",
            likelihood=1, impact=1,
        )


class TestCrossObjectSearch(SearchBase):
    """Core: Search — one cross-object substring search."""

    def test_search_returns_the_three_result_buckets(self):
        """Core: Search. Contract: search returns {findings, assets,
        risks}."""
        result = self.store.search(actor=ANALYST, q="vpn")
        self.assertEqual(set(result.keys()), SEARCH_KEYS)
        for bucket in result.values():
            self.assertIsInstance(bucket, list)

    def test_search_finds_all_three_object_kinds_on_a_shared_term(self):
        """Core: Search. Contract: one cross-object search — 'vpn'
        matches the asset (name), the finding (title) and the risk
        (title) in a single call."""
        result = self.store.search(actor=ANALYST, q="vpn")
        self.assertEqual([a["id"] for a in result["assets"]],
                         [self.asset["id"]])
        self.assertIn(self.finding["id"],
                      [f["id"] for f in result["findings"]])
        self.assertEqual([r["id"] for r in result["risks"]],
                         [self.risk["id"]])

    def test_search_is_case_insensitive(self):
        """Core: Search. Contract: matching is a 'case-insensitive
        substring' in query and content alike."""
        for query in ("VPN", "Vpn", "vPn"):
            with self.subTest(query=query):
                result = self.store.search(actor=ANALYST, q=query)
                self.assertEqual(len(result["assets"]), 1)
                self.assertEqual(len(result["risks"]), 1)
                self.assertTrue(result["findings"])

    def test_search_matches_finding_description_and_source(self):
        """Core: Search. Contract: findings match over
        title/description/source — 'split tunnel' occurs only in a
        description and 'posture-engine' only in a source."""
        by_desc = self.store.search(actor=ANALYST, q="split tunnel")
        self.assertEqual([f["id"] for f in by_desc["findings"]],
                         [self.finding["id"]])
        by_source = self.store.search(actor=ANALYST, q="POSTURE-ENGINE")
        self.assertEqual([f["id"] for f in by_source["findings"]],
                         [self.finding["id"]])

    def test_search_matches_asset_owner_and_risk_description(self):
        """Core: Search. Contract: assets match over name/owner and
        risks over title/description — 'netops' is owner-only and
        'single point' is risk-description-only."""
        by_owner = self.store.search(actor=ANALYST, q="netops")
        self.assertEqual([a["id"] for a in by_owner["assets"]],
                         [self.asset["id"]])
        self.assertEqual(by_owner["findings"], [])
        by_desc = self.store.search(actor=ANALYST, q="single point")
        self.assertEqual([r["id"] for r in by_desc["risks"]],
                         [self.risk["id"]])

    def test_search_with_no_match_returns_empty_buckets(self):
        """Core: Search. A query matching nothing returns three empty
        lists, not an error."""
        result = self.store.search(actor=ANALYST, q="no-such-term-xyz")
        self.assertEqual(
            result, {"findings": [], "assets": [], "risks": []}
        )

    def test_search_does_not_return_non_matching_objects(self):
        """Core: Search. Scoping: 'firmware' matches only the second
        finding — the VPN finding, the asset and both risks stay out
        of the results."""
        result = self.store.search(actor=ANALYST, q="firmware")
        self.assertEqual([f["id"] for f in result["findings"]],
                         [self.other_finding["id"]])
        self.assertEqual(result["assets"], [])
        self.assertEqual(result["risks"], [])

    def test_viewer_may_search(self):
        """Core: Search + Access control. search takes action read,
        which viewer holds."""
        result = self.store.search(actor=VIEWER, q="vpn")
        self.assertEqual(len(result["assets"]), 1)


class TestListFindingsFilters(unittest.TestCase):
    """Core: Search & filtering — list_findings filters and sort."""

    def setUp(self):
        self.store = fresh_store()
        self.critical_asset = make_asset(
            self.store, name="crit-asset", criticality="critical"
        )
        self.low_asset = make_asset(
            self.store, name="low-asset", criticality="low"
        )
        # Scores: a = 5*2.0=10, b = 4*2.0=8, c = 5*0.5=2.5, d = 1*2.0=2.
        self.a = ingest_sample_finding(
            self.store, self.critical_asset["id"], title="Alpha hole",
            severity="critical", source="scanner",
        )
        self.b = ingest_sample_finding(
            self.store, self.critical_asset["id"], title="Beta hole",
            severity="high", source="posture",
        )
        self.c = ingest_sample_finding(
            self.store, self.low_asset["id"], title="Gamma hole",
            severity="critical", source="scanner",
        )
        self.d = ingest_sample_finding(
            self.store, self.critical_asset["id"], title="Delta note",
            severity="info", source="scanner",
            description="alpha mention in text",
        )
        self.store.transition_finding(self.b["id"], "triaged",
                                      actor=ANALYST)

    def test_list_findings_sorts_by_score_desc_then_id_asc(self):
        """Core: Search & filtering. Contract: list_findings is
        'sorted by score descending, then id ascending'."""
        listed = self.store.list_findings(actor=ANALYST)
        self.assertEqual(
            [f["id"] for f in listed],
            [self.a["id"], self.b["id"], self.c["id"], self.d["id"]],
        )
        self.assertEqual(
            [f["score"] for f in listed], [10.0, 8.0, 2.5, 2.0]
        )

    def test_list_findings_id_asc_breaks_score_ties(self):
        """Core: Search & filtering. Contract sort tie-break: equal
        scores list in id ascending order."""
        first = ingest_sample_finding(
            self.store, self.low_asset["id"], title="tie-1",
            severity="medium", source="scanner",
        )
        second = ingest_sample_finding(
            self.store, self.low_asset["id"], title="tie-2",
            severity="medium", source="scanner",
        )
        self.assertEqual(first["score"], second["score"])
        listed = self.store.list_findings(actor=ANALYST, source="scanner")
        tie_ids = [f["id"] for f in listed
                   if f["id"] in (first["id"], second["id"])]
        self.assertEqual(tie_ids, [first["id"], second["id"]])

    def test_filter_by_severity(self):
        """Core: Search & filtering. Contract: list_findings filters
        by severity — critical returns the two critical findings
        across both assets, in score order."""
        listed = self.store.list_findings(actor=ANALYST,
                                          severity="critical")
        self.assertEqual([f["id"] for f in listed],
                         [self.a["id"], self.c["id"]])
        self.assertEqual(
            self.store.list_findings(actor=ANALYST, severity="medium"),
            [],
        )

    def test_filter_by_status(self):
        """Core: Search & filtering. Contract: list_findings filters
        by status."""
        listed = self.store.list_findings(actor=ANALYST, status="triaged")
        self.assertEqual([f["id"] for f in listed], [self.b["id"]])
        listed = self.store.list_findings(actor=ANALYST, status="new")
        self.assertEqual(len(listed), 3)

    def test_filter_by_asset_id_scopes_to_one_asset(self):
        """Core: Search & filtering. Contract: list_findings filters
        by asset_id — results are scoped to exactly that asset."""
        listed = self.store.list_findings(
            actor=ANALYST, asset_id=self.low_asset["id"]
        )
        self.assertEqual([f["id"] for f in listed], [self.c["id"]])
        for finding in listed:
            self.assertEqual(finding["asset_id"], self.low_asset["id"])

    def test_filter_by_source(self):
        """Core: Search & filtering. Contract: list_findings filters
        by source."""
        listed = self.store.list_findings(actor=ANALYST, source="posture")
        self.assertEqual([f["id"] for f in listed], [self.b["id"]])

    def test_filter_by_q_over_title_description_and_source(self):
        """Core: Search & filtering. Contract: list_findings q is 'a
        case-insensitive substring over title, description, and
        source' — 'alpha' hits a title and a description."""
        listed = self.store.list_findings(actor=ANALYST, q="ALPHA")
        self.assertEqual({f["id"] for f in listed},
                         {self.a["id"], self.d["id"]})
        by_source = self.store.list_findings(actor=ANALYST, q="posture")
        self.assertEqual([f["id"] for f in by_source], [self.b["id"]])

    def test_filters_combine_as_intersection(self):
        """Core: Search & filtering. Contract: list_findings returns
        findings 'matching all given filters' — severity critical AND
        asset low AND source scanner leaves only finding c."""
        listed = self.store.list_findings(
            actor=ANALYST, severity="critical",
            asset_id=self.low_asset["id"], source="scanner",
        )
        self.assertEqual([f["id"] for f in listed], [self.c["id"]])
        self.assertEqual(
            self.store.list_findings(
                actor=ANALYST, severity="critical", status="triaged"
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
