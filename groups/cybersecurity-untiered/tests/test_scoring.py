"""Risk-scoring tests.

Traces to: UNION-SPEC Core function 4 (Risk scoring — a deterministic,
published score per finding: severity weight × asset criticality
weight, with a named band) and Core function 5's register scoring
(likelihood × impact); Implementation contract for ``cyber/store.py``
constants, score_finding, risk_score and risk_band; control family
RA-3.
"""

import unittest

from cyber.store import (
    ASSET_KINDS,
    CRITICALITIES,
    CRITICALITY_WEIGHTS,
    FINDING_STATUSES,
    SEVERITIES,
    SEVERITY_WEIGHTS,
    risk_band,
    risk_score,
    score_finding,
)

# The full published 5x4 table, written out literally: severity weights
# critical=5, high=4, medium=3, low=2, info=1; criticality weights
# critical=2.0, high=1.5, medium=1.0, low=0.5. Bands: critical >= 8,
# high >= 5, medium >= 2.5, else low.
EXPECTED_TABLE = {
    ("critical", "critical"): (10.0, "critical"),
    ("critical", "high"): (7.5, "high"),
    ("critical", "medium"): (5.0, "high"),
    ("critical", "low"): (2.5, "medium"),
    ("high", "critical"): (8.0, "critical"),
    ("high", "high"): (6.0, "high"),
    ("high", "medium"): (4.0, "medium"),
    ("high", "low"): (2.0, "low"),
    ("medium", "critical"): (6.0, "high"),
    ("medium", "high"): (4.5, "medium"),
    ("medium", "medium"): (3.0, "medium"),
    ("medium", "low"): (1.5, "low"),
    ("low", "critical"): (4.0, "medium"),
    ("low", "high"): (3.0, "medium"),
    ("low", "medium"): (2.0, "low"),
    ("low", "low"): (1.0, "low"),
    ("info", "critical"): (2.0, "low"),
    ("info", "high"): (1.5, "low"),
    ("info", "medium"): (1.0, "low"),
    ("info", "low"): (0.5, "low"),
}


class TestPublishedConstants(unittest.TestCase):
    """Core: Risk scoring — the contract's published constant tables."""

    def test_severities_and_weights(self):
        """Core: Risk scoring. Contract: SEVERITIES = (critical, high,
        medium, low, info) with SEVERITY_WEIGHTS 5/4/3/2/1."""
        self.assertEqual(
            tuple(SEVERITIES), ("critical", "high", "medium", "low", "info")
        )
        self.assertEqual(
            dict(SEVERITY_WEIGHTS),
            {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1},
        )

    def test_criticalities_and_weights(self):
        """Core: Risk scoring. Contract: CRITICALITIES = (critical,
        high, medium, low) with CRITICALITY_WEIGHTS 2.0/1.5/1.0/0.5."""
        self.assertEqual(
            tuple(CRITICALITIES), ("critical", "high", "medium", "low")
        )
        self.assertEqual(
            dict(CRITICALITY_WEIGHTS),
            {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5},
        )

    def test_asset_kinds_and_finding_statuses(self):
        """Core: Asset inventory / Finding lifecycle. Contract:
        ASSET_KINDS and FINDING_STATUSES carry exactly the listed
        values."""
        self.assertEqual(
            tuple(ASSET_KINDS),
            ("server", "workstation", "mobile", "network", "cloud",
             "application", "database", "other"),
        )
        self.assertEqual(
            tuple(FINDING_STATUSES),
            ("new", "triaged", "in_progress", "mitigated", "accepted",
             "false_positive", "closed"),
        )


