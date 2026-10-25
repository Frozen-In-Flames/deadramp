"""Posture-reporting tests.

Traces to: UNION-SPEC Core function 8 (Posture reporting — a summary:
assets by criticality, findings by severity and status, the top open
findings by score, risks by band and status, control coverage);
Implementation contract for ``cyber/store.py`` posture_summary;
control families CA-7 and AU-6.
"""

import unittest

from cyber_helpers import (
    ANALYST,
    VIEWER,
    create_sample_risk,
    fresh_store,
    ingest_sample_finding,
    make_asset,
    make_store,
)


class TestPostureShapeOnEmptyStore(unittest.TestCase):
    """Core: Posture reporting — summary shape with all-zero buckets."""

    def test_summary_shape_with_all_zero_buckets(self):
        """Core: Posture reporting. Contract: posture_summary returns
        {assets: {total, by_criticality{4}}, findings: {total,
        by_severity{5}, by_status{7}, open, top_open}, risks: {total,
        by_status{4}, by_band{4}}, controls: {total: 34, assessed,
        implemented, coverage_pct}} — on an empty store every by_*
        bucket is present with zeros."""
        store = fresh_store()
        summary = store.posture_summary(actor=ANALYST)
        self.assertEqual(
            set(summary.keys()), {"assets", "findings", "risks", "controls"}
        )
        self.assertEqual(
            summary["assets"],
            {"total": 0,
             "by_criticality": {"critical": 0, "high": 0, "medium": 0,
                                "low": 0}},
        )
        findings = summary["findings"]
        self.assertEqual(findings["total"], 0)
        self.assertEqual(
            findings["by_severity"],
            {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        self.assertEqual(
            findings["by_status"],
            {"new": 0, "triaged": 0, "in_progress": 0, "mitigated": 0,
             "accepted": 0, "false_positive": 0, "closed": 0},
        )
        self.assertEqual(findings["open"], 0)
        self.assertEqual(findings["top_open"], [])
        risks = summary["risks"]
        self.assertEqual(risks["total"], 0)
        self.assertEqual(
            risks["by_status"],
            {"open": 0, "monitoring": 0, "treated": 0, "closed": 0},
        )
        self.assertEqual(
            risks["by_band"],
            {"critical": 0, "high": 0, "medium": 0, "low": 0},
        )
        self.assertEqual(
            summary["controls"],
            {"total": 34, "assessed": 0, "implemented": 0,
             "coverage_pct": 0.0},
        )

    def test_summary_reflects_the_fixture_counts(self):
        """Core: Posture reporting. With the canonical fixture (one
        high-criticality asset, one high-severity new finding) the
        buckets count exactly those objects."""
        store, asset, finding = make_store()
        summary = store.posture_summary(actor=VIEWER)
        self.assertEqual(summary["assets"]["total"], 1)
        self.assertEqual(
            summary["assets"]["by_criticality"],
            {"critical": 0, "high": 1, "medium": 0, "low": 0},
        )
        self.assertEqual(summary["findings"]["total"], 1)
        self.assertEqual(summary["findings"]["by_severity"]["high"], 1)
        self.assertEqual(summary["findings"]["by_status"]["new"], 1)
        self.assertEqual(summary["findings"]["open"], 1)
        self.assertEqual(
            [f["id"] for f in summary["findings"]["top_open"]],
            [finding["id"]],
        )


class TestPostureOpenAndTopOpen(unittest.TestCase):
    """Core: Posture reporting — open counting and the top_open list."""

    def setUp(self):
        self.store = fresh_store()
        self.asset = make_asset(self.store, criticality="critical")

    def _drive(self, finding, *steps):
        """Transition a finding through the given legal steps."""
        for step in steps:
            finding = self.store.transition_finding(
                finding["id"], step, actor=ANALYST
            )
        return finding

    def test_open_excludes_closed_and_false_positive(self):
        """Core: Posture reporting. Contract: 'open counts findings
        whose status is not closed or false_positive' — a closed
        finding and a false-positive finding drop out while new,
        triaged, mitigated and accepted findings still count."""
        new_f = ingest_sample_finding(self.store, self.asset["id"],
                                      title="stays new", severity="low")
        triaged_f = ingest_sample_finding(self.store, self.asset["id"],
                                          title="triaged", severity="low")
        self._drive(triaged_f, "triaged")
        mitigated_f = ingest_sample_finding(self.store, self.asset["id"],
                                            title="mitigated",
                                            severity="low")
        self._drive(mitigated_f, "triaged", "in_progress", "mitigated")
        accepted_f = ingest_sample_finding(self.store, self.asset["id"],
                                           title="accepted", severity="low")
        self._drive(accepted_f, "triaged", "accepted")
        fp_f = ingest_sample_finding(self.store, self.asset["id"],
                                     title="false positive",
                                     severity="critical")
        self._drive(fp_f, "false_positive")
        closed_f = ingest_sample_finding(self.store, self.asset["id"],
                                         title="closed",
                                         severity="critical")
        self._drive(closed_f, "false_positive", "closed")

        summary = self.store.posture_summary(actor=ANALYST)
        self.assertEqual(summary["findings"]["total"], 6)
        self.assertEqual(summary["findings"]["open"], 4)
        top_ids = [f["id"] for f in summary["findings"]["top_open"]]
        self.assertNotIn(fp_f["id"], top_ids)
        self.assertNotIn(closed_f["id"], top_ids)
        self.assertIn(new_f["id"], top_ids)

    def test_top_open_is_limited_to_five_and_sorted(self):
        """Core: Posture reporting. Contract: top_open is 'up to 5
        open finding dicts sorted by score descending then id
        ascending' — seven open findings yield exactly the five
        highest scores in order."""
        severities = ["info", "low", "medium", "high", "critical",
                      "high", "medium"]
        created = [
            ingest_sample_finding(self.store, self.asset["id"],
                                  title="f-%s" % sev, severity=sev)
            for sev in severities
        ]
        # On a critical asset the scores are 2, 4, 6, 8, 10, 8, 6.
        summary = self.store.posture_summary(actor=ANALYST)
        top = summary["findings"]["top_open"]
        self.assertEqual(len(top), 5)
        self.assertEqual(
            [f["score"] for f in top], [10.0, 8.0, 8.0, 6.0, 6.0]
        )
        # The two 8.0s (and the two 6.0s) are in id-ascending order.
        ids_in_top = [f["id"] for f in top]
        self.assertEqual(ids_in_top[0], created[4]["id"])
        self.assertEqual(ids_in_top[1:3],
                         sorted([created[3]["id"], created[5]["id"]]))
        self.assertEqual(ids_in_top[3:5],
                         sorted([created[2]["id"], created[6]["id"]]))

    def test_by_severity_and_by_status_count_every_bucket(self):
        """Core: Posture reporting. Contract: by_severity carries all
        five severities and by_status all seven statuses, each
        counting the findings in it."""
        ingest_sample_finding(self.store, self.asset["id"],
                              title="crit", severity="critical")
        low = ingest_sample_finding(self.store, self.asset["id"],
                                    title="low", severity="low")
        self._drive(low, "false_positive")
        summary = self.store.posture_summary(actor=ANALYST)
        self.assertEqual(summary["findings"]["by_severity"]["critical"], 1)
        self.assertEqual(summary["findings"]["by_severity"]["low"], 1)
        self.assertEqual(summary["findings"]["by_severity"]["high"], 0)
        self.assertEqual(summary["findings"]["by_status"]["new"], 1)
        self.assertEqual(
            summary["findings"]["by_status"]["false_positive"], 1
        )
        self.assertEqual(summary["findings"]["by_status"]["closed"], 0)


class TestPostureRisksAndAssets(unittest.TestCase):
    """Core: Posture reporting — risk and asset bucket counting."""

    def test_risks_by_band_and_by_status(self):
        """Core: Posture reporting. Contract: risks summary carries
        by_status over all four statuses and by_band over critical/
        high/medium/low, counting the register."""
        store = fresh_store()
        crit = create_sample_risk(store, title="crit", likelihood=5,
                                  impact=5)   # 25 critical
        create_sample_risk(store, title="high", likelihood=2,
                           impact=5)          # 10 high
        create_sample_risk(store, title="med", likelihood=1,
                           impact=5)          # 5 medium
        create_sample_risk(store, title="low", likelihood=1,
                           impact=1)          # 1 low
        store.transition_risk(crit["id"], "monitoring", actor=ANALYST)
        risks = store.posture_summary(actor=ANALYST)["risks"]
        self.assertEqual(risks["total"], 4)
        self.assertEqual(
            risks["by_band"],
            {"critical": 1, "high": 1, "medium": 1, "low": 1},
        )
        self.assertEqual(
            risks["by_status"],
            {"open": 3, "monitoring": 1, "treated": 0, "closed": 0},
        )

    def test_assets_by_criticality(self):
        """Core: Posture reporting. Contract: assets summary counts
        by_criticality over critical/high/medium/low."""
        store = fresh_store()
        make_asset(store, name="a", criticality="critical")
        make_asset(store, name="b", criticality="critical")
        make_asset(store, name="c", criticality="low")
        assets = store.posture_summary(actor=ANALYST)["assets"]
        self.assertEqual(assets["total"], 3)
        self.assertEqual(
            assets["by_criticality"],
            {"critical": 2, "high": 0, "medium": 0, "low": 1},
        )


if __name__ == "__main__":
    unittest.main()
