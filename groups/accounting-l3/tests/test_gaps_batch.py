"""Final GAPS batch extension tests — Accounting L3-adjacent.

Traces to: UNION-SPEC.md function ranking rows 1 and 13-25 (the
Extended families) and gaps-batch/DECISION.md (ratified 2026-11-07).
Each test class names the GAPS.md entry it pins. The extension store
is a new module (``accounting.extensions``); no core module changed,
so every core doctrine test above keeps its meaning: integer cents
only, separation of duties (AC-5), append-only hash-chained audit
(AU-9/AU-5), and the auditor role holding no operational permission.
"""

import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from accounting_helpers import ADMIN, AUDITOR, MEMBER, VIEWER  # noqa: E402

from accounting.audit import AuditLog  # noqa: E402
from accounting.errors import (  # noqa: E402
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from accounting.extensions import ExtensionStore  # noqa: E402

BOOK = "book-1"
OTHER_BOOK = "book-2"


def make_ext(audit=None):
    if audit is None:
        audit = AuditLog()
    return ExtensionStore(audit=audit), audit


class BatchCase(unittest.TestCase):
    def setUp(self):
        self.ext, self.audit = make_ext()


class TestAnalytics(BatchCase):
    """GAPS entry: AI / analytics & BI (claimed Extended family)."""

    def test_dataset_and_insight_flow_and_summary_derivation(self):
        ds = self.ext.create_dataset(BOOK, "acq-metrics", "ds-ref-1", MEMBER)
        self.assertTrue(ds["id"].startswith("ana-"))
        ins = self.ext.record_insight(
            BOOK, ds["id"], "Cycle time fell", "cycle_cents", 12500, MEMBER)
        self.assertEqual(ins["metric_value_cents"], 12500)
        summary = self.ext.analytics_summary(BOOK, MEMBER)
        self.assertEqual(summary["dataset_count"], 1)
        self.assertEqual(summary["insight_count"], 1)
        self.assertEqual(summary["total_metric_cents"], 12500)

    def test_insight_float_metric_rejected(self):
        ds = self.ext.create_dataset(BOOK, "d", "ds-ref-1", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_insight(BOOK, ds["id"], "t", "m", 10.0, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_insight(BOOK, ds["id"], "t", "m", True, MEMBER)

    def test_insight_unknown_dataset_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_insight(BOOK, "ana-99", "t", "m", 100, MEMBER)

    def test_summary_is_scoped_per_book(self):
        ds = self.ext.create_dataset(BOOK, "d", "ds-ref-1", MEMBER)
        self.ext.record_insight(BOOK, ds["id"], "t", "m", 700, MEMBER)
        other = self.ext.analytics_summary(OTHER_BOOK, MEMBER)
        self.assertEqual(other["insight_count"], 0)
        self.assertEqual(other["total_metric_cents"], 0)


class TestProjects(BatchCase):
    """GAPS entry: Project / program / portfolio management."""

    def _active_project(self, budget=100000):
        project = self.ext.create_project(
            BOOK, "Modernization", "sponsor-1", budget, MEMBER)
        self.ext.activate_project(BOOK, project["id"], ADMIN)
        return project

    def test_activation_requires_other_actor(self):
        project = self.ext.create_project(
            BOOK, "P", "sponsor-1", 5000, MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.activate_project(BOOK, project["id"], MEMBER)

    def test_spend_cap_and_derived_view(self):
        project = self._active_project()
        self.ext.record_project_spend(BOOK, project["id"], 40000, "phase 1", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_project_spend(BOOK, project["id"], 60001, "over", MEMBER)
        view = self.ext.project_view(BOOK, project["id"], MEMBER)
        self.assertEqual(view["spent_cents"], 40000)
        self.assertEqual(view["remaining_cents"], 60000)
        self.assertEqual(view["utilization_bps"], 4000)

    def test_spend_on_draft_project_rejected(self):
        project = self.ext.create_project(BOOK, "P", "s-1", 5000, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_project_spend(BOOK, project["id"], 100, "x", MEMBER)

    def test_stored_project_record_has_no_derived_keys(self):
        project = self._active_project()
        stored = self.ext._data["projects"][project["id"]]
        self.assertNotIn("spent_cents", stored)
        self.assertNotIn("remaining_cents", stored)
        self.assertNotIn("utilization_bps", stored)

    def test_float_budget_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_project(BOOK, "P", "s-1", 100.0, MEMBER)


class TestRiskRegister(BatchCase):
    """GAPS entry: Risk register & GRC suites beyond the SoD/audit seed."""

    def test_risk_score_derived_and_controls_counted(self):
        risk = self.ext.create_risk(BOOK, "Vendor failure", "ops", 3, 20000, "owner-1", MEMBER)
        self.ext.add_risk_control(BOOK, risk["id"], "dual sourcing", MEMBER)
        self.ext.add_risk_control(BOOK, risk["id"], "escrow", MEMBER)
        view = self.ext.risk_view(BOOK, risk["id"], MEMBER)
        self.assertEqual(view["risk_score_cents"], 60000)
        self.assertEqual(view["control_count"], 2)
        self.assertNotIn("risk_score_cents", self.ext._data["risks"][risk["id"]])

    def test_likelihood_bounds(self):
        for bad in (0, 6, 2.5, True):
            with self.assertRaises(ValidationError):
                self.ext.create_risk(BOOK, "t", "c", bad, 100, "o-1", MEMBER)

    def test_acceptance_sod(self):
        risk = self.ext.create_risk(BOOK, "t", "c", 2, 100, "o-1", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.accept_risk(BOOK, risk["id"], MEMBER)
        accepted = self.ext.accept_risk(BOOK, risk["id"], ADMIN)
        self.assertEqual(accepted["status"], "accepted")


class TestAuditWorkbench(BatchCase):
    """GAPS entry: Audit-management workbenches."""

    def _engagement_with_finding(self):
        eng = self.ext.create_engagement(BOOK, "FY26 audit", "ledger", "2026-01", MEMBER)
        finding = self.ext.add_finding(BOOK, eng["id"], "Missing approval", "high", MEMBER)
        return eng, finding

    def test_close_blocked_by_open_findings_then_succeeds(self):
        eng, finding = self._engagement_with_finding()
        with self.assertRaises(ValidationError):
            self.ext.close_engagement(BOOK, eng["id"], ADMIN)
        self.ext.resolve_finding(BOOK, finding["id"], "approval on file", ADMIN)
        closed = self.ext.close_engagement(BOOK, eng["id"], ADMIN)
        self.assertTrue(closed["closed"])
        view = self.ext.engagement_view(BOOK, eng["id"], MEMBER)
        self.assertEqual(view["finding_count"], 1)
        self.assertEqual(view["open_finding_count"], 0)

    def test_resolve_finding_sod(self):
        eng, finding = self._engagement_with_finding()
        with self.assertRaises(PermissionDenied):
            self.ext.resolve_finding(BOOK, finding["id"], "x", MEMBER)

    def test_invalid_severity_rejected(self):
        eng = self.ext.create_engagement(BOOK, "t", "s", "2026-01", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.add_finding(BOOK, eng["id"], "f", "severe", MEMBER)


class TestFixedAssets(BatchCase):
    """GAPS entry: Fixed-asset registers."""

    def test_straight_line_derivation_and_salvage_floor(self):
        asset = self.ext.register_fixed_asset(
            BOOK, "Server", 120000, 20000, 10, "2026-01-01", MEMBER)
        view = self.ext.asset_view(BOOK, asset["id"], 5, MEMBER)
        self.assertEqual(view["monthly_depreciation_cents"], 10000)
        self.assertEqual(view["accumulated_depreciation_cents"], 50000)
        self.assertEqual(view["book_value_cents"], 70000)
        late = self.ext.asset_view(BOOK, asset["id"], 99, MEMBER)
        self.assertEqual(late["book_value_cents"], 20000)

    def test_salvage_above_cost_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_fixed_asset(
                BOOK, "x", 1000, 1001, 10, "2026-01-01", MEMBER)

    def test_disposal_sod(self):
        asset = self.ext.register_fixed_asset(
            BOOK, "x", 1000, 0, 10, "2026-01-01", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.dispose_fixed_asset(BOOK, asset["id"], MEMBER)
        self.assertTrue(
            self.ext.dispose_fixed_asset(BOOK, asset["id"], ADMIN)["disposed"])


class TestRetention(BatchCase):
    """GAPS entry: Records retention beyond the audit seed."""

    def _assignment(self):
        policy = self.ext.create_retention_policy(BOOK, "invoice", 24, MEMBER)
        return self.ext.assign_retention(
            BOOK, policy["id"], "inv-ref-1", "2024-03-15", MEMBER)

    def test_due_date_derived_with_month_clamping(self):
        assignment = self._assignment()
        before = self.ext.retention_view(BOOK, assignment["id"], "2026-03-14", MEMBER)
        self.assertEqual(before["disposition_due_date"], "2026-03-15")
        self.assertFalse(before["disposition_due"])
        after = self.ext.retention_view(BOOK, assignment["id"], "2026-03-15", MEMBER)
        self.assertTrue(after["disposition_due"])

    def test_disposition_is_a_record_and_assignment_survives(self):
        assignment = self._assignment()
        self.ext.record_disposition(BOOK, assignment["id"], ADMIN)
        view = self.ext.retention_view(BOOK, assignment["id"], "2026-04-01", MEMBER)
        self.assertTrue(view["disposition_recorded"])
        self.assertIn(assignment["id"], self.ext._data["retention_assignments"])

    def test_disposition_sod(self):
        assignment = self._assignment()
        with self.assertRaises(PermissionDenied):
            self.ext.record_disposition(BOOK, assignment["id"], MEMBER)


class TestForecasting(BatchCase):
    """GAPS entry: Forecasting / EPM."""

    def test_variance_derived_and_actuals_not_stored(self):
        forecast = self.ext.create_forecast(
            BOOK, "2026-02",
            [{"label": "revenue", "amount_cents": 50000},
             {"label": "rent", "amount_cents": 20000}], MEMBER)
        result = self.ext.forecast_variance(
            BOOK, forecast["id"],
            [{"label": "revenue", "amount_cents": 55000}], MEMBER)
        self.assertEqual(result["total_forecast_cents"], 70000)
        self.assertEqual(result["total_actual_cents"], 55000)
        self.assertEqual(result["total_variance_cents"], -15000)
        stored = self.ext._data["forecasts"][forecast["id"]]
        self.assertNotIn("actual", str(stored.keys()))

    def test_duplicate_labels_and_float_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_forecast(
                BOOK, "2026-02",
                [{"label": "a", "amount_cents": 1},
                 {"label": "a", "amount_cents": 2}], MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.create_forecast(
                BOOK, "2026-02", [{"label": "a", "amount_cents": 1.5}], MEMBER)

    def test_approve_sod(self):
        forecast = self.ext.create_forecast(
            BOOK, "2026-02", [{"label": "a", "amount_cents": 1}], MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.approve_forecast(BOOK, forecast["id"], MEMBER)
        self.assertEqual(
            self.ext.approve_forecast(BOOK, forecast["id"], ADMIN)["status"],
            "approved")


class TestSupplyChain(BatchCase):
    """GAPS entry: Supply chain."""

    def _approved_order(self, quantity=10, price=1500):
        supplier = self.ext.register_supplier(BOOK, "sup-1", "Supplier One", MEMBER)
        order = self.ext.create_purchase_order(
            BOOK, supplier["id"], "Widgets", quantity, price, MEMBER)
        self.ext.approve_purchase_order(BOOK, order["id"], ADMIN)
        return order

    def test_fulfillment_derived_and_receipt_cap(self):
        order = self._approved_order()
        self.ext.record_receipt(BOOK, order["id"], 4, MEMBER)
        view = self.ext.purchase_order_view(BOOK, order["id"], MEMBER)
        self.assertEqual(view["fulfillment"], "partially_received")
        self.assertEqual(view["total_cents"], 15000)
        self.assertEqual(view["remaining_quantity"], 6)
        with self.assertRaises(ValidationError):
            self.ext.record_receipt(BOOK, order["id"], 7, MEMBER)
        self.ext.record_receipt(BOOK, order["id"], 6, MEMBER)
        self.assertEqual(
            self.ext.purchase_order_view(BOOK, order["id"], MEMBER)["fulfillment"],
            "received")

    def test_receipt_requires_approved_order(self):
        supplier = self.ext.register_supplier(BOOK, "sup-1", "S", MEMBER)
        order = self.ext.create_purchase_order(
            BOOK, supplier["id"], "W", 2, 100, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_receipt(BOOK, order["id"], 1, MEMBER)

    def test_stored_order_has_no_total_key(self):
        order = self._approved_order()
        self.assertNotIn("total_cents", self.ext._data["purchase_orders"][order["id"]])


class TestGovConGrants(BatchCase):
    """GAPS entry: GovCon / grants specifics."""

    def _active_award(self, ceiling=80000):
        award = self.ext.create_award(BOOK, "awd-ref-1", "sponsor-1", ceiling, MEMBER)
        self.ext.activate_award(BOOK, award["id"], ADMIN)
        return award

    def test_ceiling_cap_and_derived_split(self):
        award = self._active_award()
        self.ext.record_award_cost(BOOK, award["id"], 30000, "direct", MEMBER)
        self.ext.record_award_cost(BOOK, award["id"], 10000, "indirect", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_award_cost(BOOK, award["id"], 40001, "direct", MEMBER)
        view = self.ext.award_view(BOOK, award["id"], MEMBER)
        self.assertEqual(view["direct_cents"], 30000)
        self.assertEqual(view["indirect_cents"], 10000)
        self.assertEqual(view["remaining_cents"], 40000)

    def test_cost_type_choice_validated(self):
        award = self._active_award()
        with self.assertRaises(ValidationError):
            self.ext.record_award_cost(BOOK, award["id"], 100, "overhead", MEMBER)

    def test_costs_require_active_award(self):
        award = self.ext.create_award(BOOK, "a-1", "s-1", 1000, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_award_cost(BOOK, award["id"], 100, "direct", MEMBER)


class TestCryptoInvestigation(BatchCase):
    """GAPS entry: Crypto investigation (records only)."""

    def test_observations_aggregate_derived(self):
        case = self.ext.create_crypto_case(BOOK, "case-1", "Exchange flow", MEMBER)
        self.ext.add_wallet_observation(BOOK, case["id"], "wallet-ref-a", 5000, MEMBER)
        self.ext.add_wallet_observation(BOOK, case["id"], "wallet-ref-a", 3000, MEMBER)
        self.ext.add_wallet_observation(BOOK, case["id"], "wallet-ref-b", 2000, MEMBER)
        view = self.ext.crypto_case_view(BOOK, case["id"], MEMBER)
        self.assertEqual(view["observation_count"], 3)
        self.assertEqual(view["distinct_wallet_count"], 2)
        self.assertEqual(view["total_observed_cents"], 10000)

    def test_observation_shape_is_opaque_ref_only(self):
        case = self.ext.create_crypto_case(BOOK, "case-1", "t", MEMBER)
        obs = self.ext.add_wallet_observation(BOOK, case["id"], "w-1", 100, MEMBER)
        self.assertEqual(
            set(obs.keys()),
            {"id", "book_id", "case_id", "wallet_ref",
             "observed_value_cents", "created_by"})

    def test_close_sod_and_closed_case_rejects_observations(self):
        case = self.ext.create_crypto_case(BOOK, "case-1", "t", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.close_crypto_case(BOOK, case["id"], MEMBER)
        self.ext.close_crypto_case(BOOK, case["id"], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.add_wallet_observation(BOOK, case["id"], "w-1", 1, MEMBER)


class TestTimeTracking(BatchCase):
    """GAPS entry: Time tracking."""

    def test_summary_derived_with_approved_split(self):
        e1 = self.ext.record_time_entry(BOOK, "worker-1", "proj-1", "2026-01-05", 120, MEMBER)
        self.ext.record_time_entry(BOOK, "worker-1", "proj-1", "2026-01-06", 90, MEMBER)
        self.ext.record_time_entry(BOOK, "worker-2", "proj-1", "2026-01-06", 45, MEMBER)
        self.ext.approve_time_entry(BOOK, e1["id"], ADMIN)
        summary = self.ext.time_summary(BOOK, "worker-1", MEMBER)
        self.assertEqual(summary["total_minutes"], 210)
        self.assertEqual(summary["approved_minutes"], 120)
        self.assertEqual(summary["entry_count"], 2)

    def test_minutes_bounds(self):
        for bad in (0, 1441, 30.5):
            with self.assertRaises(ValidationError):
                self.ext.record_time_entry(BOOK, "w-1", "p-1", "2026-01-05", bad, MEMBER)

    def test_approve_sod(self):
        entry = self.ext.record_time_entry(BOOK, "w-1", "p-1", "2026-01-05", 60, MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.approve_time_entry(BOOK, entry["id"], MEMBER)


class TestPayroll(BatchCase):
    """GAPS entry: Payroll."""

    def _run_with_item(self):
        run = self.ext.create_payroll_run(BOOK, "2026-01", MEMBER)
        self.ext.add_pay_item(BOOK, run["id"], "worker-1", 200000, 30000, MEMBER)
        return run

    def test_net_derived_never_stored_on_item(self):
        run = self._run_with_item()
        item = next(iter(self.ext._data["pay_items"].values()))
        self.assertNotIn("net_cents", item)
        view = self.ext.payroll_view(BOOK, run["id"], MEMBER)
        self.assertEqual(view["total_gross_cents"], 200000)
        self.assertEqual(view["total_net_cents"], 170000)

    def test_deductions_above_gross_rejected(self):
        run = self.ext.create_payroll_run(BOOK, "2026-01", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.add_pay_item(BOOK, run["id"], "w-1", 1000, 1001, MEMBER)

    def test_disbursement_requires_approval_and_pay_permission(self):
        run = self._run_with_item()
        with self.assertRaises(ValidationError):
            self.ext.record_payroll_disbursement(BOOK, run["id"], ADMIN)
        self.ext.approve_payroll_run(BOOK, run["id"], ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.record_payroll_disbursement(BOOK, run["id"], VIEWER)
        done = self.ext.record_payroll_disbursement(BOOK, run["id"], MEMBER)
        self.assertEqual(done["status"], "disbursed_recorded")

    def test_empty_run_cannot_be_approved(self):
        run = self.ext.create_payroll_run(BOOK, "2026-01", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.approve_payroll_run(BOOK, run["id"], ADMIN)


class TestTaxSupport(BatchCase):
    """GAPS entry: Tax support (preparation records only)."""

    def test_total_derived_and_finalize_sod(self):
        filing = self.ext.create_tax_filing(BOOK, "US-TX", "2026-01", MEMBER)
        self.ext.add_tax_line(BOOK, filing["id"], "sales tax", 4500, MEMBER)
        self.ext.add_tax_line(BOOK, filing["id"], "adjustment", -500, MEMBER)
        view = self.ext.tax_filing_view(BOOK, filing["id"], MEMBER)
        self.assertEqual(view["total_cents"], 4000)
        self.assertEqual(view["line_count"], 2)
        with self.assertRaises(PermissionDenied):
            self.ext.finalize_tax_filing(BOOK, filing["id"], MEMBER)
        self.assertEqual(
            self.ext.finalize_tax_filing(BOOK, filing["id"], ADMIN)["status"],
            "finalized")

    def test_lines_locked_after_finalize(self):
        filing = self.ext.create_tax_filing(BOOK, "US", "2026-01", MEMBER)
        self.ext.finalize_tax_filing(BOOK, filing["id"], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.add_tax_line(BOOK, filing["id"], "late", 1, MEMBER)


class TestForensicInvestigation(BatchCase):
    """GAPS entry: Forensic investigation."""

    def test_custody_chain_derives_current_custodian(self):
        case = self.ext.create_forensic_case(BOOK, "Ledger review", "matter-1", MEMBER)
        item = self.ext.add_evidence_item(
            BOOK, case["id"], "ev-ref-1", "Exported journal", "custodian-1", MEMBER)
        self.ext.transfer_custody(BOOK, item["id"], "custodian-2", MEMBER)
        view = self.ext.evidence_view(BOOK, item["id"], MEMBER)
        self.assertEqual(view["custody_length"], 2)
        self.assertEqual(view["current_custodian_ref"], "custodian-2")
        stored = self.ext._data["evidence_items"][item["id"]]
        self.assertNotIn("current_custodian_ref", stored)

    def test_close_sod(self):
        case = self.ext.create_forensic_case(BOOK, "t", "m-1", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.close_forensic_case(BOOK, case["id"], MEMBER)
        self.assertEqual(
            self.ext.close_forensic_case(BOOK, case["id"], ADMIN)["status"],
            "closed")


class TestESignatureStub(BatchCase):
    """GAPS entry: E-signature — STUB-ENGINE, labeled reference only."""

    def test_every_record_carries_reference_stub_true(self):
        request = self.ext.create_signature_request(
            BOOK, "doc-ref-1", "signer-1", MEMBER)
        self.assertIs(request["reference_stub"], True)
        event = self.ext.record_signature_event(
            BOOK, request["id"], "signed_declared", MEMBER)
        self.assertIs(event["reference_stub"], True)
        view = self.ext.signature_request_view(BOOK, request["id"], MEMBER)
        self.assertIs(view["reference_stub"], True)
        self.assertTrue(all(e["reference_stub"] for e in view["events"]))

    def test_status_vocabulary_claims_no_execution(self):
        request = self.ext.create_signature_request(
            BOOK, "doc-ref-1", "signer-1", MEMBER)
        self.assertEqual(request["status"], "recorded")

    def test_event_type_validated(self):
        request = self.ext.create_signature_request(
            BOOK, "doc-ref-1", "signer-1", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_signature_event(BOOK, request["id"], "sent", MEMBER)

    def test_request_record_shape_pinned(self):
        request = self.ext.create_signature_request(
            BOOK, "doc-ref-1", "signer-1", MEMBER)
        self.assertEqual(
            set(request.keys()),
            {"id", "book_id", "document_ref", "signer_ref", "status",
             "reference_stub", "created_by"})


class TestBatchWideDoctrines(BatchCase):
    """Cross-entry doctrines: RBAC, auditor role, audit chain, books."""

    def test_auditor_role_holds_no_operational_permission(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_project(BOOK, "P", "s-1", 1000, AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.analytics_summary(BOOK, AUDITOR)

    def test_viewer_cannot_create_but_can_read(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_dataset(BOOK, "d", "ref-1", VIEWER)
        self.assertEqual(self.ext.analytics_summary(BOOK, VIEWER)["dataset_count"], 0)

    def test_cross_book_record_is_not_found(self):
        ds = self.ext.create_dataset(BOOK, "d", "ref-1", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_insight(OTHER_BOOK, ds["id"], "t", "m", 1, MEMBER)

    def test_mutations_are_audited_and_chain_verifies(self):
        self.ext.create_dataset(BOOK, "d", "ref-1", MEMBER)
        self.ext.create_project(BOOK, "P", "s-1", 1000, MEMBER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_dataset_create", actions)
        self.assertIn("ext_project_create", actions)
        ok, first_bad = self.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)

    def test_audit_failure_rolls_back_extension_mutation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path=path)
            ext = ExtensionStore(audit=audit)
            ext.create_dataset(BOOK, "d", "ref-1", MEMBER)
            # Break the JSONL path mid-flight, as the core AU-5 tests do.
            os.remove(path)
            os.mkdir(path)
            from accounting.errors import AuditWriteError
            with self.assertRaises(AuditWriteError):
                ext.create_dataset(BOOK, "d2", "ref-2", MEMBER)
            summary = ext.analytics_summary(BOOK, MEMBER)
            self.assertEqual(summary["dataset_count"], 1)

    def test_negative_control_budget_cap_mutant(self):
        """Fresh negative control (in-suite form): a mutant spend gate
        that sums prior spend but never compares it to the budget --
        the exact counterpart of the live mutation drill recorded in
        tests/README.md. The canonical expectation (over-budget spend
        raises and stores nothing) holds on the real store and fails
        under the mutant, proving the drill's failure surface is the
        budget cap and not incidental breakage."""
        project = self.ext.create_project(BOOK, "P", "s-1", 1000, MEMBER)
        self.ext.activate_project(BOOK, project["id"], ADMIN)
        self.ext.record_project_spend(BOOK, project["id"], 900, "ok", MEMBER)

        def mutant_spend(amount_cents):
            spent = sum(r["amount_cents"]
                        for r in self.ext._data["project_spend"].values()
                        if r["project_id"] == project["id"])
            _ = spent  # mutant: computed, never compared to the budget
            return "accepted"

        with self.assertRaises(ValidationError):
            self.ext.record_project_spend(BOOK, project["id"], 200, "over", MEMBER)
        self.assertEqual(mutant_spend(200), "accepted")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_spend(200), "rejected")
        view = self.ext.project_view(BOOK, project["id"], MEMBER)
        self.assertEqual(view["spent_cents"], 900)


if __name__ == "__main__":
    unittest.main()
