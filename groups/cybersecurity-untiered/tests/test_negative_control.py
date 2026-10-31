"""Negative control: the suite must reject severity-blind scoring.

Traces to: UNION-SPEC "Implementation contract" — tests 'include a
negative control: a mutant scoring function that ignores severity
(every severity weighted 1, so a finding's score depends only on asset
criticality). The traced claim is that severity must move the score: a
critical finding and an informational finding on the same asset cannot
score alike.'

The traced claim: **severity must move a finding's score** (Core
function 4, Risk scoring — the published formula is severity weight ×
asset criticality weight). The mutant below replaces the severity
weights with 1 for every severity, keeping the real criticality
weights and the real band thresholds, so its score depends only on the
asset.

Each canonical case asserts three things: (1) the real score_finding
separates the pair; (2) the mutant collapses the pair to the same
value; and (3) a literal assertRaises(AssertionError) demonstration
that treating the mutant's output as the expected output fails. An
end-to-end arm repeats the separation through the store: two findings
ingested on the same asset with severities critical vs info carry
different scores and bands.
"""

import unittest

from cyber_helpers import ANALYST, fresh_store, make_asset
from cyber_helpers import ingest_sample_finding
from cyber.store import CRITICALITY_WEIGHTS, score_finding


def _band_for(score):
    """The contract band thresholds, shared by real and mutant."""
    if score >= 8:
        return "critical"
    if score >= 5:
        return "high"
    if score >= 2.5:
        return "medium"
    return "low"


def mutant_score_finding(severity, criticality):
    """The defect under control: every severity is weighted 1.

    Mirrors the real function's shape — (score, band) from a severity
    weight times a criticality weight — but the severity weight is 1
    regardless of ``severity``, so the score depends only on the
    asset's criticality.
    """
    score = 1 * CRITICALITY_WEIGHTS[criticality]
    return (float(score), _band_for(score))


class TestNegativeControlMutantScoring(unittest.TestCase):
    """Core: Risk scoring — negative control for severity-blind
    scoring, traced claim: severity must move the score."""

    def test_real_scoring_separates_the_canonical_pair(self):
        """Core: Risk scoring, traced claim: severity must move the
        score. Canonical: score_finding("critical","critical") =
        (10.0, "critical") while score_finding("info","critical") =
        (2.0, "low") — same asset criticality, different severity,
        different score and band."""
        critical = score_finding("critical", "critical")
        info = score_finding("info", "critical")
        self.assertEqual(critical, (10.0, "critical"))
        self.assertEqual(info, (2.0, "low"))
        self.assertNotEqual(critical, info)

    def test_mutant_collapses_the_canonical_pair(self):
        """Core: Risk scoring, traced claim: severity must move the
        score. The severity-blind mutant scores both severities on a
        critical asset at 1 * 2.0 = 2.0 (band low): the separation the
        claim requires is exactly what the mutant destroys."""
        self.assertEqual(mutant_score_finding("critical", "critical"),
                         (2.0, "low"))
        self.assertEqual(mutant_score_finding("info", "critical"),
                         (2.0, "low"))
        self.assertEqual(
            mutant_score_finding("critical", "critical"),
            mutant_score_finding("info", "critical"),
        )

    def test_mutant_output_fails_the_canonical_expectation(self):
        """Core: Risk scoring, traced claim: severity must move the
        score. Treating the mutant's output for the critical case as
        the expected (10.0, "critical") is a test failure — shown via
        a literal assertRaises(AssertionError)."""
        mutant = mutant_score_finding("critical", "critical")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, (10.0, "critical"))
        # And the symmetric arm: the mutant also fails the separation
        # assertion the real function passes.
        with self.assertRaises(AssertionError):
            self.assertNotEqual(
                mutant_score_finding("critical", "critical"),
                mutant_score_finding("info", "critical"),
            )

    def test_mutant_also_collapses_other_criticalities(self):
        """Core: Risk scoring, traced claim: severity must move the
        score. On a medium asset the mutant likewise collapses
        critical and info to one value (1 * 1.0 = 1.0), while the
        real function separates them (5.0/high vs 1.0/low)."""
        self.assertEqual(
            mutant_score_finding("critical", "medium"),
            mutant_score_finding("info", "medium"),
        )
        self.assertEqual(mutant_score_finding("critical", "medium"),
                         (1.0, "low"))
        self.assertEqual(score_finding("critical", "medium"),
                         (5.0, "high"))
        self.assertEqual(score_finding("info", "medium"), (1.0, "low"))
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant_score_finding("critical", "medium"), (5.0, "high")
            )


class TestNegativeControlEndToEnd(unittest.TestCase):
    """Core: Risk scoring / Finding ingestion — the separation holds
    end-to-end in the store, not just in the pure function."""

    def test_ingested_critical_and_info_findings_score_differently(self):
        """Core: Risk scoring, traced claim: severity must move the
        score. End-to-end arm: a critical-severity finding and an
        info-severity finding ingested on the SAME (critical) asset
        carry different scores and bands in the store — (10.0,
        critical) vs (2.0, low) — so a severity-blind store could not
        satisfy this test."""
        store = fresh_store()
        asset = make_asset(store, criticality="critical")
        critical = ingest_sample_finding(
            store, asset["id"], title="critical hole", severity="critical"
        )
        info = ingest_sample_finding(
            store, asset["id"], title="info note", severity="info"
        )
        self.assertEqual((critical["score"], critical["band"]),
                         (10.0, "critical"))
        self.assertEqual((info["score"], info["band"]), (2.0, "low"))
        self.assertNotEqual(critical["score"], info["score"])
        self.assertNotEqual(critical["band"], info["band"])
        # The stored records (not just the ingest return values) differ.
        stored = {
            f["id"]: f for f in store.list_findings(actor=ANALYST)
        }
        self.assertEqual(stored[critical["id"]]["score"], 10.0)
        self.assertEqual(stored[info["id"]]["score"], 2.0)
        # And the mutant's prediction for both (2.0) is wrong for the
        # critical finding, as an expectation.
        with self.assertRaises(AssertionError):
            self.assertEqual(
                stored[critical["id"]]["score"],
                mutant_score_finding("critical", "critical")[0],
            )


if __name__ == "__main__":
    unittest.main()
