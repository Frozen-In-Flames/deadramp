"""Control mapping & assessment tests.

Traces to: UNION-SPEC Core function 6 (Control mapping & assessment —
a built-in catalog of 34 NIST SP 800-53 Rev. 5 controls; findings link
to controls at ingest, and each control carries an assessment status
and evidence note); Implementation contract for ``cyber/catalog.py``
and ``cyber/store.py`` list_controls / assess_control; control
families CA-2, CA-5, CA-7.
"""

import unittest
from datetime import datetime

from cyber_helpers import (
    ANALYST,
    VIEWER,
    fresh_store,
    ingest_sample_finding,
    make_asset,
    make_store,
)
from cyber.catalog import CONTROL_CATALOG, CONTROL_IDS, control_by_id
from cyber.errors import NotFoundError, PermissionDenied, ValidationError
from cyber.store import ASSESSMENT_STATUSES

CONTROL_KEYS = {
    "id", "family", "title", "status", "evidence", "assessed_by",
    "assessed_utc", "finding_count",
}

# A sample of catalog entries pinned literally from the contract.
PINNED_CONTROLS = {
    "AC-2": "Account Management",
    "AC-3": "Access Enforcement",
    "AU-9": "Protection of Audit Information",
    "CA-7": "Continuous Monitoring",
    "CM-8": "System Component Inventory",
    "RA-5": "Vulnerability Monitoring and Scanning",
    "SC-8": "Transmission Confidentiality and Integrity",
    "SI-10": "Information Input Validation",
    "SI-16": "Memory Protection",
}


def _parse_ts(ts):
    """Parse a contract UTC ISO-8601 timestamp (must not raise)."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _controls_by_id(store, actor=ANALYST):
    """list_controls indexed by control id."""
    return {c["id"]: c for c in store.list_controls(actor=actor)}


class TestCatalog(unittest.TestCase):
    """Core: Control mapping — the built-in 34-control catalog."""

    def test_catalog_has_exactly_34_controls(self):
        """Core: Control mapping. Contract: CONTROL_CATALOG is 'a list
        of 34 dicts' covering the named NIST SP 800-53 Rev. 5
        controls."""
        self.assertEqual(len(CONTROL_CATALOG), 34)

    def test_catalog_entries_have_id_family_title_and_unique_ids(self):
        """Core: Control mapping. Contract: each catalog dict is {id,
        family, title} and 'family is the id's alphabetic prefix'."""
        ids = [c["id"] for c in CONTROL_CATALOG]
        self.assertEqual(len(set(ids)), 34)
        for control in CONTROL_CATALOG:
            with self.subTest(control=control["id"]):
                self.assertEqual(
                    set(control.keys()), {"id", "family", "title"}
                )
                prefix = control["id"].split("-")[0]
                self.assertEqual(control["family"], prefix)
                self.assertTrue(control["title"])

    def test_catalog_pinned_titles(self):
        """Core: Control mapping. Contract: the catalog covers the
        named controls with their NIST titles (a pinned sample,
        including AC-2, CM-8, RA-5 and SI-10)."""
        by_id = {c["id"]: c for c in CONTROL_CATALOG}
        for control_id, title in PINNED_CONTROLS.items():
            with self.subTest(control=control_id):
                self.assertIn(control_id, by_id)
                self.assertEqual(by_id[control_id]["title"], title)

    def test_control_ids_set_matches_the_catalog(self):
        """Core: Control mapping. Contract: CONTROL_IDS is 'a set/
        frozenset of the ids' — exactly the 34 catalog ids."""
        self.assertEqual(
            set(CONTROL_IDS), {c["id"] for c in CONTROL_CATALOG}
        )
        self.assertEqual(len(set(CONTROL_IDS)), 34)

    def test_control_by_id_known_and_unknown(self):
        """Core: Control mapping. Contract: control_by_id 'returning
        the catalog dict or None'."""
        found = control_by_id("RA-5")
        self.assertIsNotNone(found)
        self.assertEqual(found["title"],
                         "Vulnerability Monitoring and Scanning")
        self.assertIsNone(control_by_id("XX-99"))
        self.assertIsNone(control_by_id(""))

    def test_assessment_statuses_constant(self):
        """Core: Control mapping. Contract: ASSESSMENT_STATUSES =
        (not_assessed, implemented, partially_implemented,
        not_implemented)."""
        self.assertEqual(
            tuple(ASSESSMENT_STATUSES),
            ("not_assessed", "implemented", "partially_implemented",
             "not_implemented"),
        )


class TestListControls(unittest.TestCase):
    """Core: Control mapping — list_controls initial state and counts."""

    def test_list_controls_initial_state(self):
        """Core: Control mapping. Contract: list_controls returns one
        dict per catalog control, in catalog order, where 'status
        starts as "not_assessed", evidence starts as "",
        assessed_by/assessed_utc start as None'."""
        store, asset, finding = make_store()
        controls = store.list_controls(actor=VIEWER)
        self.assertEqual(len(controls), 34)
        self.assertEqual(
            [c["id"] for c in controls],
            [c["id"] for c in CONTROL_CATALOG],
        )
        for control in controls:
            with self.subTest(control=control["id"]):
                self.assertEqual(set(control.keys()), CONTROL_KEYS)
                self.assertEqual(control["status"], "not_assessed")
                self.assertEqual(control["evidence"], "")
                self.assertIsNone(control["assessed_by"])
                self.assertIsNone(control["assessed_utc"])
                self.assertEqual(
                    control["title"],
                    control_by_id(control["id"])["title"],
                )

    def test_finding_count_reflects_linked_findings(self):
        """Core: Control mapping. Contract: finding_count is 'the
        number of findings whose control_ids include the control' —
        two findings link AC-2 (one also RA-5), so AC-2 counts 2,
        RA-5 counts 1 and an unlinked control counts 0."""
        store = fresh_store()
        asset = make_asset(store)
        ingest_sample_finding(store, asset["id"],
                              control_ids=["AC-2", "RA-5"])
        ingest_sample_finding(store, asset["id"], title="second",
                              control_ids=["AC-2"])
        ingest_sample_finding(store, asset["id"], title="unlinked")
        by_id = _controls_by_id(store)
        self.assertEqual(by_id["AC-2"]["finding_count"], 2)
        self.assertEqual(by_id["RA-5"]["finding_count"], 1)
        self.assertEqual(by_id["SI-10"]["finding_count"], 0)


