"""Final GAPS batch tests — Accounting L2 extension surface.

Traces to: gaps-batch/DECISION.md (ratified 2026-11-07) and the group's
BATCH.md. Each test class names the GAPS.md entry it pins. Fixtures use
the canonical helpers: a book owned by MEMBER with VIEWER as member;
OUTSIDER is a non-member. Money is integer cents throughout.
"""

import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

import accounting_helpers as helpers  # noqa: E402
from accounting.errors import PermissionDenied, ValidationError  # noqa: E402
from accounting.extensions import AccountingExtensions  # noqa: E402

ADMIN = helpers.ADMIN
MEMBER = helpers.MEMBER
VIEWER = helpers.VIEWER
OUTSIDER = helpers.OUTSIDER


def make_ext():
    store, book_id = helpers.make_store()
    chart = helpers.make_chart(store, book_id)
    return AccountingExtensions(store), store, book_id, chart


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.book_id, self.chart = make_ext()


class TestAnalytics(BatchFixture):
    """Entry: AI / analytics & BI (deterministic rules, no learned model)."""

    def test_summary_derived_from_posted_statements(self):
        helpers.build_scenario(self.store, self.book_id, self.chart)
        s = self.ext.analytics_summary(self.book_id, "2026-01", MEMBER)
        self.assertEqual(s["total_revenue_cents"], 50000)
        self.assertEqual(s["total_expense_cents"], 20000)
        self.assertEqual(s["net_income_cents"], 30000)
        self.assertEqual(s["net_margin_bps"], 6000)
        self.assertEqual(s["method"], "deterministic_rules")
        self.assertTrue(s["trial_balanced"])

    def test_anomaly_flag_on_large_change(self):
        helpers.post_revenue(self.store, self.book_id, self.chart, 10000,
                             date=helpers.DATE_JAN)
        helpers.post_revenue(self.store, self.book_id, self.chart, 40000,
                             date=helpers.DATE_FEB)
        out = self.ext.detect_anomalies(self.book_id, "2026-02", "2026-01", 5000, MEMBER)
        self.assertTrue(out["flags"])
        self.assertTrue(all(f["change_bps"] >= 5000 for f in out["flags"]))

    def test_float_threshold_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.detect_anomalies(self.book_id, "2026-02", "2026-01", 50.0, MEMBER)


