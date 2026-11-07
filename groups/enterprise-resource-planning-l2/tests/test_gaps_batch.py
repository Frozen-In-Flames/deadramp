"""Final GAPS batch — extension surface tests.

Pins ``src/erp/extensions.py`` (``ErpExtensions``), the
in-substrate forms and labeled reference implementations for
the 16 open gaps of UNION-SPEC.md's gap list for this group
(see ``../BATCH.md`` for the per-entry disposition). Each test
class names the GAPS.md entry it pins. Fixtures use the house
actors from ``erp_helpers`` (alice=admin, bob=operator,
carol=viewer) over a fresh core store per test.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from erp.errors import NotFoundError, PermissionDenied, ValidationError  # noqa: E402
from erp.extensions import ErpExtensions  # noqa: E402

from erp_helpers import (  # noqa: E402
    ADMIN,
    OPERATOR,
    VIEWER,
    make_org,
    make_person,
    make_store,
)

FORBIDDEN_KEY_PARTS = ("score", "rating", "rank", "grade", "email",
                       "phone", "ssn", "fraud")


def assert_no_forbidden_keys(case, value):
    if isinstance(value, dict):
        for key, item in value.items():
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(part, key.lower(),
                                 "forbidden key part in %r" % (key,))
            assert_no_forbidden_keys(case, item)
    elif isinstance(value, list):
        for item in value:
            assert_no_forbidden_keys(case, item)


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.ext = ErpExtensions(self.store)
        self.org = make_org(self.store)
        self.oid = self.org["id"]

    def make_entry(self, ref="JE-0001", amount=10000):
        return self.store.create_ledger_entry(
            OPERATOR, self.oid, ref, "Close entry", [
                {"account_ref": "ACCT-1000", "debit_cents": amount,
                 "credit_cents": 0},
                {"account_ref": "ACCT-2000", "debit_cents": 0,
                 "credit_cents": amount},
            ])

    def make_order(self, ref="PO-0001", supplier="SUPPLIER-0001",
                   quantity=2, price=3000):
        return self.store.create_purchase_order(
            OPERATOR, self.oid, ref, supplier,
            [{"item_label": "Widgets", "quantity": quantity,
              "unit_price_cents": price}])


class TestPortalPresentation(BatchFixture):
    """Gap: Suite platform & portal presentation layer."""

    def test_layout_derived_in_position_order(self):
        page = self.ext.create_portal_page(
            OPERATOR, self.oid, "PAGE-HOME", "Home (label)")
        self.ext.add_portal_widget(
            OPERATOR, page["id"], "W-2", "summary (label)", 2)
        returned = self.ext.add_portal_widget(
            OPERATOR, page["id"], "W-1", "search (label)", 1)
        # Stored widget list keeps recording order...
        self.assertEqual(
            [w["widget_ref"] for w in returned["widgets"]], ["W-2", "W-1"])
        # ...while the layout is derived in position order.
        layout = self.ext.portal_layout(OPERATOR, self.oid)
        widgets = layout["pages"][0]["widgets"]
        self.assertEqual([w["widget_ref"] for w in widgets],
                         ["W-1", "W-2"])

    def test_duplicate_position_and_ref_rejected(self):
        page = self.ext.create_portal_page(
            OPERATOR, self.oid, "PAGE-HOME", "Home (label)")
        self.ext.add_portal_widget(
            OPERATOR, page["id"], "W-1", "search (label)", 1)
        with self.assertRaises(ValidationError):
            self.ext.add_portal_widget(
                OPERATOR, page["id"], "W-2", "other (label)", 1)
        with self.assertRaises(ValidationError):
            self.ext.add_portal_widget(
                OPERATOR, page["id"], "W-1", "other (label)", 2)
        with self.assertRaises(ValidationError):
            self.ext.create_portal_page(
                OPERATOR, self.oid, "PAGE-HOME", "Again (label)")


class TestDataLake(BatchFixture):
    """Gap: Data lake & schema-on-read engine."""

    def test_schema_applied_at_read_over_current_records(self):
        dataset = self.ext.register_lake_dataset(
            OPERATOR, self.oid, "DS-LEDGER", "ledger_entries",
            ["entry_ref", "total_debits_cents"])
        before = self.ext.lake_query(OPERATOR, dataset["id"])
        self.assertEqual(before["row_count"], 0)
        self.assertFalse(before["materialized"])
        self.make_entry()
        after = self.ext.lake_query(OPERATOR, dataset["id"])
        self.assertEqual(after["row_count"], 1)
        self.assertEqual(after["rows"],
                         [{"entry_ref": "JE-0001",
                           "total_debits_cents": 10000}])

    def test_stored_dataset_holds_no_rows(self):
        dataset = self.ext.register_lake_dataset(
            OPERATOR, self.oid, "DS-LEDGER", "ledger_entries",
            ["entry_ref"])
        self.assertEqual(
            set(dataset.keys()),
            {"id", "org_id", "dataset_ref", "source_kind", "fields",
             "created_by", "created_utc"})

    def test_unknown_source_and_duplicate_field_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_lake_dataset(
                OPERATOR, self.oid, "DS-X", "external_warehouse",
                ["entry_ref"])
        with self.assertRaises(ValidationError):
            self.ext.register_lake_dataset(
                OPERATOR, self.oid, "DS-Y", "ledger_entries",
                ["entry_ref", "entry_ref"])


class TestCloseAndConsolidation(BatchFixture):
    """Gap: Financial close & consolidation engine."""

    def test_close_status_derived_never_stored(self):
        entry = self.make_entry()
        close = self.ext.create_close_period(
            OPERATOR, self.oid, "CLO-2026-10", "2026-10", [entry["id"]])
        self.assertEqual(
            set(close.keys()),
            {"id", "org_id", "close_ref", "period_label", "entry_ids",
             "created_by", "created_utc"})
        status = self.ext.close_status(OPERATOR, close["id"])
        self.assertEqual(status["total_debits_cents"], 10000)
        self.assertEqual(status["total_credits_cents"], 10000)
        self.assertTrue(status["balanced"])
        self.assertEqual(status["entry_count"], 1)

    def test_close_rejects_entry_from_another_org(self):
        entry = self.make_entry()
        other = self.store.create_organization(ADMIN, "ORG-0002",
                                               "Other (label)")
        with self.assertRaises(ValidationError):
            self.ext.create_close_period(
                OPERATOR, other["id"], "CLO-X", "2026-10", [entry["id"]])

    def test_consolidation_sums_per_account_across_orgs(self):
        self.make_entry(amount=10000)
        other = self.store.create_organization(ADMIN, "ORG-0002",
                                               "Other (label)")
        self.store.create_ledger_entry(
            OPERATOR, other["id"], "JE-9001", "Other close", [
                {"account_ref": "ACCT-1000", "debit_cents": 2500,
                 "credit_cents": 0},
                {"account_ref": "ACCT-3000", "debit_cents": 0,
                 "credit_cents": 2500},
            ])
        view = self.ext.consolidation_view(OPERATOR, [self.oid,
                                                      other["id"]])
        rows = {r["account_ref"]: r for r in view["accounts"]}
        self.assertEqual(rows["ACCT-1000"]["debit_cents"], 12500)
        self.assertEqual(rows["ACCT-1000"]["net_cents"], 12500)
        self.assertEqual(rows["ACCT-2000"]["credit_cents"], 10000)
        self.assertEqual(view["total_debits_cents"], 12500)
        self.assertEqual(view["total_credits_cents"], 12500)


class TestSourceToSettle(BatchFixture):
    """Gap: Source-to-settle execution engine."""

    def setUp(self):
        super().setUp()
        self.order = self.make_order()  # total 6000
        self.cycle = self.ext.create_settle_cycle(
            OPERATOR, self.oid, "SET-0001", self.order["id"])

    def test_match_state_derived_from_order_lifecycle(self):
        status = self.ext.settle_status(OPERATOR, self.cycle["id"])
        self.assertEqual(status["match_state"], "awaiting_receipt")
        self.assertEqual(status["po_total_cents"], 6000)
        self.store.transition_purchase_order(OPERATOR, self.order["id"],
                                             "received")
        status = self.ext.settle_status(OPERATOR, self.cycle["id"])
        self.assertEqual(status["match_state"], "matched")

    def test_instruction_cap_guard_and_no_id_consumed_on_refusal(self):
        first = self.ext.record_payment_instruction(
            OPERATOR, self.cycle["id"], "PI-0001", 4000)
        self.assertEqual(first["id"], "pin-1")
        self.assertFalse(first["payment_executed"])
        with self.assertRaises(ValidationError):
            self.ext.record_payment_instruction(
                OPERATOR, self.cycle["id"], "PI-0002", 2001)
        second = self.ext.record_payment_instruction(
            OPERATOR, self.cycle["id"], "PI-0002", 2000)
        self.assertEqual(second["id"], "pin-2")
        status = self.ext.settle_status(OPERATOR, self.cycle["id"])
        self.assertEqual(status["instructed_cents"], 6000)
        self.assertEqual(status["remaining_cents"], 0)

    def test_float_instruction_rejected_and_cycle_record_shape(self):
        with self.assertRaises(ValidationError):
            self.ext.record_payment_instruction(
                OPERATOR, self.cycle["id"], "PI-F", 10.5)
        self.assertEqual(
            set(self.cycle.keys()),
            {"id", "org_id", "cycle_ref", "po_id", "created_by",
             "created_utc"})


class TestManufacturing(BatchFixture):
    """Gap: Manufacturing production engine."""

    def setUp(self):
        super().setUp()
        self.item = self.store.create_inventory_item(
            OPERATOR, self.oid, "ITEM-0001", "Bracket", 5)
        self.order = self.ext.create_production_order(
            OPERATOR, self.oid, "PRD-0001", self.item["id"], 10)

    def test_output_applies_to_inventory_and_status_derives(self):
        self.ext.record_production_output(OPERATOR, self.order["id"], 4)
        status = self.ext.production_status(OPERATOR, self.order["id"])
        self.assertEqual(status["produced_quantity"], 4)
        self.assertEqual(status["remaining_quantity"], 6)
        self.assertFalse(status["complete"])
        self.assertEqual(status["inventory_quantity_on_hand"], 9)
        self.ext.record_production_output(OPERATOR, self.order["id"], 6)
        status = self.ext.production_status(OPERATOR, self.order["id"])
        self.assertTrue(status["complete"])

    def test_over_plan_output_refused_whole(self):
        with self.assertRaises(ValidationError):
            self.ext.record_production_output(
                OPERATOR, self.order["id"], 11)
        status = self.ext.production_status(OPERATOR, self.order["id"])
        self.assertEqual(status["produced_quantity"], 0)
        self.assertEqual(status["inventory_quantity_on_hand"], 5)
        self.assertEqual(
            set(self.order.keys()),
            {"id", "org_id", "order_ref", "item_id", "planned_quantity",
             "created_by", "created_utc"})


class TestSupplierExchange(BatchFixture):
    """Gap: Supplier exchange network."""

    def test_notice_is_a_labeled_record_and_feed_derives(self):
        self.make_order()
        notice = self.ext.publish_supplier_notice(
            OPERATOR, self.oid, "NOT-0001", "SUPPLIER-0001", "demand",
            "Quarterly demand (label)")
        self.assertTrue(notice["reference_transport"])
        self.assertEqual(notice["delivery_state"], "recorded_only")
        feed = self.ext.supplier_exchange_feed(
            OPERATOR, self.oid, "SUPPLIER-0001")
        self.assertEqual(len(feed["notices"]), 1)
        self.assertEqual(feed["purchase_orders"],
                         [{"po_ref": "PO-0001", "status": "open",
                           "total_cents": 6000}])

    def test_unknown_notice_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.publish_supplier_notice(
                OPERATOR, self.oid, "NOT-0002", "SUPPLIER-0001",
                "broadcast", "Nope (label)")


class TestTalentManagement(BatchFixture):
    """Gap: Talent management engine."""

    def setUp(self):
        super().setUp()
        make_person(self.store, self.org)
        self.cycle = self.ext.create_talent_cycle(
            OPERATOR, self.oid, "PERSON-0001", "TAL-0001")

    def test_stages_move_forward_only(self):
        self.assertEqual(self.cycle["stage"], "identified")
        moved = self.ext.record_talent_stage(
            OPERATOR, self.cycle["id"], "developed")
        self.assertEqual(moved["stage"], "developed")
        self.assertEqual(len(moved["stage_history"]), 2)
        with self.assertRaises(ValidationError):
            self.ext.record_talent_stage(
                OPERATOR, self.cycle["id"], "hired")
        with self.assertRaises(ValidationError):
            self.ext.record_talent_stage(
                OPERATOR, self.cycle["id"], "developed")

    def test_pipeline_counts_derived(self):
        self.ext.record_talent_stage(OPERATOR, self.cycle["id"], "hired")
        pipeline = self.ext.talent_pipeline(OPERATOR, self.oid)
        self.assertEqual(pipeline["cycles_by_stage"]["hired"], 1)
        self.assertEqual(pipeline["cycles_by_stage"]["identified"], 0)
        self.assertEqual(pipeline["cycles_by_stage"]["retained"], 0)


class TestScheduling(BatchFixture):
    """Gap: Workforce scheduling optimizer -- built as a
    deterministic coverage derivation; no optimization is
    performed or claimed."""

    def setUp(self):
        super().setUp()
        make_person(self.store, self.org)
        self.schedule = self.ext.create_schedule(
            OPERATOR, self.oid, "SCH-0001",
            [{"work_date": "2026-10-05", "required_minutes": 960}])

    def test_coverage_gap_and_conflict_derived(self):
        self.ext.add_shift(OPERATOR, self.schedule["id"], "PERSON-0001",
                           "2026-10-05", 480)
        view = self.ext.schedule_view(OPERATOR, self.schedule["id"])
        self.assertEqual(view["method"], "deterministic_coverage")
        self.assertEqual(view["coverage"],
                         [{"work_date": "2026-10-05",
                           "required_minutes": 960,
                           "scheduled_minutes": 480,
                           "gap_minutes": 480}])
        self.assertEqual(view["conflicts"], [])
        self.ext.add_shift(OPERATOR, self.schedule["id"], "PERSON-0001",
                           "2026-10-05", 240)
        view = self.ext.schedule_view(OPERATOR, self.schedule["id"])
        self.assertEqual(view["coverage"][0]["gap_minutes"], 240)
        self.assertEqual(view["conflicts"],
                         [{"person_ref": "PERSON-0001",
                           "work_date": "2026-10-05", "shift_count": 2}])
        self.assertEqual(view["per_person"],
                         [{"person_ref": "PERSON-0001",
                           "total_minutes": 720}])

    def test_stored_schedule_holds_demand_only(self):
        self.assertEqual(
            set(self.schedule.keys()),
            {"id", "org_id", "schedule_ref", "demands", "created_by",
             "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.add_shift(OPERATOR, self.schedule["id"],
                               "PERSON-0001", "2026-10-05", 60.5)
        with self.assertRaises(NotFoundError):
            self.ext.add_shift(OPERATOR, self.schedule["id"],
                               "PERSON-9999", "2026-10-05", 60)


class TestPayrollCalculation(BatchFixture):
    """Gap: Payroll calculation engine."""

    def setUp(self):
        super().setUp()
        make_person(self.store, self.org)
        self.calc = self.ext.create_payroll_calculation(
            OPERATOR, self.oid, "PERSON-0001", "CAL-0001",
            "2026-10-01", "2026-10-31", 6000,
            [{"label": "tax (label)", "rate_bps": 1000}])

    def test_amounts_derived_from_current_time_entries(self):
        self.store.create_time_entry(OPERATOR, self.oid, "PERSON-0001",
                                     "2026-10-05", 480)
        self.store.create_time_entry(OPERATOR, self.oid, "PERSON-0001",
                                     "2026-11-02", 480)  # outside range
        view = self.ext.payroll_calculation_view(OPERATOR,
                                                self.calc["id"])
        self.assertEqual(view["total_minutes"], 480)
        self.assertEqual(view["gross_cents"], 48000)
        self.assertEqual(view["total_deductions_cents"], 4800)
        self.assertEqual(view["net_cents"], 43200)
        # A later time entry changes the derivation: nothing was
        # stored from the first calculation.
        self.store.create_time_entry(OPERATOR, self.oid, "PERSON-0001",
                                     "2026-10-06", 60)
        view = self.ext.payroll_calculation_view(OPERATOR,
                                                self.calc["id"])
        self.assertEqual(view["gross_cents"], 54000)

    def test_stored_record_holds_inputs_only(self):
        self.assertEqual(
            set(self.calc.keys()),
            {"id", "org_id", "person_ref", "calc_ref", "from_date",
             "to_date", "hourly_rate_cents", "deductions", "created_by",
             "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.create_payroll_calculation(
                OPERATOR, self.oid, "PERSON-0001", "CAL-0002",
                "2026-10-01", "2026-10-31", 60.5, [])
        with self.assertRaises(ValidationError):
            self.ext.create_payroll_calculation(
                OPERATOR, self.oid, "PERSON-0001", "CAL-0003",
                "2026-10-01", "2026-10-31", 6000,
                [{"label": "a (label)", "rate_bps": 6000},
                 {"label": "b (label)", "rate_bps": 6000}])


class TestBusinessIntelligence(BatchFixture):
    """Gap: Business intelligence platform."""

    def test_metrics_derived_from_core_records(self):
        self.make_entry()
        dashboard = self.ext.create_dashboard(
            OPERATOR, self.oid, "DSH-0001", "Overview (label)",
            ["ledger_totals", "organization_counts"])
        view = self.ext.dashboard_view(OPERATOR, dashboard["id"])
        self.assertEqual(view["metrics"]["ledger_totals"],
                         {"entry_count": 1, "total_debits_cents": 10000,
                          "total_credits_cents": 10000})
        self.assertEqual(
            view["metrics"]["organization_counts"]["applications"], 0)
        self.assertEqual(
            set(dashboard.keys()),
            {"id", "org_id", "dashboard_ref", "title_label",
             "metric_kinds", "created_by", "created_utc"})

    def test_unknown_metric_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_dashboard(
                OPERATOR, self.oid, "DSH-0002", "Nope (label)",
                ["predictive_insights"])


class TestPerformanceManagement(BatchFixture):
    """Gap: Enterprise performance management engine."""

    def setUp(self):
        super().setUp()
        self.plan = self.ext.create_plan(
            OPERATOR, self.oid, "PLN-0001", "FY plan (label)", [
                {"account_ref": "ACCT-1000",
                 "planned_debit_cents": 100000, "planned_credit_cents": 0},
                {"account_ref": "ACCT-2000",
                 "planned_debit_cents": 0, "planned_credit_cents": 40000},
            ])

    def test_actuals_and_variance_derived(self):
        self.make_entry(amount=10000)
        view = self.ext.plan_view(OPERATOR, self.plan["id"])
        rows = {r["account_ref"]: r for r in view["accounts"]}
        self.assertEqual(rows["ACCT-1000"]["planned_net_cents"], 100000)
        self.assertEqual(rows["ACCT-1000"]["actual_net_cents"], 10000)
        self.assertEqual(rows["ACCT-1000"]["variance_cents"], -90000)
        self.assertEqual(rows["ACCT-2000"]["variance_cents"], 30000)
        self.assertEqual(view["planned_net_cents"], 60000)
        self.assertEqual(view["actual_net_cents"], 0)
        for line in self.plan["lines"]:
            self.assertEqual(
                set(line.keys()),
                {"account_ref", "planned_debit_cents",
                 "planned_credit_cents"})

    def test_forecast_applies_growth_with_integer_arithmetic(self):
        forecast = self.ext.plan_forecast(OPERATOR, self.plan["id"],
                                          1000, 2)
        self.assertEqual(
            forecast["projection"],
            [{"period_index": 1, "projected_net_cents": 66000},
             {"period_index": 2, "projected_net_cents": 72600}])


class TestGovernanceRiskCompliance(BatchFixture):
    """Gap: Governance, risk & compliance engine."""

    def test_exposure_derived_never_stored(self):
        risk = self.ext.create_risk_record(
            OPERATOR, self.oid, "RSK-0001", "Vendor outage (label)", 3, 4)
        self.assertEqual(
            set(risk.keys()),
            {"id", "org_id", "risk_ref", "title_label", "likelihood",
             "impact", "created_by", "created_utc"})
        exposure = self.ext.risk_exposure(OPERATOR, risk["id"])
        self.assertEqual(exposure["exposure"], 12)
        self.assertEqual(exposure["band"], "high")
        with self.assertRaises(ValidationError):
            self.ext.create_risk_record(
                OPERATOR, self.oid, "RSK-0002", "Bad (label)", 6, 1)
        with self.assertRaises(ValidationError):
            self.ext.create_risk_record(
                OPERATOR, self.oid, "RSK-0003", "Bad (label)", 2.5, 1)

    def test_check_outcome_recorded_once_and_summary_derives(self):
        self.ext.create_risk_record(
            OPERATOR, self.oid, "RSK-0001", "Vendor outage (label)", 3, 4)
        check = self.ext.create_control_check(
            OPERATOR, self.oid, "CHK-0001", "Access review (label)",
            "role matrix (label)")
        done = self.ext.record_check_result(OPERATOR, check["id"],
                                            "pass")
        self.assertEqual(done["outcome"], "pass")
        with self.assertRaises(ValidationError):
            self.ext.record_check_result(OPERATOR, check["id"], "fail")
        summary = self.ext.grc_summary(OPERATOR, self.oid)
        self.assertEqual(summary["risks_by_band"]["high"], 1)
        self.assertEqual(summary["checks_by_outcome"],
                         {"pass": 1, "fail": 0, "open": 0})
        self.assertIn("audit_read",
                      summary["permission_matrix"]["admin"])
        self.assertNotIn("audit_read",
                         summary["permission_matrix"]["operator"])


class TestFederationStub(BatchFixture):
    """Gap (stub-engine): Identity federation service."""

    def test_record_is_a_labeled_hook_only_reference(self):
        record = self.ext.create_federation_record(
            OPERATOR, self.oid, "FED-0001", "IdP (label)",
            "SAML (label)")
        self.assertTrue(record["reference_stub"])
        self.assertTrue(record["hook_only"])
        self.assertEqual(record["status"], "recorded_reference_only")
        listed = self.ext.list_federation_records(OPERATOR,
                                                  org_id=self.oid)
        self.assertEqual([r["id"] for r in listed], [record["id"]])
        for item in listed:
            self.assertTrue(item["reference_stub"])


class TestOrchestrationStub(BatchFixture):
    """Gap (stub-engine): Integration execution & orchestration
    runtime (the build's registries store records and never
    execute)."""

    def test_record_is_labeled_and_references_a_workflow(self):
        workflow = self.store.create_workflow(
            OPERATOR, self.oid, "Expense flow (label)",
            "Expense submitted (label)")
        record = self.ext.create_orchestration_record(
            OPERATOR, self.oid, "ORC-0001", workflow["id"],
            "ION runtime (label)")
        self.assertTrue(record["reference_stub"])
        self.assertEqual(record["status"], "recorded_reference_only")
        self.assertEqual(record["workflow_id"], workflow["id"])
        with self.assertRaises(NotFoundError):
            self.ext.create_orchestration_record(
                OPERATOR, self.oid, "ORC-0002", "wfl-999",
                "Missing (label)")

    def test_no_execution_surface_on_the_extension(self):
        verbs = ("execute", "run_", "fire", "trigger", "dispatch",
                 "connect")
        operations = [name for name in dir(ErpExtensions)
                      if not name.startswith("_")]
        for name in operations:
            for verb in verbs:
                self.assertNotIn(verb, name,
                                 "execution verb in %r" % (name,))


class TestGatewayStub(BatchFixture):
    """Gap (stub-engine): API gateway runtime."""

    def test_route_record_against_gateway_integration(self):
        gateway = self.store.create_integration(
            OPERATOR, self.oid, "api_gateway", "Gateway (label)")
        record = self.ext.create_gateway_route_record(
            OPERATOR, self.oid, "GWR-0001", gateway["id"],
            "/ledger (label)", "throttle (label)")
        self.assertTrue(record["reference_stub"])
        self.assertEqual(record["status"], "recorded_reference_only")

    def test_route_against_non_gateway_integration_rejected(self):
        platform = self.store.create_integration(
            OPERATOR, self.oid, "integration_platform",
            "Platform (label)")
        with self.assertRaises(ValidationError):
            self.ext.create_gateway_route_record(
                OPERATOR, self.oid, "GWR-0002", platform["id"],
                "/ledger (label)", "throttle (label)")


class TestExpensePolicyStub(BatchFixture):
    """Gap (stub-engine): Expense policy enforcement & fraud
    detection engine -- shipped as a labeled reference: a
    deterministic limit check whose findings state recorded
    limit breaches only."""

    def setUp(self):
        super().setUp()
        make_person(self.store, self.org)
        self.policy = self.ext.create_expense_policy(
            OPERATOR, self.oid, "POL-0001", "Travel", 2000)

    def test_policy_record_is_labeled_reference(self):
        self.assertTrue(self.policy["reference_stub"])
        self.assertEqual(self.policy["status"],
                         "recorded_reference_only")
        with self.assertRaises(ValidationError):
            self.ext.create_expense_policy(
                OPERATOR, self.oid, "POL-0002", "Travel", 20.5)

    def test_evaluation_derives_limit_breaches_only(self):
        report = self.store.create_expense_report(
            OPERATOR, self.oid, "PERSON-0001", "EXP-0001", [
                {"category_label": "Travel", "amount_cents": 5000},
                {"category_label": "Travel", "amount_cents": 1500},
                {"category_label": "Meals", "amount_cents": 9000},
            ])
        evaluation = self.ext.expense_policy_evaluation(
            OPERATOR, self.policy["id"], report["id"])
        self.assertTrue(evaluation["reference_stub"])
        self.assertEqual(evaluation["method"],
                         "deterministic_limit_check")
        self.assertEqual(evaluation["finding_count"], 1)
        self.assertEqual(evaluation["findings"],
                         [{"category_label": "Travel",
                           "amount_cents": 5000, "limit_cents": 2000,
                           "excess_cents": 3000}])
        self.assertEqual(evaluation["report_total_cents"], 15500)
        assert_no_forbidden_keys(self, evaluation)


class TestBatchBoundaries(BatchFixture):
    """Cross-cutting pins for the whole batch surface."""

    def test_viewer_is_denied_mutations(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_portal_page(VIEWER, self.oid, "PAGE-X",
                                        "Nope (label)")
        with self.assertRaises(PermissionDenied):
            self.ext.create_federation_record(
                VIEWER, self.oid, "FED-X", "IdP (label)", "SAML (label)")
        page = self.ext.portal_layout(VIEWER, self.oid)
        self.assertEqual(page["pages"], [])

    def test_mutations_are_audited_with_ext_prefix(self):
        self.ext.create_portal_page(OPERATOR, self.oid, "PAGE-HOME",
                                    "Home (label)")
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_portal_page_create", actions)

    def test_record_shapes_hold_no_forbidden_fields(self):
        make_person(self.store, self.org)
        page = self.ext.create_portal_page(
            OPERATOR, self.oid, "PAGE-HOME", "Home (label)")
        self.ext.add_portal_widget(OPERATOR, page["id"], "W-1",
                                   "search (label)", 1)
        dataset = self.ext.register_lake_dataset(
            OPERATOR, self.oid, "DS-1", "persons", ["person_ref"])
        risk = self.ext.create_risk_record(
            OPERATOR, self.oid, "RSK-1", "Risk (label)", 2, 2)
        fed = self.ext.create_federation_record(
            OPERATOR, self.oid, "FED-1", "IdP (label)", "SAML (label)")
        for record in (page, dataset, risk, fed):
            assert_no_forbidden_keys(self, record)


if __name__ == "__main__":
    unittest.main()
