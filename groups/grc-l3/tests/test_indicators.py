"""Indicator (KSI) registry and recorded-results tests.

Traces to: Core function 3 (indicator registry — indicator definitions
linked to controls, plus recorded validation RESULTS carrying
indicator, system, result status, timestamp, recorded-by; results are
records and no automated validation is performed); control family
CA-7 (continuous monitoring — the records are the monitoring trail).
"""

import unittest

from grc_helpers import (
    ADMIN,
    MEMBER,
    VIEWER,
    INDICATOR_ID,
    SYSTEM_REF,
    make_store,
)
from grc.errors import NotFoundError, PermissionDenied, ValidationError


class TestIndicatorDefinitions(unittest.TestCase):
    """Core 3: indicator definitions linked to controls."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()

    def test_indicator_shape_and_control_links(self):
        """Core 3. An indicator definition carries its id, name,
        description, the linked control ids, and provenance."""
        indicator = self.indicator
        self.assertEqual(indicator["id"], INDICATOR_ID)
        self.assertEqual(indicator["name"], "MFA coverage indicator")
        self.assertEqual(indicator["control_ids"], ["IA-2"])
        self.assertEqual(indicator["created_by"], "bob")
        self.assertEqual(
            self.store.get_indicator(INDICATOR_ID, actor=VIEWER), indicator
        )

    def test_indicator_links_multiple_controls(self):
        """Core 3. An indicator may link several registered controls."""
        indicator = self.store.create_indicator(
            "KSI-2", "Logging indicator", ["AU-2", "AU-6", "SI-4"], actor=MEMBER
        )
        self.assertEqual(indicator["control_ids"], ["AU-2", "AU-6", "SI-4"])

    def test_indicator_unknown_control_rejected(self):
        """Core 3. Linking an unregistered control id is a
        ValidationError and registers nothing."""
        with self.assertRaises(ValidationError):
            self.store.create_indicator("KSI-2", "Bad link", ["ZZ-9"], actor=MEMBER)
        self.assertEqual(len(self.store.list_indicators(actor=ADMIN)), 1)

    def test_indicator_duplicate_rejected(self):
        """Core 3. A duplicate indicator id is a ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_indicator(INDICATOR_ID, "Again", ["AC-2"], actor=MEMBER)

    def test_indicator_missing_404(self):
        """Core 3. An unknown indicator id is a NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_indicator("KSI-404", actor=ADMIN)


class TestIndicatorResults(unittest.TestCase):
    """Core 3: recorded validation results."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()

    def test_record_result_shape(self):
        """Core 3. A recorded result carries indicator, system, the
        status verbatim, the supplied timestamp verbatim, and the
        recording identity."""
        result = self.store.record_indicator_result(
            INDICATOR_ID,
            SYSTEM_REF,
            "reported-pass",
            actor=MEMBER,
            timestamp="2026-10-01T00:00:00Z",
            note="per assessor worksheet",
        )
        self.assertEqual(result["id"], "result-1")
        self.assertEqual(result["indicator_id"], INDICATOR_ID)
        self.assertEqual(result["system_ref"], SYSTEM_REF)
        self.assertEqual(result["status"], "reported-pass")
        self.assertEqual(result["timestamp"], "2026-10-01T00:00:00Z")
        self.assertEqual(result["recorded_by"], "bob")
        self.assertEqual(result["note"], "per assessor worksheet")

    def test_result_status_is_recorded_verbatim(self):
        """Core 3. Any non-empty status string is stored exactly as
        supplied — vendor or house wording is never normalized,
        mapped, or computed."""
        for status in ["pass", "FAIL", "Satisfied (vendor wording)", "n/a — see note"]:
            result = self.store.record_indicator_result(
                INDICATOR_ID, SYSTEM_REF, status, actor=MEMBER
            )
            self.assertEqual(result["status"], status)
        statuses = [
            r["status"]
            for r in self.store.list_indicator_results(actor=ADMIN)
        ]
        self.assertEqual(
            statuses, ["pass", "FAIL", "Satisfied (vendor wording)", "n/a — see note"]
        )

    def test_result_timestamp_defaults_to_now_utc(self):
        """Core 3. Without a supplied timestamp, the result is stamped
        with the recording time in UTC ISO-8601."""
        result = self.store.record_indicator_result(
            INDICATOR_ID, SYSTEM_REF, "pass", actor=MEMBER
        )
        self.assertTrue(result["timestamp"].endswith("+00:00"))

    def test_result_requires_known_indicator_and_system(self):
        """Core 3. Recording against an unknown indicator or system
        is a NotFoundError and consumes no result id."""
        with self.assertRaises(NotFoundError):
            self.store.record_indicator_result("KSI-404", SYSTEM_REF, "pass", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.record_indicator_result(INDICATOR_ID, "NOPE", "pass", actor=MEMBER)
        result = self.store.record_indicator_result(
            INDICATOR_ID, SYSTEM_REF, "pass", actor=MEMBER
        )
        self.assertEqual(result["id"], "result-1")

    def test_result_empty_status_and_bad_timestamp_rejected(self):
        """Core 3. An empty status or a malformed timestamp is a
        ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.record_indicator_result(INDICATOR_ID, SYSTEM_REF, "", actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.store.record_indicator_result(
                INDICATOR_ID, SYSTEM_REF, "pass", actor=MEMBER, timestamp="not-a-date"
            )

    def test_results_filter_by_indicator_and_system(self):
        """Core 3. list_indicator_results filters by indicator and/or
        system, in recording order."""
        self.store.create_indicator("KSI-2", "Logging", ["AU-2"], actor=MEMBER)
        self.store.create_system("SYS-002", "second", actor=MEMBER)
        self.store.record_indicator_result(INDICATOR_ID, SYSTEM_REF, "pass", actor=MEMBER)
        self.store.record_indicator_result("KSI-2", SYSTEM_REF, "fail", actor=MEMBER)
        self.store.record_indicator_result(INDICATOR_ID, "SYS-002", "pass", actor=MEMBER)
        by_indicator = self.store.list_indicator_results(actor=ADMIN, indicator_id=INDICATOR_ID)
        self.assertEqual([r["id"] for r in by_indicator], ["result-1", "result-3"])
        by_system = self.store.list_indicator_results(actor=ADMIN, system_ref="SYS-002")
        self.assertEqual([r["id"] for r in by_system], ["result-3"])
        both = self.store.list_indicator_results(
            actor=ADMIN, indicator_id="KSI-2", system_ref=SYSTEM_REF
        )
        self.assertEqual([r["id"] for r in both], ["result-2"])

    def test_viewer_may_read_but_not_record(self):
        """Core 3 + Core 9 RBAC. Viewer reads results; recording one
        as viewer is PermissionDenied."""
        self.store.record_indicator_result(INDICATOR_ID, SYSTEM_REF, "pass", actor=MEMBER)
        self.assertEqual(
            len(self.store.list_indicator_results(actor=VIEWER)), 1
        )
        with self.assertRaises(PermissionDenied):
            self.store.record_indicator_result(
                INDICATOR_ID, SYSTEM_REF, "pass", actor=VIEWER
            )


if __name__ == "__main__":
    unittest.main()