class TestScoreFinding(unittest.TestCase):
    """Core: Risk scoring — score_finding(severity, criticality)."""

    def test_full_five_by_four_table(self):
        """Core: Risk scoring. Contract: score = SEVERITY_WEIGHTS[sev]
        * CRITICALITY_WEIGHTS[crit] with bands critical >= 8, high
        >= 5, medium >= 2.5, else low — all 20 combinations."""
        for (severity, criticality), expected in EXPECTED_TABLE.items():
            with self.subTest(severity=severity, criticality=criticality):
                self.assertEqual(score_finding(severity, criticality), expected)

    def test_canonical_critical_on_critical(self):
        """Core: Risk scoring. Contract spot check:
        ("critical","critical") = (10.0, "critical")."""
        self.assertEqual(
            score_finding("critical", "critical"), (10.0, "critical")
        )

    def test_canonical_info_on_critical(self):
        """Core: Risk scoring. Contract spot check:
        ("info","critical") = (2.0, "low") — severity alone moves this
        pair 8 points below the critical/critical case."""
        self.assertEqual(score_finding("info", "critical"), (2.0, "low"))

    def test_band_edge_eight_is_critical(self):
        """Core: Risk scoring. Band edge: a score of exactly 8.0
        (high severity × critical criticality) is band critical."""
        score, band = score_finding("high", "critical")
        self.assertEqual((score, band), (8.0, "critical"))

    def test_band_edge_five_is_high(self):
        """Core: Risk scoring. Band edge: a score of exactly 5.0
        (critical severity × medium criticality) is band high."""
        score, band = score_finding("critical", "medium")
        self.assertEqual((score, band), (5.0, "high"))

    def test_band_edge_two_point_five_is_medium(self):
        """Core: Risk scoring. Band edge: a score of exactly 2.5
        (critical severity × low criticality) is band medium."""
        score, band = score_finding("critical", "low")
        self.assertEqual((score, band), (2.5, "medium"))

    def test_just_below_each_band_edge_falls_to_the_lower_band(self):
        """Core: Risk scoring. Just under the edges: 7.5 is high (not
        critical), 4.5 is medium (not high), 2.0 is low (not
        medium)."""
        self.assertEqual(score_finding("critical", "high"), (7.5, "high"))
        self.assertEqual(score_finding("medium", "high"), (4.5, "medium"))
        self.assertEqual(score_finding("high", "low"), (2.0, "low"))

    def test_scoring_is_deterministic(self):
        """Core: Risk scoring. Spec claim: 'Same inputs, same score,
        always (no ML, no hidden model).'"""
        for args in EXPECTED_TABLE:
            with self.subTest(args=args):
                self.assertEqual(score_finding(*args), score_finding(*args))


class TestRiskScoreAndBand(unittest.TestCase):
    """Core: Risk register — risk_score / risk_band (RA-3)."""

    def test_risk_score_is_likelihood_times_impact(self):
        """Core: Risk register. Contract: risk_score(likelihood,
        impact) = likelihood * impact (range 1..25)."""
        self.assertEqual(risk_score(1, 1), 1)
        self.assertEqual(risk_score(3, 4), 12)
        self.assertEqual(risk_score(5, 5), 25)
        self.assertEqual(risk_score(2, 5), 10)

    def test_risk_band_edges_fifteen_ten_five(self):
        """Core: Risk register. Contract band edges: risk_band is
        critical for >= 15, high for >= 10, medium for >= 5, else
        low — the exact edge values land in the upper band."""
        self.assertEqual(risk_band(15), "critical")
        self.assertEqual(risk_band(10), "high")
        self.assertEqual(risk_band(5), "medium")

    def test_risk_band_just_below_each_edge(self):
        """Core: Risk register. Just under the edges: 14 is high, 9 is
        medium, 4 is low; the extremes 25 and 1 are critical and
        low."""
        self.assertEqual(risk_band(25), "critical")
        self.assertEqual(risk_band(14), "high")
        self.assertEqual(risk_band(9), "medium")
        self.assertEqual(risk_band(4), "low")
        self.assertEqual(risk_band(1), "low")


if __name__ == "__main__":
    unittest.main()
