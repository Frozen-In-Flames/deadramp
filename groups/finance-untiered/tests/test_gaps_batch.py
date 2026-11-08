"""Final GAPS batch tests — Finance untiered set (Untiered Set 24).

Pins the extension surface in ``finance.extensions`` for the
section's 2 open entries:

- idx 948 — Expense reporting, approval & reimbursement workflow
  engine (drafted stub-engine; **built** in records form under a
  re-judgment recorded in ``../BATCH.md``): expense report records
  running draft -> submitted -> approved / denied -> reimbursed
  (via a reimbursement record) / void, with separation of duties,
  totals derived at read and never stored, and reimbursements
  recorded, never executed (``paid_here`` / ``settled_here``:
  False).
- idx 949 — Travel & expense policy enforcement engine (drafted
  build-extension; **built** as drafted): policy records holding
  declared rules as data, plus compliance evaluations derived at
  read through the ``_exceeds`` seam -- never stored, blocking
  nothing.

Cross-cutting pins: tier stays null (no tier / baseline / impact /
equivalence key anywhere on the surface, recursive scan); money is
integer cents (floats and booleans rejected at every boundary);
no record shape can hold a real account identifier or personal
data (exact key sets + recursive key scan); a full expense flow
leaves every core record byte-identical; audit-write failure
rolls the mutation and its id back.

The fresh mutation-verified negative control for this surface is
``TestPolicyEvaluationNegativeControl``: the ``_exceeds``
comparison seam. The canonical rule is that a recorded line (or
report total) strictly greater than a recorded cap is a
violation, and exactly-at-cap complies. The mutant is
violation-blind (``_exceeds`` returns False unconditionally): it
waves every over-cap report through as compliant.
"""

import unittest

import finance_helpers as H
from finance.errors import NotFoundError, PermissionDenied, ValidationError
from finance.extensions import FinanceExtensions
from finance.store import FinanceStore

PERIOD = H.PERIOD

FORBIDDEN_KEYS = {
    # tier discipline: this set is untiered, tier null
    "tier", "cmmc_tier", "fedramp_impact_level", "impact_level",
    "baseline", "equivalence",
    # privacy: no shape may hold a real identifier or account data
    "account", "account_number", "routing", "iban", "sort_code",
    "card_number", "ssn", "name_of_person", "email",
    # no scoring anywhere on this surface
    "score", "credit_score",
}


