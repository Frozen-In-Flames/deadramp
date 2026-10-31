"""Posture reporting tests.

Traces to: Core function 7 (posture reporting — computed on read from
records: counts by framework/system/status, open findings, overdue
findings, evidence counts, indicator results summary; counts and
summaries ONLY, no computed risk score or aggregate rating anywhere);
control families CA-7 / AU-6.
"""

import unittest

from grc_helpers import ADMIN, MEMBER, VIEWER, SYSTEM_REF, make_finding, make_store
from grc.store import FINDING_STATUSES


def _all_keys(obj):
    """Every dict key anywhere inside a nested structure."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class TestPostureEmpty(unittest.TestCase):
    """Core 7: posture of a fresh (seed-only) store."""

    def test_empty_store_shape_with_zeros(self):
        """Core 7. A fresh store reports the seed framework and its
        21 controls, zero everywhere else, and every finding/auth
        status bucket present with zero counts."""
        from grc_helpers import fresh_store

        store = fresh_store()
        summary = store.posture_summary(actor=VIEWER, as_of="2026-10-25")
        self.assertEqual(summary["as_of"], "2026-10-25")
        self.assertEqual(summary["frameworks"]["total"], 1)
        self.assertEqual(summary["frameworks"]["controls_total"], 21)
        self.assertEqual(
            summary["frameworks"]["controls_by_framework"], {"NIST-SP-800-53": 21}
        )
        self.assertEqual(summary["systems"]["total"], 0)
        self.assertEqual(summary["indicators"]["total"], 0)
        self.assertEqual(summary["indicators"]["results_by_status"], {})
        self.assertEqual(summary["evidence"]["total"], 0)
        self.assertEqual(summary["findings"]["total"], 0)
        self.assertEqual(
            summary["findings"]["by_status"], {name: 0 for name in FINDING_STATUSES}
        )
        self.assertEqual(summary["findings"]["open"], 0)
        self.assertEqual(summary["findings"]["overdue"], 0)
        self.assertEqual(summary["assessments"]["total"], 0)
        self.assertEqual(summary["authorizations"]["by_status"]["authorized"], 0)


class TestPostureCounts(unittest.TestCase):
    """Core 7: posture counts computed on read from the records."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()
        # Indicator results: two recorded statuses.
        self.store.record_indicator_result(
            "KSI-1", SYSTEM_REF, "reported-pass", actor=MEMBER
        )
        self.store.record_indicator_result(
            "KSI-1", SYSTEM_REF, "reported-pass", actor=MEMBER
        )
        self.store.record_indicator_result(
            "KSI-1", SYSTEM_REF, "reported-fail", actor=MEMBER
        )
        # Evidence: one unvalidated, one reviewed.
        self.store.create_evidence("a", "alpha", ["AC-2"], [SYSTEM_REF], actor=MEMBER)
        reviewed = self.store.create_evidence(
            "b", "beta", ["AC-2"], [SYSTEM_REF], actor=MEMBER
        )
        self.store.review_evidence(reviewed["id"], "accepted", actor=ADMIN)
        # Findings: one open past due at as_of, one remediated past
        # due, one open not yet due.
        make_finding(self.store, due_date="2026-06-30")
        done = make_finding(self.store, due_date="2026-06-30")
        self.store.transition_finding(done["id"], "in_progress", actor=MEMBER)
        self.store.transition_finding(done["id"], "remediated", actor=MEMBER)
        make_finding(self.store, due_date="2027-06-30", severity="Sev-2 (vendor)")
        # One assessment, one authorization in progress.
        self.store.create_assessment(
            SYSTEM_REF, "NIST-SP-800-53", "full", "assessor-7", "2026-09-15",
            "Satisfied (as reported)", actor=MEMBER,
        )
        auth = self.store.create_authorization(SYSTEM_REF, "NIST-SP-800-53", actor=ADMIN)
        self.store.transition_authorization(auth["id"], "in_progress", actor=ADMIN)

    def test_counts_by_framework_system_and_status(self):
        """Core 7. Counts by framework (controls per framework),
        by system (findings per system), and by status come straight
        from the records."""
        summary = self.store.posture_summary(actor=ADMIN, as_of="2026-10-25")
        self.assertEqual(summary["systems"]["total"], 1)
        self.assertEqual(summary["findings"]["total"], 3)
        self.assertEqual(summary["findings"]["by_system"], {SYSTEM_REF: 3})
        self.assertEqual(summary["findings"]["by_status"]["open"], 2)
        self.assertEqual(summary["findings"]["by_status"]["remediated"], 1)
        self.assertEqual(summary["assessments"]["total"], 1)
        self.assertEqual(
            summary["assessments"]["by_result"], {"Satisfied (as reported)": 1}
        )
        self.assertEqual(summary["authorizations"]["by_status"]["in_progress"], 1)

    def test_open_and_overdue_counts_use_the_derivation(self):
        """Core 7. "open" counts open + in_progress + accepted_risk;
        "overdue" is the read-time derivation at the summary's as_of:
        exactly the one past-due open finding here. Moving as_of
        before every due date yields zero overdue."""
        summary = self.store.posture_summary(actor=ADMIN, as_of="2026-10-25")
        self.assertEqual(summary["findings"]["open"], 2)
        self.assertEqual(summary["findings"]["overdue"], 1)
        early = self.store.posture_summary(actor=ADMIN, as_of="2026-01-01")
        self.assertEqual(early["findings"]["overdue"], 0)

    def test_severity_counts_are_verbatim_buckets(self):
        """Core 7. Findings by severity bucket the recorded strings
        verbatim — the vendor-worded severity is its own bucket."""
        summary = self.store.posture_summary(actor=ADMIN, as_of="2026-10-25")
        self.assertEqual(
            summary["findings"]["by_severity"], {"high": 2, "Sev-2 (vendor)": 1}
        )

    def test_indicator_and_evidence_summaries(self):
        """Core 7. Indicator results are summarized by their recorded
        statuses; evidence by its recorded validation statuses."""
        summary = self.store.posture_summary(actor=ADMIN, as_of="2026-10-25")
        self.assertEqual(summary["indicators"]["total"], 1)
        self.assertEqual(summary["indicators"]["results_total"], 3)
        self.assertEqual(
            summary["indicators"]["results_by_status"],
            {"reported-pass": 2, "reported-fail": 1},
        )
        self.assertEqual(summary["evidence"]["total"], 2)
        self.assertEqual(
            summary["evidence"]["by_validation_status"],
            {"unvalidated": 1, "accepted": 1},
        )

    def test_no_score_or_rating_anywhere_in_posture(self):
        """Core 7. The posture summary contains no key mentioning a
        score, rating, grade, or percentage anywhere in its nested
        structure — counts and summaries only."""
        summary = self.store.posture_summary(actor=ADMIN, as_of="2026-10-25")
        for key in _all_keys(summary):
            lowered = key.lower()
            self.assertNotIn("score", lowered)
            self.assertNotIn("rating", lowered)
            self.assertNotIn("grade", lowered)
            self.assertNotIn("pct", lowered)
            self.assertNotIn("percent", lowered)

    def test_posture_does_not_audit(self):
        """Core 7 + Core 10 Audit. Reading the posture summary writes
        no audit entry."""
        from grc.audit import AuditLog
        from grc_helpers import fresh_store

        audit = AuditLog()
        store = fresh_store(audit=audit)
        store.posture_summary(actor=ADMIN, as_of="2026-10-25")
        self.assertEqual(audit.entries(), [])


if __name__ == "__main__":
    unittest.main()