class TestProjects(BatchFixture):
    """Entry: Project / program / portfolio management."""

    def test_spend_derived_and_over_budget_flag(self):
        p = self.ext.create_project(self.book_id, "P1", "Portal", 100000, MEMBER)
        self.assertEqual(p["id"], "proj-1")
        self.ext.record_project_cost(self.book_id, p["id"], "2026-01-05", "work", 40000, MEMBER)
        self.ext.record_project_cost(self.book_id, p["id"], "2026-01-06", "more", 70000, MEMBER)
        st = self.ext.project_status(self.book_id, p["id"], MEMBER)
        self.assertEqual(st["spent_cents"], 110000)
        self.assertEqual(st["remaining_cents"], -10000)
        self.assertTrue(st["over_budget"])
        stored = self.ext.list_projects(self.book_id, MEMBER)[0]
        self.assertNotIn("spent_cents", stored)

    def test_duplicate_code_and_float_budget_rejected(self):
        self.ext.create_project(self.book_id, "P1", "Portal", 1000, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.create_project(self.book_id, "P1", "Again", 1000, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.create_project(self.book_id, "P2", "Float", 10.0, MEMBER)


class TestRisk(BatchFixture):
    """Entry: Risk register / GRC suites."""

    def test_exposure_derived_never_stored(self):
        r = self.ext.create_risk(self.book_id, "Vendor failure", "operational", 3, 5, "team-a", MEMBER)
        out = self.ext.risk_exposure(self.book_id, r["id"], MEMBER)
        self.assertEqual(out["exposure"], 15)
        self.assertEqual(out["band"], "high")
        self.assertNotIn("exposure", self.ext.list_risks(self.book_id, MEMBER)[0])

    def test_score_out_of_range_and_mitigate(self):
        with self.assertRaises(ValidationError):
            self.ext.create_risk(self.book_id, "Bad", "x", 6, 1, "team-a", MEMBER)
        r = self.ext.create_risk(self.book_id, "Risk", "x", 2, 2, "team-a", MEMBER)
        done = self.ext.mitigate_risk(self.book_id, r["id"], "controls added", MEMBER)
        self.assertEqual(done["status"], "mitigated")
        with self.assertRaises(ValidationError):
            self.ext.mitigate_risk(self.book_id, r["id"], "again", MEMBER)


class TestAuditManagement(BatchFixture):
    """Entry: Audit management workbenches."""

    def test_plan_workpaper_finding_close_with_sod(self):
        plan = self.ext.create_audit_plan(self.book_id, "FY26 audit", "2026-01", MEMBER)
        wp = self.ext.add_workpaper(self.book_id, plan["id"], "WP-1", "doc-ref-1", MEMBER)
        self.assertEqual(wp["plan_id"], plan["id"])
        f = self.ext.create_finding(self.book_id, plan["id"], "Weak control", "high", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.close_finding(self.book_id, f["id"], "fixed", MEMBER)
        closed = self.ext.close_finding(self.book_id, f["id"], "fixed", ADMIN)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(len(self.ext.list_findings(self.book_id, MEMBER, plan["id"])), 1)

    def test_bad_severity_rejected(self):
        plan = self.ext.create_audit_plan(self.book_id, "P", "2026-01", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.create_finding(self.book_id, plan["id"], "F", "severe", MEMBER)


class TestFixedAssets(BatchFixture):
    """Entry: Fixed-asset registers."""

    def test_book_value_derived_straight_line(self):
        a = self.ext.register_fixed_asset(self.book_id, "FA-1", "Server", 120000, 0, 12, "2026-01", MEMBER)
        v = self.ext.asset_book_value(self.book_id, a["id"], "2026-04", MEMBER)
        self.assertEqual(v["months_depreciated"], 3)
        self.assertEqual(v["accumulated_cents"], 30000)
        self.assertEqual(v["book_value_cents"], 90000)
        stored = self.ext.list_fixed_assets(self.book_id, MEMBER)[0]
        self.assertNotIn("book_value_cents", stored)
        v2 = self.ext.asset_book_value(self.book_id, a["id"], "2027-06", MEMBER)
        self.assertEqual(v2["book_value_cents"], 0)

    def test_salvage_must_be_below_cost_and_float_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_fixed_asset(self.book_id, "FA-2", "X", 1000, 1000, 12, "2026-01", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_fixed_asset(self.book_id, "FA-3", "X", 100.0, 0, 12, "2026-01", MEMBER)


class TestRetention(BatchFixture):
    """Entry: Records retention."""

    def test_eligibility_derived_from_age(self):
        r = self.ext.create_retention_record(self.book_id, "rec-ref-1", "invoices", "2024-01", 24, MEMBER)
        early = self.ext.retention_disposition(self.book_id, r["id"], "2025-06", MEMBER)
        self.assertFalse(early["eligible_for_disposition"])
        self.assertEqual(early["age_months"], 17)
        late = self.ext.retention_disposition(self.book_id, r["id"], "2026-02", MEMBER)
        self.assertTrue(late["eligible_for_disposition"])


class TestForecasting(BatchFixture):
    """Entry: Forecasting / EPM."""

    def test_projection_derived_from_base_period_net(self):
        helpers.build_scenario(self.store, self.book_id, self.chart)
        f = self.ext.create_forecast(self.book_id, "Plan", "2026-01", 1000, MEMBER)
        out = self.ext.derive_forecast(self.book_id, f["id"], 2, MEMBER)
        self.assertEqual(out["base_net_cents"], 30000)
        self.assertEqual([p["period"] for p in out["projection"]], ["2026-02", "2026-03"])
        self.assertEqual(out["projection"][0]["projected_net_cents"], 33000)
        self.assertEqual(out["projection"][1]["projected_net_cents"], 36300)


class TestSupplyChain(BatchFixture):
    """Entry: Supply chain."""

    def test_po_total_computed_and_status_derived(self):
        po = self.ext.create_purchase_order(
            self.book_id, "vendor-ref-1", "2026-01-05",
            [{"description": "widgets", "quantity": 10, "unit_price_cents": 500}], MEMBER)
        self.assertEqual(po["total_cents"], 5000)
        self.assertEqual(self.ext.purchase_order_status(self.book_id, po["id"], MEMBER)["status"], "ordered")
        self.ext.record_receipt(self.book_id, po["id"], 0, 4, "2026-01-06", MEMBER)
        self.assertEqual(self.ext.purchase_order_status(self.book_id, po["id"], MEMBER)["status"],
                         "partially_received")
        with self.assertRaises(ValidationError):
            self.ext.record_receipt(self.book_id, po["id"], 0, 7, "2026-01-07", MEMBER)
        self.ext.record_receipt(self.book_id, po["id"], 0, 6, "2026-01-07", MEMBER)
        self.assertEqual(self.ext.purchase_order_status(self.book_id, po["id"], MEMBER)["status"], "fulfilled")

    def test_float_price_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_purchase_order(self.book_id, "v", "2026-01-05",
                                           [{"description": "x", "quantity": 1,
                                             "unit_price_cents": 1.5}], MEMBER)


class TestGovConGrants(BatchFixture):
    """Entry: GovCon / grants. The ceiling guard is the signature seam."""

    def test_draw_applies_indirect_and_derives_status(self):
        g = self.ext.create_grant_award(self.book_id, "award-1", "sponsor-ref", 100000, 1000, "2026-01", MEMBER)
        d = self.ext.record_grant_draw(self.book_id, g["id"], "2026-01-10", 10000, MEMBER)
        self.assertEqual(d["indirect_cents"], 1000)
        st = self.ext.grant_status(self.book_id, g["id"], MEMBER)
        self.assertEqual(st["drawn_cents"], 11000)
        self.assertEqual(st["remaining_cents"], 89000)

    def test_draw_beyond_ceiling_rejected_whole(self):
        g = self.ext.create_grant_award(self.book_id, "award-1", "s-ref", 10000, 0, "2026-01", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_grant_draw(self.book_id, g["id"], "2026-01-10", 10001, MEMBER)
        self.assertEqual(self.ext.grant_status(self.book_id, g["id"], MEMBER)["drawn_cents"], 0)


class TestCrypto(BatchFixture):
    """Entry: Crypto investigation (records only)."""

    def test_summary_derives_net_units(self):
        c = self.ext.create_crypto_case(self.book_id, "Case 1", "wallet-ref-1", MEMBER)
        self.ext.record_crypto_transaction(self.book_id, c["id"], "2026-01-05", "in", 500, "cp-ref-1", MEMBER)
        self.ext.record_crypto_transaction(self.book_id, c["id"], "2026-01-06", "out", 200, "cp-ref-2", MEMBER)
        s = self.ext.crypto_case_summary(self.book_id, c["id"], MEMBER)
        self.assertEqual((s["in_units"], s["out_units"], s["net_units"]), (500, 200, 300))
        with self.assertRaises(ValidationError):
            self.ext.record_crypto_transaction(self.book_id, c["id"], "2026-01-06", "sideways", 1, "cp", MEMBER)


class TestTimeTracking(BatchFixture):
    """Entry: Time tracking."""

    def test_summary_derives_totals_by_worker_ref(self):
        self.ext.record_time_entry(self.book_id, "worker-1", "2026-01-05", 120, "proj-x", MEMBER)
        self.ext.record_time_entry(self.book_id, "worker-1", "2026-01-06", 60, "proj-x", MEMBER)
        self.ext.record_time_entry(self.book_id, "worker-2", "2026-02-01", 30, "", MEMBER)
        s = self.ext.time_summary(self.book_id, "2026-01", MEMBER)
        self.assertEqual(s["total_minutes"], 180)
        self.assertEqual(s["by_worker_ref"], {"worker-1": 180})
        with self.assertRaises(ValidationError):
            self.ext.record_time_entry(self.book_id, "w", "2026-01-05", 1441, "", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_time_entry(self.book_id, "w", "2026-01-05", 1.5, "", MEMBER)


class TestESignatureStub(BatchFixture):
    """Entry: E-signature — STUB-ENGINE, labeled reference implementation."""

    def test_every_record_carries_reference_stub(self):
        r = self.ext.create_signature_request(self.book_id, "doc-ref-1", "signer-ref-1", MEMBER)
        self.assertIs(r["reference_stub"], True)
        self.assertEqual(r["status"], "recorded_reference_only")
        rows = self.ext.list_signature_requests(self.book_id, MEMBER)
        self.assertTrue(all(row["reference_stub"] is True for row in rows))
        self.assertEqual(set(r.keys()), {"id", "book_id", "document_ref", "signer_ref",
                                         "reference_stub", "status", "created_by", "created_utc"})


class TestPayroll(BatchFixture):
    """Entry: Payroll (records pay; pays nobody)."""

    def test_summary_derives_net_never_stored(self):
        run = self.ext.create_payroll_run(self.book_id, "2026-01", MEMBER)
        line = self.ext.add_pay_line(self.book_id, run["id"], "worker-1", 200000, 30000, MEMBER)
        self.assertNotIn("net_cents", line)
        s = self.ext.payroll_summary(self.book_id, run["id"], MEMBER)
        self.assertEqual((s["gross_cents"], s["deduction_cents"], s["net_cents"]),
                         (200000, 30000, 170000))

    def test_deductions_above_gross_and_float_rejected(self):
        run = self.ext.create_payroll_run(self.book_id, "2026-01", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.add_pay_line(self.book_id, run["id"], "w", 1000, 1001, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.add_pay_line(self.book_id, run["id"], "w", 100.0, 0, MEMBER)


class TestTax(BatchFixture):
    """Entry: Tax (computes a recorded figure; files nothing)."""

    def test_tax_due_derived_never_stored(self):
        f = self.ext.create_tax_filing(self.book_id, "jurisdiction-ref-1", "2026-01", 100000, 825, MEMBER)
        out = self.ext.tax_due(self.book_id, f["id"], MEMBER)
        self.assertEqual(out["tax_due_cents"], 8250)
        self.assertNotIn("tax_due_cents", f)


class TestForensic(BatchFixture):
    """Entry: Forensic investigation."""

    def test_evidence_hash_validated_and_custody_appended(self):
        c = self.ext.create_forensic_case(self.book_id, "Investigation 1", MEMBER)
        e = self.ext.add_evidence_item(self.book_id, c["id"], "ledger export", "deadbeef12345678", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.add_evidence_item(self.book_id, c["id"], "bad", "not-a-hash!", MEMBER)
        updated = self.ext.record_custody_transfer(self.book_id, e["id"], "custodian-ref-1", "2026-01-07", MEMBER)
        self.assertEqual(len(updated["custody"]), 1)
        s = self.ext.forensic_case_summary(self.book_id, c["id"], MEMBER)
        self.assertEqual((s["evidence_count"], s["custody_transfers"]), (1, 1))


class TestBatchBoundaries(BatchFixture):
    """Cross-cutting: membership, RBAC, audit, shape/privacy pins."""

    def test_non_member_denied_and_viewer_cannot_enter(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_project(self.book_id, "PX", "X", 1000, OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.create_project(self.book_id, "PX", "X", 1000, VIEWER)

    def test_mutations_audited_on_core_log(self):
        self.ext.create_project(self.book_id, "P9", "Audited", 1000, MEMBER)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_project_create", actions)

    def test_record_shapes_hold_no_pii_fields(self):
        p = self.ext.create_project(self.book_id, "PS", "Shape", 1000, MEMBER)
        self.assertEqual(set(p.keys()), {"id", "book_id", "code", "name", "budget_cents",
                                         "created_by", "created_utc"})
        t = self.ext.record_time_entry(self.book_id, "worker-9", "2026-01-05", 30, "", MEMBER)
        for key in t:
            self.assertNotIn(key, ("name", "email", "phone", "ssn", "address"))


if __name__ == "__main__":
    unittest.main()