def scan_forbidden(node, path="root"):
    """Recursively assert no forbidden key and no float value."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, "forbidden key %r at %s" % (key, path)
            scan_forbidden(value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for i, value in enumerate(node):
            scan_forbidden(value, "%s[%d]" % (path, i))
    else:
        assert not isinstance(node, float), "float value at %s: %r" % (path, node)


def make_extensions():
    """Canonical fixture: core store + extension + one employee."""
    store, audit, program_id = H.make_store()
    ext = FinanceExtensions(store)
    employee = H.make_employee(store, program_id)
    return ext, store, audit, program_id, employee["id"]


def make_report(ext, program_id, participant_id, lines=None, actor=H.MEMBER,
                period=PERIOD):
    if lines is None:
        lines = [
            {"category": "meals", "amount_cents": 4200},
            {"category": "lodging", "amount_cents": 12500},
        ]
    return ext.create_expense_report(
        program_id, participant_id, period, lines, actor)


def approved_report(ext, program_id, participant_id, lines=None):
    """Create + submit (creator) + approve (ADMIN, never the creator)."""
    report = make_report(ext, program_id, participant_id, lines=lines)
    ext.submit_expense_report(program_id, report["id"], H.MEMBER)
    return ext.decide_expense_report(program_id, report["id"], True, H.ADMIN)


class TestExpenseReportCreation(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()

    def test_create_shape_and_exact_keys(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.assertEqual(report["id"], "exp-1")
        self.assertEqual(
            set(report),
            {"id", "program_id", "participant_id", "period", "lines",
             "status", "created_by", "created_utc"})
        self.assertEqual(report["status"], "draft")
        self.assertEqual(report["participant_id"], self.emp)
        # the stored record carries no total: totals derive at read
        self.assertNotIn("total_cents", report)

    def test_view_derives_total_from_recorded_lines(self):
        report = make_report(self.ext, self.pid, self.emp)
        view = self.ext.get_expense_report(self.pid, report["id"], H.MEMBER)
        self.assertEqual(view["total_cents"], 4200 + 12500)
        self.assertEqual(
            set(view),
            {"id", "program_id", "participant_id", "period", "lines",
             "status", "created_by", "created_utc", "total_cents"})

    def test_lines_are_deep_copied_at_the_boundary(self):
        lines = [{"category": "meals", "amount_cents": 100}]
        report = self.ext.create_expense_report(
            self.pid, self.emp, PERIOD, lines, H.MEMBER)
        lines[0]["amount_cents"] = 999999
        view = self.ext.get_expense_report(self.pid, report["id"], H.MEMBER)
        self.assertEqual(view["total_cents"], 100)
        view["lines"][0]["amount_cents"] = 555
        again = self.ext.get_expense_report(self.pid, report["id"], H.MEMBER)
        self.assertEqual(again["total_cents"], 100)

    def test_traveler_may_file_expenses(self):
        traveler = H.make_traveler(self.store, self.pid)
        report = make_report(self.ext, self.pid, traveler["id"])
        self.assertEqual(report["participant_id"], traveler["id"])

    def test_unknown_participant_is_not_found(self):
        with self.assertRaises(NotFoundError):
            make_report(self.ext, self.pid, "part-999")

    def test_bad_period_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_expense_report(
                self.pid, self.emp, "2026-13",
                [{"category": "meals", "amount_cents": 100}], H.MEMBER)

    def test_line_amount_must_be_integer_cents(self):
        for bad in (10.5, 100.0, True, "100"):
            with self.assertRaises(ValidationError):
                self.ext.create_expense_report(
                    self.pid, self.emp, PERIOD,
                    [{"category": "meals", "amount_cents": bad}], H.MEMBER)

    def test_line_amount_must_be_positive(self):
        for bad in (0, -1):
            with self.assertRaises(ValidationError):
                self.ext.create_expense_report(
                    self.pid, self.emp, PERIOD,
                    [{"category": "meals", "amount_cents": bad}], H.MEMBER)

    def test_duplicate_line_category_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_expense_report(
                self.pid, self.emp, PERIOD,
                [{"category": "meals", "amount_cents": 100},
                 {"category": "meals", "amount_cents": 200}], H.MEMBER)

    def test_line_with_extra_key_rejected(self):
        # a 'note' / content key has no place in the shape
        with self.assertRaises(ValidationError):
            self.ext.create_expense_report(
                self.pid, self.emp, PERIOD,
                [{"category": "meals", "amount_cents": 100,
                  "note": "taxi"}], H.MEMBER)

    def test_empty_lines_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_expense_report(
                self.pid, self.emp, PERIOD, [], H.MEMBER)
        report = make_report(self.ext, self.pid, self.emp)
        self.assertEqual(report["id"], "exp-1")

    def test_viewer_create_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            make_report(self.ext, self.pid, self.emp, actor=H.VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_expense_create:denied", actions)

    def test_non_member_create_denied(self):
        with self.assertRaises(PermissionDenied):
            make_report(self.ext, self.pid, self.emp, actor=H.OUTSIDER)


class TestExpenseWorkflow(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()

    def test_submit_moves_draft_to_submitted(self):
        report = make_report(self.ext, self.pid, self.emp)
        updated = self.ext.submit_expense_report(
            self.pid, report["id"], H.MEMBER)
        self.assertEqual(updated["status"], "submitted")

    def test_submit_twice_rejected(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)

    def test_unrelated_member_may_not_submit(self):
        # created by ADMIN: neither creator, owner, nor admin is VIEWER
        report = make_report(self.ext, self.pid, self.emp, actor=H.ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.submit_expense_report(self.pid, report["id"], H.VIEWER)
        # the program owner may submit it
        updated = self.ext.submit_expense_report(
            self.pid, report["id"], H.MEMBER)
        self.assertEqual(updated["status"], "submitted")

    def test_decide_approve_records_decider(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)
        decided = self.ext.decide_expense_report(
            self.pid, report["id"], True, H.ADMIN)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["decided_by"], "alice")
        self.assertIn("decided_utc", decided)

    def test_creator_may_not_decide_own_report(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.decide_expense_report(
                self.pid, report["id"], True, H.MEMBER)
        view = self.ext.get_expense_report(self.pid, report["id"], H.MEMBER)
        self.assertEqual(view["status"], "submitted")

    def test_decide_requires_submitted_status(self):
        report = make_report(self.ext, self.pid, self.emp)
        with self.assertRaises(ValidationError):
            self.ext.decide_expense_report(
                self.pid, report["id"], True, H.ADMIN)

    def test_decide_approve_must_be_bool(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.decide_expense_report(
                self.pid, report["id"], "yes", H.ADMIN)

    def test_deny_then_void(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)
        denied = self.ext.decide_expense_report(
            self.pid, report["id"], False, H.ADMIN)
        self.assertEqual(denied["status"], "denied")
        voided = self.ext.void_expense_report(
            self.pid, report["id"], H.MEMBER)
        self.assertEqual(voided["status"], "void")

    def test_void_approved_rejected(self):
        report = approved_report(self.ext, self.pid, self.emp)
        with self.assertRaises(ValidationError):
            self.ext.void_expense_report(self.pid, report["id"], H.MEMBER)

    def test_list_filters(self):
        first = make_report(self.ext, self.pid, self.emp)
        make_report(self.ext, self.pid, self.emp)
        self.ext.submit_expense_report(self.pid, first["id"], H.MEMBER)
        drafts = self.ext.list_expense_reports(
            self.pid, H.MEMBER, status="draft")
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["total_cents"], 16700)
        with self.assertRaises(ValidationError):
            self.ext.list_expense_reports(
                self.pid, H.MEMBER, status="bogus")


class TestReimbursements(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()

    def test_reimbursement_record_shape_and_report_transition(self):
        report = approved_report(self.ext, self.pid, self.emp)
        reimbursement = self.ext.record_reimbursement(
            self.pid, report["id"], "2026-01-20", H.MEMBER, method="payroll")
        self.assertEqual(reimbursement["id"], "rei-1")
        self.assertEqual(
            set(reimbursement),
            {"id", "program_id", "report_id", "participant_id", "period",
             "amount_cents", "date", "method", "paid_here", "settled_here",
             "created_by", "created_utc"})
        self.assertEqual(reimbursement["amount_cents"], 16700)
        self.assertIs(reimbursement["paid_here"], False)
        self.assertIs(reimbursement["settled_here"], False)
        view = self.ext.get_expense_report(self.pid, report["id"], H.MEMBER)
        self.assertEqual(view["status"], "reimbursed")
        self.assertEqual(view["reimbursement_id"], "rei-1")

    def test_reimbursement_requires_approved_status(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_reimbursement(
                self.pid, report["id"], "2026-01-20", H.MEMBER)

    def test_reimbursement_bad_date_rejected(self):
        report = approved_report(self.ext, self.pid, self.emp)
        with self.assertRaises(ValidationError):
            self.ext.record_reimbursement(
                self.pid, report["id"], "20-01-2026", H.MEMBER)

    def test_list_reimbursements_filtered_by_report(self):
        report = approved_report(self.ext, self.pid, self.emp)
        self.ext.record_reimbursement(
            self.pid, report["id"], "2026-01-20", H.MEMBER)
        mine = self.ext.list_reimbursements(
            self.pid, H.MEMBER, report_id=report["id"])
        self.assertEqual(len(mine), 1)
        other = self.ext.list_reimbursements(
            self.pid, H.MEMBER, report_id="exp-999")
        self.assertEqual(other, [])


class TestExpenseSummary(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()

    def test_summary_counts_and_totals_derived_at_read(self):
        approved = approved_report(self.ext, self.pid, self.emp)
        self.ext.record_reimbursement(
            self.pid, approved["id"], "2026-01-20", H.MEMBER)
        pending = make_report(
            self.ext, self.pid, self.emp,
            lines=[{"category": "meals", "amount_cents": 3000}])
        self.ext.submit_expense_report(self.pid, pending["id"], H.MEMBER)
        make_report(self.ext, self.pid, self.emp,
                    lines=[{"category": "taxi", "amount_cents": 1500}],
                    period=H.PERIOD_OTHER)
        summary = self.ext.expense_summary(self.pid, PERIOD, H.MEMBER)
        self.assertEqual(summary["report_count"], 2)
        self.assertEqual(summary["counts_by_status"]["reimbursed"], 1)
        self.assertEqual(summary["counts_by_status"]["submitted"], 1)
        self.assertEqual(summary["counts_by_status"]["draft"], 0)
        self.assertEqual(
            summary["totals_by_status_cents"]["reimbursed"], 16700)
        self.assertEqual(
            summary["totals_by_status_cents"]["submitted"], 3000)
        self.assertEqual(summary["reimbursed_cents"], 16700)
        self.assertEqual(
            summary["basis"],
            "recorded_expense_lines_and_reimbursement_records")
        self.assertIs(summary["paid_here"], False)

    def test_summary_bad_period_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.expense_summary(self.pid, "Jan 2026", H.MEMBER)


class TestExpensePolicies(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()

    def make_policy(self, rules=None, name="t-and-e"):
        if rules is None:
            rules = [
                {"kind": "category_line_cap", "category": "meals",
                 "limit_cents": 5000},
                {"kind": "report_total_cap", "category": None,
                 "limit_cents": 20000},
            ]
        return self.ext.create_expense_policy(self.pid, name, rules, H.MEMBER)

    def test_create_shape_and_exact_keys(self):
        policy = self.make_policy()
        self.assertEqual(policy["id"], "pol-1")
        self.assertEqual(
            set(policy),
            {"id", "program_id", "name", "rules", "definition_only",
             "created_by", "created_utc"})
        self.assertIs(policy["definition_only"], True)

    def test_rules_deep_copied_at_the_boundary(self):
        rules = [{"kind": "report_total_cap", "category": None,
                  "limit_cents": 100}]
        policy = self.ext.create_expense_policy(
            self.pid, "p", rules, H.MEMBER)
        rules[0]["limit_cents"] = 999999
        stored = self.ext.get_expense_policy(self.pid, policy["id"], H.MEMBER)
        self.assertEqual(stored["rules"][0]["limit_cents"], 100)

    def test_rule_validation(self):
        bad_rule_sets = [
            [],  # empty
            [{"kind": "bogus", "category": "meals", "limit_cents": 1}],
            [{"kind": "category_line_cap", "category": "",
              "limit_cents": 1}],
            [{"kind": "category_line_cap", "category": None,
              "limit_cents": 1}],
            [{"kind": "report_total_cap", "category": "meals",
              "limit_cents": 1}],
            [{"kind": "report_total_cap", "category": None,
              "limit_cents": -1}],
            [{"kind": "report_total_cap", "category": None,
              "limit_cents": 1.5}],
            [{"kind": "report_total_cap", "category": None,
              "limit_cents": True}],
            [{"kind": "report_total_cap", "category": None,
              "limit_cents": 1, "extra": 2}],
            [{"kind": "report_total_cap", "category": None,
              "limit_cents": 1},
             {"kind": "report_total_cap", "category": None,
              "limit_cents": 2}],  # duplicate rule
        ]
        for rules in bad_rule_sets:
            with self.assertRaises(ValidationError):
                self.ext.create_expense_policy(
                    self.pid, "p", rules, H.MEMBER)
        policy = self.make_policy()
        self.assertEqual(policy["id"], "pol-1")  # no id consumed

    def test_policy_in_other_program_is_not_found(self):
        policy = self.make_policy()
        other = self.store.create_program("other-program", H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_expense_policy(other["id"], policy["id"], H.MEMBER)


class TestPolicyEvaluation(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()
        self.policy = self.ext.create_expense_policy(
            self.pid, "t-and-e",
            [{"kind": "category_line_cap", "category": "meals",
              "limit_cents": 5000},
             {"kind": "report_total_cap", "category": None,
              "limit_cents": 20000}],
            H.MEMBER)

    def evaluate(self, report_id):
        return self.ext.evaluate_expense_report(
            self.pid, self.policy["id"], report_id, H.MEMBER)

    def test_compliant_report(self):
        report = make_report(self.ext, self.pid, self.emp)
        view = self.evaluate(report["id"])
        self.assertTrue(view["compliant"])
        self.assertEqual(view["violations"], [])
        self.assertEqual(view["violation_count"], 0)
        self.assertIs(view["blocked_here"], False)
        self.assertIs(view["paid_here"], False)

    def test_line_exactly_at_cap_complies(self):
        report = make_report(
            self.ext, self.pid, self.emp,
            lines=[{"category": "meals", "amount_cents": 5000}])
        self.assertTrue(self.evaluate(report["id"])["compliant"])

    def test_line_one_cent_over_cap_is_a_violation(self):
        report = make_report(
            self.ext, self.pid, self.emp,
            lines=[{"category": "meals", "amount_cents": 5001}])
        view = self.evaluate(report["id"])
        self.assertFalse(view["compliant"])
        self.assertEqual(len(view["violations"]), 1)
        violation = view["violations"][0]
        self.assertEqual(violation["kind"], "category_line_cap")
        self.assertEqual(violation["category"], "meals")
        self.assertEqual(violation["limit_cents"], 5000)
        self.assertEqual(violation["observed_cents"], 5001)

    def test_report_total_cap_violation(self):
        report = make_report(
            self.ext, self.pid, self.emp,
            lines=[{"category": "lodging", "amount_cents": 15000},
                   {"category": "airfare", "amount_cents": 6000}])
        view = self.evaluate(report["id"])
        self.assertFalse(view["compliant"])
        self.assertEqual(len(view["violations"]), 1)
        self.assertEqual(view["violations"][0]["kind"], "report_total_cap")
        self.assertEqual(view["violations"][0]["observed_cents"], 21000)

    def test_multiple_violations_all_reported(self):
        report = make_report(
            self.ext, self.pid, self.emp,
            lines=[{"category": "meals", "amount_cents": 9000},
                   {"category": "lodging", "amount_cents": 15000}])
        view = self.evaluate(report["id"])
        self.assertEqual(view["violation_count"], 2)
        kinds = {v["kind"] for v in view["violations"]}
        self.assertEqual(kinds, {"category_line_cap", "report_total_cap"})

    def test_evaluation_is_a_view_and_changes_nothing(self):
        report = make_report(
            self.ext, self.pid, self.emp,
            lines=[{"category": "meals", "amount_cents": 9000}])
        first = self.evaluate(report["id"])
        second = self.evaluate(report["id"])
        self.assertEqual(first, second)
        stored = self.ext.get_expense_report(
            self.pid, report["id"], H.MEMBER)
        self.assertEqual(stored["status"], "draft")
        self.assertEqual(
            len(self.ext.list_expense_policies(self.pid, H.MEMBER)), 1)
        self.assertEqual(
            len(self.ext.list_expense_reports(self.pid, H.MEMBER)), 1)


class ViolationBlindExtensions(FinanceExtensions):
    """Mutant: the comparison seam never flags an excess."""

    def _exceeds(self, observed_cents, limit_cents):
        return False


class TestPolicyEvaluationNegativeControl(unittest.TestCase):
    """Three-leg control on the ``_exceeds`` seam.

    Canonical: an over-cap line is flagged. Mutant (violation-
    blind): the same report reads compliant. Treating the
    mutant's outcome as the canonical expectation fails.
    """

    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()
        self.policy = self.ext.create_expense_policy(
            self.pid, "t-and-e",
            [{"kind": "category_line_cap", "category": "meals",
              "limit_cents": 5000}],
            H.MEMBER)
        self.report = make_report(
            self.ext, self.pid, self.emp,
            lines=[{"category": "meals", "amount_cents": 5001}])

    def test_canonical_flags_the_over_cap_line(self):
        view = self.ext.evaluate_expense_report(
            self.pid, self.policy["id"], self.report["id"], H.MEMBER)
        self.assertFalse(view["compliant"])
        self.assertEqual(view["violation_count"], 1)

    def blind_mutant(self):
        """The mutant subclass, sharing the canonical record tables."""
        mutant = ViolationBlindExtensions(self.store)
        mutant._records = self.ext._records
        mutant._order = self.ext._order
        mutant._counters = self.ext._counters
        return mutant

    def test_mutant_waves_the_over_cap_line_through(self):
        mutant = self.blind_mutant()
        view = mutant.evaluate_expense_report(
            self.pid, self.policy["id"], self.report["id"], H.MEMBER)
        self.assertTrue(view["compliant"])
        self.assertEqual(view["violations"], [])

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = self.blind_mutant()
        mutant_view = mutant.evaluate_expense_report(
            self.pid, self.policy["id"], self.report["id"], H.MEMBER)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_view["compliant"], False)


class TestTierNullPrivacyAndCoreIsolation(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()

    def test_no_tier_baseline_identifier_or_float_anywhere(self):
        policy = self.ext.create_expense_policy(
            self.pid, "t-and-e",
            [{"kind": "category_line_cap", "category": "meals",
              "limit_cents": 5000}], H.MEMBER)
        report = approved_report(self.ext, self.pid, self.emp)
        reimbursement = self.ext.record_reimbursement(
            self.pid, report["id"], "2026-01-20", H.MEMBER)
        surfaces = [
            policy,
            report,
            reimbursement,
            self.ext.get_expense_report(self.pid, report["id"], H.MEMBER),
            self.ext.list_expense_reports(self.pid, H.MEMBER),
            self.ext.list_reimbursements(self.pid, H.MEMBER),
            self.ext.expense_summary(self.pid, PERIOD, H.MEMBER),
            self.ext.evaluate_expense_report(
                self.pid, policy["id"], report["id"], H.MEMBER),
        ]
        for surface in surfaces:
            scan_forbidden(surface)
            # built, not stub: no reference label on this surface
            self.assertNotIn("reference_stub", str(surface))

    def test_full_flow_leaves_core_records_byte_identical(self):
        accrual = H.make_accrual(self.store, self.pid, self.emp)
        before_summary = self.store.program_summary(
            self.pid, PERIOD, H.MEMBER)
        before_accrual = self.store.get_accrual(
            self.pid, accrual["id"], H.MEMBER)
        before_participant = self.store.get_participant(
            self.pid, self.emp, H.MEMBER)
        report = approved_report(self.ext, self.pid, self.emp)
        self.ext.record_reimbursement(
            self.pid, report["id"], "2026-01-20", H.MEMBER)
        self.assertEqual(
            self.store.program_summary(self.pid, PERIOD, H.MEMBER),
            before_summary)
        self.assertEqual(
            self.store.get_accrual(self.pid, accrual["id"], H.MEMBER),
            before_accrual)
        after_participant = self.store.get_participant(
            self.pid, self.emp, H.MEMBER)
        self.assertEqual(after_participant, before_participant)
        self.assertEqual(
            set(after_participant),
            {"id", "program_id", "ref", "kind", "status",
             "created_by", "created_utc"})

    def test_audit_trail_records_extension_actions(self):
        report = approved_report(self.ext, self.pid, self.emp)
        self.ext.record_reimbursement(
            self.pid, report["id"], "2026-01-20", H.MEMBER)
        actions = [e["action"] for e in self.audit.entries()]
        for expected in ("ext_expense_create", "ext_expense_submit",
                         "ext_expense_approve", "ext_reimbursement_record",
                         "ext_expense_reimburse"):
            self.assertIn(expected, actions)


class BoomAudit:
    """An audit sink whose write always fails."""

    def record(self, actor, action, target, details=None):
        raise RuntimeError("audit write failed")


class TestAuditFailureRollsBack(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit,
         self.pid, self.emp) = make_extensions()

    def test_failed_audit_rolls_back_create_and_id(self):
        self.store.audit = BoomAudit()
        with self.assertRaises(RuntimeError):
            make_report(self.ext, self.pid, self.emp)
        self.store.audit = self.audit
        self.assertEqual(
            self.ext.list_expense_reports(self.pid, H.MEMBER), [])
        report = make_report(self.ext, self.pid, self.emp)
        self.assertEqual(report["id"], "exp-1")

    def test_failed_audit_rolls_back_transition(self):
        report = make_report(self.ext, self.pid, self.emp)
        self.store.audit = BoomAudit()
        with self.assertRaises(RuntimeError):
            self.ext.submit_expense_report(self.pid, report["id"], H.MEMBER)
        self.store.audit = self.audit
        view = self.ext.get_expense_report(self.pid, report["id"], H.MEMBER)
        self.assertEqual(view["status"], "draft")


if __name__ == "__main__":
    unittest.main()