class TestAssessControl(unittest.TestCase):
    """Core: Control mapping — assess_control (action assess_controls)."""

    def test_assess_control_happy_path(self):
        """Core: Control mapping. Contract: assess_control returns the
        updated control dict (list_controls shape) with the new
        status, evidence, assessed_by and assessed_utc set."""
        store, asset, finding = make_store()
        updated = store.assess_control(
            "AC-2", "implemented", actor=ANALYST,
            evidence="quarterly account review attached",
        )
        self.assertEqual(set(updated.keys()), CONTROL_KEYS)
        self.assertEqual(updated["id"], "AC-2")
        self.assertEqual(updated["status"], "implemented")
        self.assertEqual(updated["evidence"],
                         "quarterly account review attached")
        self.assertEqual(updated["assessed_by"], "bob")
        self.assertIsNotNone(updated["assessed_utc"])
        _parse_ts(updated["assessed_utc"])  # must not raise
        # And the change is visible through list_controls.
        self.assertEqual(
            _controls_by_id(store)["AC-2"]["status"], "implemented"
        )

    def test_assess_control_accepts_each_assessable_status(self):
        """Core: Control mapping. Contract: status must be in
        ASSESSMENT_STATUSES — implemented, partially_implemented and
        not_implemented are all assessable."""
        store, asset, finding = make_store()
        for status in ("implemented", "partially_implemented",
                       "not_implemented"):
            with self.subTest(status=status):
                updated = store.assess_control("AU-2", status,
                                               actor=ANALYST)
                self.assertEqual(updated["status"], status)

    def test_assess_control_evidence_defaults_to_empty(self):
        """Core: Control mapping. Contract: assess_control's evidence
        parameter defaults to ""."""
        store, asset, finding = make_store()
        updated = store.assess_control("AU-2", "implemented",
                                       actor=ANALYST)
        self.assertEqual(updated["evidence"], "")

    def test_assess_unknown_control_is_not_found(self):
        """Core: Control mapping. Contract: 'Unknown control_id →
        NotFoundError.'"""
        store, asset, finding = make_store()
        with self.assertRaises(NotFoundError):
            store.assess_control("XX-99", "implemented", actor=ANALYST)

    def test_assess_with_not_assessed_is_validation_error(self):
        """Core: Control mapping. Contract: status must be in
        ASSESSMENT_STATUSES 'and not "not_assessed" — assessing means
        assessing' — so not_assessed is a ValidationError."""
        store, asset, finding = make_store()
        with self.assertRaises(ValidationError):
            store.assess_control("AC-2", "not_assessed", actor=ANALYST)
        self.assertEqual(
            _controls_by_id(store)["AC-2"]["status"], "not_assessed"
        )

    def test_assess_with_unknown_status_is_validation_error(self):
        """Core: Control mapping. Contract: a status outside
        ASSESSMENT_STATUSES is a ValidationError."""
        store, asset, finding = make_store()
        with self.assertRaises(ValidationError):
            store.assess_control("AC-2", "mostly-done", actor=ANALYST)

    def test_viewer_cannot_assess_a_control(self):
        """Core: Control mapping + Access control. assess_control
        takes action assess_controls, which viewer lacks."""
        store, asset, finding = make_store()
        with self.assertRaises(PermissionDenied):
            store.assess_control("AC-2", "implemented", actor=VIEWER)


class TestPostureCoverageMath(unittest.TestCase):
    """Core: Control mapping / Posture reporting — coverage math."""

    def test_coverage_counts_assessed_and_implemented(self):
        """Core: Posture reporting. Contract: controls summary is
        {total: 34, assessed, implemented, coverage_pct} where
        assessed counts status != not_assessed, implemented counts
        status implemented, and coverage_pct = round(100 *
        implemented / total, 1) — 1 implemented + 1 partial of 34
        gives assessed 2, implemented 1, coverage 2.9."""
        store, asset, finding = make_store()
        store.assess_control("AC-2", "implemented", actor=ANALYST)
        store.assess_control("AU-2", "partially_implemented",
                             actor=ANALYST)
        controls = store.posture_summary(actor=ANALYST)["controls"]
        self.assertEqual(controls["total"], 34)
        self.assertEqual(controls["assessed"], 2)
        self.assertEqual(controls["implemented"], 1)
        self.assertEqual(controls["coverage_pct"], 2.9)

    def test_coverage_full_when_every_control_is_implemented(self):
        """Core: Posture reporting. Coverage math at the top of the
        scale: all 34 implemented gives coverage_pct 100.0."""
        store, asset, finding = make_store()
        for control in CONTROL_CATALOG:
            store.assess_control(control["id"], "implemented",
                                 actor=ANALYST)
        controls = store.posture_summary(actor=ANALYST)["controls"]
        self.assertEqual(controls["assessed"], 34)
        self.assertEqual(controls["implemented"], 34)
        self.assertEqual(controls["coverage_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
