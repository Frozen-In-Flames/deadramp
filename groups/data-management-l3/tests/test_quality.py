"""Data-quality rule and check tests.

Traces to: Core functions -- Quality rules, Quality checks; contract
for ``create_quality_rule`` / ``get_quality_rule`` /
``list_quality_rules`` / ``run_quality_check`` /
``get_quality_check`` / ``list_quality_checks`` with the pinned
per-kind violation semantics; SI-10, AC-3. Failed operations must
consume no ids. Every check-run expectation below is hand-computed
from the pinned semantics:

- completeness: absent / None / "" violates.
- uniqueness: a present value equal to an earlier record's violates;
  absent/None is not counted.
- format: absent/None violates; else re.fullmatch(pattern, str(v)).
- range: absent/None/bool/non-numeric violates; else outside
  [min, max] violates (edges are inclusive-pass).
- freshness: value must parse ISO-8601 (Z ok); absent/unparseable
  violates; else (now - value) > max_age_hours violates.
"""

import unittest

from datamgmt_helpers import STEWARD, VIEWER, fresh_store, make_store
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError

NOW = "2026-01-02T12:00:00Z"


class TestRuleCreation(unittest.TestCase):
    """Core: Quality rules -- creation and per-kind params validation."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def _rule(self, name="r", kind="completeness", field="patient_id", params=None):
        """Core: Quality rules. Helper creating a rule on the canonical dataset."""
        return self.store.create_quality_rule(
            self.dataset["id"], name, kind, field, STEWARD, params=params
        )

    def test_create_shape(self):
        """Core: Quality rules. Created rule carries qr-1, dataset, name, kind, field, params."""
        rule = self._rule(name="pid-present")
        self.assertEqual(rule["id"], "qr-1")
        self.assertEqual(rule["dataset_id"], self.dataset["id"])
        self.assertEqual(rule["name"], "pid-present")
        self.assertEqual(rule["kind"], "completeness")
        self.assertEqual(rule["field"], "patient_id")
        self.assertIn("created_utc", rule)

    def test_ids_sequential(self):
        """Core: Quality rules. Ids are qr-1, qr-2, ... in creation order."""
        self.assertEqual(self._rule(name="a")["id"], "qr-1")
        self.assertEqual(self._rule(name="b")["id"], "qr-2")

    def test_all_kinds_accepted(self):
        """Core: Quality rules. All pinned kinds are accepted with valid params."""
        cases = [
            ("completeness", None), ("uniqueness", None),
            ("format", {"pattern": "^[A-Z]+$"}),
            ("range", {"min": 0, "max": 10}),
            ("freshness", {"max_age_hours": 24}),
        ]
        for kind, params in cases:
            with self.subTest(kind=kind):
                rule = self._rule(name="k-%s" % kind, kind=kind, params=params)
                self.assertEqual(rule["kind"], kind)

    def test_bad_kind_rejected_no_id(self):
        """Core: Quality rules (SI-10). Bad kind -> ValidationError and no id consumed."""
        with self.assertRaises(ValidationError):
            self._rule(kind="spellcheck")
        self.assertEqual(self._rule(name="ok")["id"], "qr-1")

    def test_unknown_dataset_not_found_no_id(self):
        """Core: Quality rules. Unknown dataset -> NotFoundError and no id consumed."""
        with self.assertRaises(NotFoundError):
            self.store.create_quality_rule("ds-999", "r", "completeness", "f", STEWARD)
        self.assertEqual(self._rule(name="ok")["id"], "qr-1")

    def test_format_requires_pattern(self):
        """Core: Quality rules (SI-10). format without params.pattern -> ValidationError, no id."""
        for params in (None, {}, {"pattern": None}):
            with self.subTest(params=params):
                with self.assertRaises(ValidationError):
                    self._rule(kind="format", params=params)
        self.assertEqual(
            self._rule(name="ok", kind="format", params={"pattern": "^a$"})["id"], "qr-1"
        )

    def test_format_pattern_must_compile(self):
        """Core: Quality rules (SI-10). format with a non-compiling regex -> ValidationError, no id."""
        with self.assertRaises(ValidationError):
            self._rule(kind="format", params={"pattern": "[unclosed"})
        self.assertEqual(
            self._rule(name="ok", kind="format", params={"pattern": "^a$"})["id"], "qr-1"
        )

    def test_range_requires_min_or_max(self):
        """Core: Quality rules (SI-10). range without min and without max -> ValidationError, no id."""
        for params in (None, {}, {"min": None, "max": None}):
            with self.subTest(params=params):
                with self.assertRaises(ValidationError):
                    self._rule(kind="range", field="amount", params=params)
        self.assertEqual(
            self._rule(name="ok", kind="range", field="amount", params={"min": 0})["id"],
            "qr-1",
        )

    def test_range_min_only_and_max_only_accepted(self):
        """Core: Quality rules. range with only min, or only max, is accepted."""
        self.assertEqual(self._rule(name="lo", kind="range", field="amount", params={"min": 0})["kind"], "range")
        self.assertEqual(self._rule(name="hi", kind="range", field="amount", params={"max": 9})["kind"], "range")

    def test_range_non_numeric_bounds_rejected(self):
        """Core: Quality rules (SI-10). range with non-numeric min/max -> ValidationError."""
        with self.assertRaises(ValidationError):
            self._rule(kind="range", field="amount", params={"min": "zero"})

    def test_freshness_requires_positive_max_age(self):
        """Core: Quality rules (SI-10). freshness without max_age_hours > 0 -> ValidationError, no id."""
        for params in (None, {}, {"max_age_hours": 0}, {"max_age_hours": -3}, {"max_age_hours": "24"}):
            with self.subTest(params=params):
                with self.assertRaises(ValidationError):
                    self._rule(kind="freshness", params=params)
        self.assertEqual(
            self._rule(name="ok", kind="freshness", params={"max_age_hours": 24})["id"],
            "qr-1",
        )

    def test_get_and_list_rules(self):
        """Core: Quality rules. get_quality_rule round-trips; list filters by dataset, viewer-readable."""
        rule = self._rule(name="one")
        self.assertEqual(self.store.get_quality_rule(rule["id"], VIEWER)["name"], "one")
        other = self.store.create_dataset("Other", "d", STEWARD)
        self.store.create_quality_rule(other["id"], "two", "completeness", "f", STEWARD)
        self.assertEqual(
            [r["id"] for r in self.store.list_quality_rules(dataset_id=self.dataset["id"], actor=VIEWER)],
            [rule["id"]],
        )
        self.assertEqual(len(self.store.list_quality_rules(actor=VIEWER)), 2)
        with self.assertRaises(NotFoundError):
            self.store.get_quality_rule("qr-999", STEWARD)

    def test_viewer_create_denied_no_id(self):
        """Core: Quality rules (AC-3). Viewer create -> PermissionDenied and no id consumed."""
        with self.assertRaises(PermissionDenied):
            self.store.create_quality_rule(
                self.dataset["id"], "nope", "completeness", "patient_id", VIEWER
            )
        self.assertEqual(self._rule(name="ok")["id"], "qr-1")


class TestQualityChecks(unittest.TestCase):
    """Core: Quality checks -- one hand-computed run per kind."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def _run(self, kind, field, records, params=None, now=None):
        """Core: Quality checks. Helper: create a rule and run it."""
        rule = self.store.create_quality_rule(
            self.dataset["id"], "rule-%s" % kind, kind, field, STEWARD, params=params
        )
        return rule, self.store.run_quality_check(rule["id"], records, STEWARD, now=now)

    def test_check_shape_and_ids(self):
        """Core: Quality checks. A check carries qc-1, rule/dataset ids, counts and passed flag."""
        rule, check = self._run("completeness", "patient_id", [{"patient_id": "P1"}])
        self.assertEqual(check["id"], "qc-1")
        self.assertEqual(check["rule_id"], rule["id"])
        self.assertEqual(check["dataset_id"], self.dataset["id"])
        self.assertEqual(check["kind"], "completeness")
        self.assertEqual(check["field"], "patient_id")
        self.assertEqual(check["records_checked"], 1)
        self.assertEqual(check["violations"], 0)
        self.assertTrue(check["passed"])
        self.assertIn("checked_utc", check)

    def test_completeness_hand_computed(self):
        """Core: Quality checks -- completeness. 4 records: present, None, absent, "" -> 3 violations."""
        records = [{"patient_id": "P1"}, {"patient_id": None}, {}, {"patient_id": ""}]
        rule, check = self._run("completeness", "patient_id", records)
        self.assertEqual(check["records_checked"], 4)
        self.assertEqual(check["violations"], 3)
        self.assertFalse(check["passed"])

    def test_completeness_all_present_passes(self):
        """Core: Quality checks -- completeness. All values present (incl. 0) -> 0 violations, passed."""
        records = [{"patient_id": "P1"}, {"patient_id": "P2"}, {"patient_id": 0}]
        rule, check = self._run("completeness", "patient_id", records)
        self.assertEqual(check["violations"], 0)
        self.assertTrue(check["passed"])

    def test_uniqueness_hand_computed(self):
        """Core: Quality checks -- uniqueness. P1,P2,P1,P1 -> 2 violations (3rd and 4th repeat earlier values)."""
        records = [{"patient_id": v} for v in ("P1", "P2", "P1", "P1")]
        rule, check = self._run("uniqueness", "patient_id", records)
        self.assertEqual(check["records_checked"], 4)
        self.assertEqual(check["violations"], 2)
        self.assertFalse(check["passed"])

    def test_uniqueness_absent_and_none_not_counted(self):
        """Core: Quality checks -- uniqueness. Repeated absent/None values are not violations."""
        records = [{"patient_id": "P1"}, {}, {"patient_id": None}, {}, {"patient_id": None}]
        rule, check = self._run("uniqueness", "patient_id", records)
        self.assertEqual(check["violations"], 0)
        self.assertTrue(check["passed"])

    def test_format_hand_computed(self):
        """Core: Quality checks -- format ^[A-Z]{2}\\d{4}$. AB1234 passes; ab1234, AB123, None, absent violate -> 4."""
        records = [
            {"patient_id": "AB1234"}, {"patient_id": "ab1234"},
            {"patient_id": "AB123"}, {"patient_id": None}, {},
        ]
        rule, check = self._run(
            "format", "patient_id", records, params={"pattern": r"^[A-Z]{2}\d{4}$"}
        )
        self.assertEqual(check["records_checked"], 5)
        self.assertEqual(check["violations"], 4)
        self.assertFalse(check["passed"])

    def test_format_uses_fullmatch(self):
        """Core: Quality checks -- format. A value merely containing a match (XAB1234) violates under fullmatch."""
        records = [{"patient_id": "AB1234"}, {"patient_id": "XAB1234"}]
        rule, check = self._run(
            "format", "patient_id", records, params={"pattern": r"^[A-Z]{2}\d{4}$"}
        )
        self.assertEqual(check["violations"], 1)

    def test_range_hand_computed_edges_inclusive(self):
        """Core: Quality checks -- range [0,100]. 0, 100 and 50 pass (edges inclusive); -1, 101, None, True violate -> 4."""
        records = [{"amount": v} for v in (0, 100, 50, -1, 101, None, True)]
        rule, check = self._run("range", "amount", records, params={"min": 0, "max": 100})
        self.assertEqual(check["records_checked"], 7)
        self.assertEqual(check["violations"], 4)
        self.assertFalse(check["passed"])

    def test_range_non_numeric_and_absent_violate(self):
        """Core: Quality checks -- range. A numeric string and an absent value both violate."""
        records = [{"amount": "50"}, {}]
        rule, check = self._run("range", "amount", records, params={"min": 0, "max": 100})
        self.assertEqual(check["violations"], 2)

    def test_range_min_only(self):
        """Core: Quality checks -- range with only min. 5 passes, -1 violates."""
        records = [{"amount": 5}, {"amount": 10 ** 9}, {"amount": -1}]
        rule, check = self._run("range", "amount", records, params={"min": 0})
        self.assertEqual(check["violations"], 1)

    def test_freshness_hand_computed(self):
        """Core: Quality checks -- freshness (max_age 24h, now 2026-01-02T12:00Z). 1h-old passes; 25h-old, unparseable, absent, None violate -> 4."""
        records = [
            {"patient_id": "2026-01-02T11:00:00Z"},
            {"patient_id": "2026-01-01T11:00:00Z"},
            {"patient_id": "not-a-date"},
            {},
            {"patient_id": None},
        ]
        rule, check = self._run(
            "freshness", "patient_id", records, params={"max_age_hours": 24}, now=NOW
        )
        self.assertEqual(check["records_checked"], 5)
        self.assertEqual(check["violations"], 4)
        self.assertFalse(check["passed"])

    def test_freshness_exactly_max_age_passes(self):
        """Core: Quality checks -- freshness. Age exactly max_age_hours is not > max, so it passes."""
        records = [{"patient_id": "2026-01-01T12:00:00Z"}]
        rule, check = self._run(
            "freshness", "patient_id", records, params={"max_age_hours": 24}, now=NOW
        )
        self.assertEqual(check["violations"], 0)
        self.assertTrue(check["passed"])

    def test_empty_records_passes(self):
        """Core: Quality checks. Zero records -> 0 checked, 0 violations, passed."""
        rule, check = self._run("completeness", "patient_id", [])
        self.assertEqual(check["records_checked"], 0)
        self.assertEqual(check["violations"], 0)
        self.assertTrue(check["passed"])

    def test_get_and_list_checks(self):
        """Core: Quality checks. get_quality_check round-trips; list filters by rule and by dataset."""
        rule, check = self._run("completeness", "patient_id", [{"patient_id": "P1"}])
        self.assertEqual(self.store.get_quality_check(check["id"], VIEWER)["id"], check["id"])
        self.assertEqual(
            [c["id"] for c in self.store.list_quality_checks(rule_id=rule["id"], actor=VIEWER)],
            [check["id"]],
        )
        self.assertEqual(
            [c["id"] for c in self.store.list_quality_checks(dataset_id=self.dataset["id"], actor=VIEWER)],
            [check["id"]],
        )
        other_rule = self.store.create_quality_rule(
            self.dataset["id"], "other", "completeness", "amount", STEWARD
        )
        self.assertEqual(
            self.store.list_quality_checks(rule_id=other_rule["id"], actor=VIEWER), []
        )
        with self.assertRaises(NotFoundError):
            self.store.get_quality_check("qc-999", STEWARD)

    def test_run_unknown_rule_not_found_no_id(self):
        """Core: Quality checks. Unknown rule -> NotFoundError and no qc id consumed."""
        with self.assertRaises(NotFoundError):
            self.store.run_quality_check("qr-999", [], STEWARD)
        rule, check = self._run("completeness", "patient_id", [])
        self.assertEqual(check["id"], "qc-1")

    def test_viewer_run_denied_no_id(self):
        """Core: Quality checks (AC-3). Viewer run -> PermissionDenied and no qc id consumed."""
        rule = self.store.create_quality_rule(
            self.dataset["id"], "r", "completeness", "patient_id", STEWARD
        )
        with self.assertRaises(PermissionDenied):
            self.store.run_quality_check(rule["id"], [{"patient_id": "P1"}], VIEWER)
        check = self.store.run_quality_check(rule["id"], [{"patient_id": "P1"}], STEWARD)
        self.assertEqual(check["id"], "qc-1")


if __name__ == "__main__":
    unittest.main()
