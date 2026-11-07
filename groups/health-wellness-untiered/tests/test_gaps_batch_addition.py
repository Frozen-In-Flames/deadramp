"""Final GAPS batch tests -- second unit: HealthEdge addition.

Pins the addition surface in ``src/health/extensions_addition.py``
(``HealthExtensionsAddition``, wrapping the core ``HealthStore``):
one test class per open GAPS.md entry of the section "No-Signal
Addition -- Health & Wellness Untiered Set (HealthEdge,
FR2700137029)" (see ``../BATCH-ADDITION.md`` for the per-entry
disposition), plus cross-cutting pins -- the category's HARD
PRIVACY RULE over the whole addition surface (no diagnosis /
clinical-note / identifier-shaped key anywhere, and no AMOUNT
key anywhere: adjudication and pricing operate over amounts this
substrate does not hold), this set's tier-null discipline (no
tier/baseline-shaped key anywhere), stub labels
(``reference_stub: True``) on the adjudication, pricing, and
utilization records, derived-never-stored values (adjudication
current outcome and counts, coverage counts by plan reference
and derived status, utilization latest outcome label, report
view counts), member scope, RBAC denials audited with a
``:denied`` suffix under the ``exta_`` prefix, no id consumed by
a failed operation, and the fresh negative control on the
eligibility-binding guard seam ``_check_eligibility_belongs``.

Fixtures: ``make_store()`` (program "Diabetes Care", participant
under opaque ref "carol") plus a second participant (ref "erin").
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError
from health.extensions_addition import HealthExtensionsAddition


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(str(key))
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


def _banned_keys(obj):
    """Keys that would break the founding invariants.

    The HARD PRIVACY RULE (no diagnosis, no clinical free text,
    no direct identifier field in any shape), this set's
    tier-null discipline (no tier/baseline-shaped key), and this
    unit's no-amount rule (no monetary amount field in any
    shape -- the substrate holds nothing a price could be
    computed from or recorded against).
    """
    privacy = {
        "diagnosis", "note", "notes", "clinical_note", "clinical_notes",
        "name", "email", "phone", "ssn", "dob", "date_of_birth",
        "member_number", "address", "first_name", "last_name",
        "insurer", "insurer_name",
        "amount", "amount_cents", "price", "price_cents", "charge",
        "fee", "fee_cents", "allowed_amount", "billed_amount",
    }
    bad = set()
    for key in _all_keys(obj):
        lowered = key.lower()
        if lowered in privacy:
            bad.add(key)
        elif (lowered in ("tier", "cmmc_tier", "baseline",
                          "fedramp_impact_level")
              or lowered.endswith("_tier")):
            bad.add(key)
    return bad


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.participant = make_store()
        self.ext = HealthExtensionsAddition(self.store)
        self.pid = self.participant["id"]
        self.prg = self.program["id"]
        self.other = self.store.create_participant("erin", ADMIN)

    def make_eligibility(self, participant_id=None, plan_ref="plan-ref-1",
                         start="2026-01-01", end=None):
        return self.store.create_eligibility(
            participant_id or self.pid, plan_ref, start, ADMIN,
            coverage_end=end)


class TestAdjudicationReference(AdditionFixture):
    """Entry 972: Health plan claims adjudication & pricing
    engine -- RE-JUDGED to a labeled reference implementation
    (grounds in BATCH-ADDITION.md): registry records of the
    external engine's reported activity; nothing is adjudicated,
    priced, or paid here."""

    def test_pricing_schedule_reference_shape_and_labels(self):
        schedule = self.ext.create_pricing_schedule_reference(
            "schedule-2026", "CY2026 schedule", ADMIN)
        self.assertEqual(schedule["id"], "prs-1")
        self.assertEqual(
            set(schedule.keys()),
            {"id", "schedule_ref", "label", "reference_stub",
             "priced_here", "state", "created_by", "created_utc"})
        self.assertIs(schedule["reference_stub"], True)
        self.assertIs(schedule["priced_here"], False)
        self.assertEqual(schedule["state"], "recorded_reference_only")
        with self.assertRaises(ValidationError):
            self.ext.create_pricing_schedule_reference(
                "schedule-2026", "duplicate", ADMIN)

    def test_adjudication_reference_shape_and_labels(self):
        eligibility = self.make_eligibility()
        reference = self.ext.create_adjudication_reference(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01")
        self.assertEqual(reference["id"], "adj-1")
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["adjudicated_here"], False)
        self.assertIs(reference["priced_here"], False)
        self.assertIs(reference["paid_here"], False)
        self.assertEqual(reference["state"], "recorded_reference_only")
        view = self.ext.get_adjudication_reference(reference["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 0)
        self.assertIsNone(view["current_outcome"])

    def test_outcome_recorded_verbatim_and_current_outcome_derived(self):
        eligibility = self.make_eligibility()
        reference = self.ext.create_adjudication_reference(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01")
        first = self.ext.record_adjudication_outcome(
            reference["id"], "pended", ADMIN, "2026-06-03")
        self.assertEqual(first["id"], "ado-1")
        self.assertIs(first["reference_stub"], True)
        self.ext.record_adjudication_outcome(
            reference["id"], "approved", ADMIN, "2026-06-10")
        view = self.ext.get_adjudication_reference(reference["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["current_outcome"], "approved")
        # The stored reference record itself never gains the
        # derived keys.
        stored = self.ext._adjudication_references[reference["id"]]
        self.assertNotIn("current_outcome", stored)
        self.assertNotIn("outcome_count", stored)

    def test_invalid_outcome_and_unknown_schedule_refused(self):
        eligibility = self.make_eligibility()
        with self.assertRaises(NotFoundError):
            self.ext.create_adjudication_reference(
                self.pid, eligibility["id"], "claim-ref-1", ADMIN,
                "2026-06-01", schedule_id="prs-99")
        reference = self.ext.create_adjudication_reference(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01")
        with self.assertRaises(ValidationError):
            self.ext.record_adjudication_outcome(
                reference["id"], "partially", ADMIN, "2026-06-03")

    def test_cross_participant_eligibility_refused_no_id_consumed(self):
        other_eligibility = self.make_eligibility(
            participant_id=self.other["id"], plan_ref="plan-ref-9")
        with self.assertRaises(ValidationError):
            self.ext.create_adjudication_reference(
                self.pid, other_eligibility["id"], "claim-ref-1", ADMIN,
                "2026-06-01")
        own = self.make_eligibility()
        reference = self.ext.create_adjudication_reference(
            self.pid, own["id"], "claim-ref-1", ADMIN, "2026-06-01")
        self.assertEqual(reference["id"], "adj-1")

    def test_summary_counts_by_current_outcome_no_amounts(self):
        eligibility = self.make_eligibility()
        first = self.ext.create_adjudication_reference(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01")
        self.ext.record_adjudication_outcome(
            first["id"], "approved", ADMIN, "2026-06-05")
        self.ext.create_adjudication_reference(
            self.pid, eligibility["id"], "claim-ref-2", ADMIN, "2026-06-02")
        summary = self.ext.adjudication_summary(ADMIN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["references"], 2)
        self.assertEqual(summary["by_current_outcome"]["approved"], 1)
        self.assertEqual(summary["undecided"], 1)
        self.assertEqual(_banned_keys(summary), set())


class TestBenefitsAdministration(AdditionFixture):
    """Entry 973: Benefits administration platform -- built as
    package definitions held as data, administration records
    bound to the participant's own eligibility records, and a
    summary deriving coverage counts from the core records."""

    def test_package_definition_shape_and_validation(self):
        package = self.ext.create_benefit_package(
            "pkg-standard", "Standard package", ["comp-a", "comp-b"], ADMIN)
        self.assertEqual(package["id"], "bpk-1")
        self.assertEqual(package["component_refs"], ["comp-a", "comp-b"])
        with self.assertRaises(ValidationError):
            self.ext.create_benefit_package(
                "pkg-standard", "duplicate ref", ["comp-a"], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_benefit_package(
                "pkg-dup", "dup components", ["comp-a", "comp-a"], ADMIN)

    def test_administration_record_bound_to_own_eligibility(self):
        package = self.ext.create_benefit_package(
            "pkg-standard", "Standard package", ["comp-a"], ADMIN)
        eligibility = self.make_eligibility()
        record = self.ext.record_benefit_administration(
            self.pid, eligibility["id"], package["id"],
            "enrollment_processed", ADMIN, "2026-06-01")
        self.assertEqual(record["id"], "bad-1")
        self.assertEqual(record["action_label"], "enrollment_processed")
        records = self.ext.list_benefit_administrations(
            ADMIN, participant_id=self.pid)
        self.assertEqual([r["id"] for r in records], ["bad-1"])

    def test_cross_participant_eligibility_refused_no_id_consumed(self):
        package = self.ext.create_benefit_package(
            "pkg-standard", "Standard package", ["comp-a"], ADMIN)
        other_eligibility = self.make_eligibility(
            participant_id=self.other["id"], plan_ref="plan-ref-9")
        with self.assertRaises(ValidationError):
            self.ext.record_benefit_administration(
                self.pid, other_eligibility["id"], package["id"],
                "enrollment_processed", ADMIN, "2026-06-01")
        own = self.make_eligibility()
        record = self.ext.record_benefit_administration(
            self.pid, own["id"], package["id"], "enrollment_processed",
            ADMIN, "2026-06-01")
        self.assertEqual(record["id"], "bad-1")

    def test_summary_derives_coverage_counts_from_core_records(self):
        self.ext.create_benefit_package(
            "pkg-standard", "Standard package", ["comp-a"], ADMIN)
        self.make_eligibility()  # carol, plan-ref-1, current
        self.make_eligibility(participant_id=self.other["id"],
                              plan_ref="plan-ref-2", end="2026-03-01")
        self.make_eligibility(participant_id=self.other["id"],
                              plan_ref="plan-ref-1", start="2027-01-01")
        summary = self.ext.benefits_administration_summary(
            ADMIN, as_of="2026-06-01")
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["packages"], 1)
        self.assertEqual(summary["administration_records"], 0)
        self.assertEqual(summary["coverage_records"], 3)
        self.assertEqual(summary["coverage_by_plan_ref"],
                         {"plan-ref-1": 2, "plan-ref-2": 1})
        self.assertEqual(summary["coverage_by_derived_status"],
                         {"upcoming": 1, "current": 1, "ended": 1})


class TestUtilizationWorkflows(AdditionFixture):
    """Entry 974: Care & utilization management workflows for
    health plans -- labeled reference implementation, as
    drafted: definitions held as data and never executed; cases
    and outcomes recorded as reported."""

    def test_definition_shape_and_labels(self):
        definition = self.ext.create_utilization_workflow_definition(
            "um-prior-auth", ["step-intake", "step-review"], ADMIN)
        self.assertEqual(definition["id"], "uwd-1")
        self.assertIs(definition["reference_stub"], True)
        self.assertIs(definition["executed_here"], False)
        self.assertEqual(definition["state"], "recorded_reference_only")

    def test_case_and_outcome_records_with_derived_latest_label(self):
        definition = self.ext.create_utilization_workflow_definition(
            "um-prior-auth", ["step-intake"], ADMIN)
        case = self.ext.record_utilization_case(
            definition["id"], self.pid, "case-ref-1", CLINICIAN,
            "2026-06-01")
        self.assertEqual(case["id"], "umc-1")
        self.assertIs(case["reviewed_here"], False)
        self.assertIs(case["determined_here"], False)
        self.ext.record_utilization_outcome(
            case["id"], "more_information_requested", CLINICIAN,
            "2026-06-03")
        self.ext.record_utilization_outcome(
            case["id"], "authorized_as_reported", CLINICIAN, "2026-06-07")
        view = self.ext.get_utilization_case(case["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"],
                         "authorized_as_reported")
        stored = self.ext._utilization_cases[case["id"]]
        self.assertNotIn("latest_outcome_label", stored)

    def test_summary_is_counts_only(self):
        definition = self.ext.create_utilization_workflow_definition(
            "um-prior-auth", ["step-intake"], ADMIN)
        case = self.ext.record_utilization_case(
            definition["id"], self.pid, "case-ref-1", CLINICIAN,
            "2026-06-01")
        self.ext.record_utilization_outcome(
            case["id"], "authorized_as_reported", CLINICIAN, "2026-06-07")
        summary = self.ext.utilization_summary(ADMIN)
        self.assertEqual(
            summary,
            {"method": "deterministic_counts", "definitions": 1,
             "cases": 1, "outcomes": 1})


class TestRegulatoryReporting(AdditionFixture):
    """Entry 975: Regulatory compliance reporting engine for
    payers -- built as definitions, filing records, and a view
    deriving counts over the substrate's own records; explicitly
    not a control claim."""

    def test_definition_and_filing_shapes(self):
        definition = self.ext.create_report_definition(
            "report-quarterly", "Quarterly payer report", "plan-operations",
            ADMIN)
        self.assertEqual(definition["id"], "rpd-1")
        filing = self.ext.record_report_filing(
            definition["id"], "filing-q1", "submitted_as_reported",
            CLINICIAN, "2026-04-15")
        self.assertEqual(filing["id"], "rfl-1")
        self.assertIs(filing["filed_here"], False)
        self.assertIs(filing["submitted_here"], False)
        self.assertEqual(filing["status_label"], "submitted_as_reported")

    def test_report_view_derives_counts_over_core_records(self):
        definition = self.ext.create_report_definition(
            "report-quarterly", "Quarterly payer report", "plan-operations",
            ADMIN)
        self.store.create_enrollment(self.pid, self.prg, CLINICIAN)
        self.make_eligibility()
        self.make_eligibility(participant_id=self.other["id"],
                              plan_ref="plan-ref-2", end="2026-03-01")
        self.ext.record_report_filing(
            definition["id"], "filing-q1", "prepared_as_reported",
            CLINICIAN, "2026-04-15")
        self.ext.record_report_filing(
            definition["id"], "filing-q2", "submitted_as_reported",
            CLINICIAN, "2026-07-15")
        view = self.ext.regulatory_report_view(
            definition["id"], ADMIN, as_of="2026-06-01")
        self.assertEqual(view["method"], "deterministic_counts")
        self.assertEqual(view["basis"], "substrate_records_only")
        self.assertEqual(view["participants"], 2)
        self.assertEqual(view["enrollments"], 1)
        self.assertEqual(view["coverage_records"], 2)
        self.assertEqual(view["coverage_by_derived_status"],
                         {"upcoming": 0, "current": 1, "ended": 1})
        self.assertEqual(view["filings"], 2)
        self.assertEqual(view["latest_filing_status_label"],
                         "submitted_as_reported")

    def test_report_view_asserts_no_control_family(self):
        definition = self.ext.create_report_definition(
            "report-quarterly", "Quarterly payer report", "plan-operations",
            ADMIN)
        view = self.ext.regulatory_report_view(definition["id"], ADMIN)
        for key in _all_keys(view):
            self.assertNotIn("control", key.lower())
            self.assertNotIn("framework", key.lower())
        self.assertEqual(_banned_keys(view), set())


class _NoBindingGuardAddition(HealthExtensionsAddition):
    """Mutant: the eligibility-binding guard never fires."""

    def _check_eligibility_belongs(self, participant_id, eligibility):
        return None


class TestEligibilityBindingNegativeControl(AdditionFixture):
    """Fresh negative control for the new code: a payer-side
    record may bind only to a core eligibility record of the
    SAME participant it names."""

    def test_canonical_refuses_cross_participant_binding(self):
        other_eligibility = self.make_eligibility(
            participant_id=self.other["id"], plan_ref="plan-ref-9")
        with self.assertRaises(ValidationError):
            self.ext.create_adjudication_reference(
                self.pid, other_eligibility["id"], "claim-ref-1", ADMIN,
                "2026-06-01")

    def test_mutant_binds_across_participants(self):
        mutant = _NoBindingGuardAddition(self.store)
        other_eligibility = self.make_eligibility(
            participant_id=self.other["id"], plan_ref="plan-ref-9")
        record = mutant.create_adjudication_reference(
            self.pid, other_eligibility["id"], "claim-ref-1", ADMIN,
            "2026-06-01")
        self.assertEqual(record["participant_id"], self.pid)
        self.assertEqual(record["eligibility_id"], other_eligibility["id"])

    def test_treating_mutant_outcome_as_expected_fails(self):
        mutant = _NoBindingGuardAddition(self.store)
        other_eligibility = self.make_eligibility(
            participant_id=self.other["id"], plan_ref="plan-ref-9")
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                mutant.create_adjudication_reference(
                    self.pid, other_eligibility["id"], "claim-ref-1",
                    ADMIN, "2026-06-01")


class TestAdditionCrossCutting(AdditionFixture):
    """Cross-cutting pins over the whole addition surface."""

    def _exercise_surface(self):
        out = []
        schedule = self.ext.create_pricing_schedule_reference(
            "schedule-2026", "CY2026 schedule", ADMIN)
        out.append(schedule)
        out.append(self.ext.list_pricing_schedule_references(ADMIN))
        eligibility = self.make_eligibility()
        reference = self.ext.create_adjudication_reference(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01",
            schedule_id=schedule["id"])
        out.append(reference)
        out.append(self.ext.record_adjudication_outcome(
            reference["id"], "approved", ADMIN, "2026-06-05"))
        out.append(self.ext.get_adjudication_reference(reference["id"], ADMIN))
        out.append(self.ext.adjudication_summary(ADMIN))
        package = self.ext.create_benefit_package(
            "pkg-standard", "Standard package", ["comp-a"], ADMIN)
        out.append(package)
        out.append(self.ext.record_benefit_administration(
            self.pid, eligibility["id"], package["id"],
            "enrollment_processed", ADMIN, "2026-06-01"))
        out.append(self.ext.benefits_administration_summary(
            ADMIN, as_of="2026-06-01"))
        definition = self.ext.create_utilization_workflow_definition(
            "um-prior-auth", ["step-intake"], ADMIN)
        out.append(definition)
        case = self.ext.record_utilization_case(
            definition["id"], self.pid, "case-ref-1", CLINICIAN,
            "2026-06-01")
        out.append(case)
        out.append(self.ext.record_utilization_outcome(
            case["id"], "authorized_as_reported", CLINICIAN, "2026-06-07"))
        out.append(self.ext.get_utilization_case(case["id"], ADMIN))
        out.append(self.ext.utilization_summary(ADMIN))
        report = self.ext.create_report_definition(
            "report-quarterly", "Quarterly payer report", "plan-operations",
            ADMIN)
        out.append(report)
        out.append(self.ext.record_report_filing(
            report["id"], "filing-q1", "submitted_as_reported", CLINICIAN,
            "2026-04-15"))
        out.append(self.ext.regulatory_report_view(
            report["id"], ADMIN, as_of="2026-06-01"))
        return out

    def test_no_privacy_tier_or_amount_key_anywhere_on_surface(self):
        for value in self._exercise_surface():
            self.assertEqual(_banned_keys(value), set())

    def test_forbidden_field_cannot_be_represented(self):
        with self.assertRaises(TypeError):
            self.ext.create_benefit_package(
                "pkg-x", "Title", ["comp-a"], ADMIN, diagnosis="smuggled")
        with self.assertRaises(TypeError):
            self.ext.create_adjudication_reference(
                self.pid, "elg-1", "claim-x", ADMIN, "2026-06-01",
                amount=100)
        with self.assertRaises(TypeError):
            self.ext.record_utilization_case(
                "uwd-1", self.pid, "case-x", CLINICIAN, "2026-06-01",
                note="smuggled")

    def test_member_scope_on_addition_records(self):
        eligibility = self.make_eligibility(
            participant_id=self.other["id"], plan_ref="plan-ref-9")
        reference = self.ext.create_adjudication_reference(
            self.other["id"], eligibility["id"], "claim-ref-1", ADMIN,
            "2026-06-01")
        with self.assertRaises(PermissionDenied):
            self.ext.get_adjudication_reference(reference["id"], MEMBER)
        self.assertEqual(self.ext.list_adjudication_references(MEMBER), [])

    def test_member_write_denied_and_audited(self):
        audit = self.store.audit
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            self.ext.create_benefit_package(
                "pkg-x", "Title", ["comp-a"], MEMBER)
        entries = audit.entries()[before:]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"],
                         "exta_benefit_package_create:denied")
        self.assertEqual(entries[0]["actor"], "carol")

    def test_auditor_cannot_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_report_definition(
                "report-x", "Title", "scope", AUDITOR)

    def test_addition_mutations_use_exta_prefixed_audit_actions(self):
        self.ext.create_pricing_schedule_reference(
            "schedule-2026", "CY2026 schedule", ADMIN)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_pricing_schedule_create", actions)

    def test_unknown_records_raise_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.get_adjudication_reference("adj-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.get_utilization_case("umc-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.regulatory_report_view("rpd-99", ADMIN)


if __name__ == "__main__":
    unittest.main()
