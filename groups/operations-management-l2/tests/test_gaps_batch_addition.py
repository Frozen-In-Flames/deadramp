"""Final GAPS batch tests, second unit — Remainder Addition,
Operations Management L2.

Pins the verticals surface in ``src/opsmgmt/verticals.py``
(``OpsVerticals``, wrapping the core ``OpsStore``): one test
class per entry of the "Remainder Addition — Operations
Management L2 (+20 forks)" GAPS.md section (see
``../BATCH-ADDITION.md`` for the per-entry disposition), plus
cross-cutting pins -- ``vert_``-prefixed actions and
``:denied`` denials on the core audit log, stub labels on the
Maximo reference records, derived-never-stored summaries,
integer-cents-only money shapes, opaque-reference-only record
shapes, and this unit's fresh negative control: the case
decider-not-opener guard ``_check_decider_not_opener``.

Fixtures: ``make_store()`` (a person, an organization, and a
project with the person as member) from ``opsmgmt_helpers``;
ADMIN=alice/admin, OPERATOR=bob/operator, VIEWER=carol/viewer.
"""

import unittest

import opsmgmt.verticals as verticals_module
from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, make_store

from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from opsmgmt.verticals import OpsVerticals


class VertFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.person, self.org, self.project = make_store()
        self.vert = OpsVerticals(self.store)
        self.pid = self.person["id"]
        self.oid = self.org["id"]
        self.proj = self.project["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]

    def make_asset(self, name="Pump"):
        return self.store.create_asset(name, ADMIN, project_id=self.proj)


class TestManagedPrint(VertFixture):
    """Entry: Managed print services engine (Canon, Xerox) --
    device records, integer meter readings, and print-job
    records with reported statuses; nothing prints."""

    def test_device_meter_job_and_summary(self):
        device = self.vert.register_print_device("printer-floor3", "multifunction", OPERATOR)
        self.assertEqual(device["id"], "pdv-1")
        self.assertIs(device["printed_here"], False)
        reading = self.vert.record_meter_reading(device["id"], 1200, OPERATOR, period="2026-10")
        self.assertEqual(reading["pages"], 1200)
        self.assertIs(reading["collected_here"], False)
        job = self.vert.record_print_job(device["id"], OPERATOR, pages=12,
                                         reported_status="reported_completed",
                                         project_id=self.proj)
        self.assertIs(job["printed_here"], False)
        summary = self.vert.print_summary(ADMIN)
        self.assertEqual(summary["devices"], 1)
        self.assertEqual(summary["devices_by_kind"], {"multifunction": 1})
        self.assertEqual(summary["jobs_by_reported_status"], {"reported_completed": 1})
        self.assertEqual(summary["job_pages_total"], 12)
        self.assertEqual(summary["meter_pages_total"], 1200)
        self.assertIs(summary["printed_here"], False)

    def test_float_and_bool_pages_rejected_no_id_consumed(self):
        device = self.vert.register_print_device("printer-1", "printer", OPERATOR)
        for bad in (1.5, True):
            with self.assertRaises(ValidationError):
                self.vert.record_meter_reading(device["id"], bad, OPERATOR)
        job = self.vert.record_print_job(device["id"], OPERATOR, pages=3)
        self.assertEqual(job["id"], "pjb-1")

    def test_address_shaped_device_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.vert.register_print_device("10.1.2.3", "printer", OPERATOR)


class TestSupplyChain(VertFixture):
    """Entry: Supply chain & logistics execution suite
    (Manhattan) -- shipment/order/inventory records with
    reported states; no shipment moves."""

    def test_shipment_lifecycle_is_reported_only(self):
        shipment = self.vert.record_shipment("ship-100", OPERATOR, origin_ref="dc-east",
                                             destination_ref="site-north",
                                             project_id=self.proj)
        self.assertEqual(shipment["status"], "planned")
        self.assertIs(shipment["moved_here"], False)
        updated = self.vert.update_shipment_status(shipment["id"], "reported_delivered", OPERATOR)
        self.assertEqual(updated["status"], "reported_delivered")
        self.assertIs(updated["moved_here"], False)

    def test_order_inventory_and_summary(self):
        order = self.vert.record_supply_order("ord-7", OPERATOR, project_id=self.proj)
        self.assertIs(order["fulfilled_here"], False)
        self.vert.record_inventory("sku-pump", 40, OPERATOR, location_ref="dc-east")
        self.vert.record_inventory("sku-pump", -5, OPERATOR, location_ref="dc-east")
        summary = self.vert.supply_chain_summary(ADMIN)
        self.assertEqual(summary["orders_by_status"], {"recorded_open": 1})
        self.assertEqual(summary["inventory_quantity_by_sku"], {"sku-pump": 35})
        self.assertIs(summary["moved_here"], False)

    def test_float_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            self.vert.record_inventory("sku-x", 2.5, OPERATOR)


class TestPLM(VertFixture):
    """Entry: Product lifecycle management (PLM) platform
    (PTC) -- product records with stage as data, revision and
    change records; nothing is applied."""

    def test_product_revision_change_and_summary(self):
        product = self.vert.create_product("pump-x1", "Pump X1", OPERATOR, project_id=self.proj)
        self.assertEqual(product["stage"], "concept")
        moved = self.vert.advance_product_stage(product["id"], "production", OPERATOR)
        self.assertEqual(moved["stage"], "production")
        revision = self.vert.record_product_revision(product["id"], "rev-C", OPERATOR,
                                                     status="recorded_released")
        self.assertEqual(revision["revision_label"], "rev-C")
        change = self.vert.record_product_change(product["id"], "widen housing", OPERATOR)
        self.assertIs(change["applied_here"], False)
        summary = self.vert.plm_summary(ADMIN)
        self.assertEqual(summary["products_by_stage"], {"production": 1})
        self.assertEqual(summary["revisions"], 1)
        self.assertEqual(summary["changes"], 1)
        # Stage totals are derived: the stored product carries no count.
        self.assertNotIn("products_by_stage", self.vert.get_product(product["id"], ADMIN))

    def test_bad_stage_rejected(self):
        with self.assertRaises(ValidationError):
            self.vert.create_product("p-1", "P", OPERATOR, stage="launched")


class TestITSM(VertFixture):
    """Entry: IT service management (ITSM) suite (Ivanti) --
    ticket records with recorded/reported states; no ticket
    auto-resolves; change approval is separated from creation."""

    def test_ticket_lifecycle_reported(self):
        ticket = self.vert.create_ticket("incident", "VPN down", OPERATOR,
                                         priority="high", project_id=self.proj)
        self.assertEqual(ticket["status"], "recorded_open")
        self.assertIs(ticket["resolved_here"], False)
        moved = self.vert.transition_ticket(ticket["id"], "reported_resolved", OPERATOR)
        self.assertEqual(moved["status"], "reported_resolved")
        closed = self.vert.transition_ticket(ticket["id"], "recorded_closed", OPERATOR)
        with self.assertRaises(ValidationError):
            self.vert.transition_ticket(closed["id"], "recorded_open", OPERATOR)

    def test_change_approval_separation(self):
        change = self.vert.create_ticket("change", "Patch window", ADMIN)
        with self.assertRaises(ValidationError):
            self.vert.approve_change(change["id"], ADMIN)
        approved = self.vert.approve_change(change["id"], OPERATOR)
        self.assertEqual(approved["approved_by"], "bob")
        incident = self.vert.create_ticket("incident", "x", OPERATOR)
        with self.assertRaises(ValidationError):
            self.vert.approve_change(incident["id"], ADMIN)

    def test_summary_counts(self):
        self.vert.create_ticket("incident", "a", OPERATOR)
        self.vert.create_ticket("problem", "b", OPERATOR)
        summary = self.vert.itsm_summary(ADMIN)
        self.assertEqual(summary["tickets_by_kind"], {"incident": 1, "problem": 1})
        self.assertEqual(summary["tickets_by_status"], {"recorded_open": 2})


class TestInfraMaintenance(VertFixture):
    """Entry: Infrastructure maintenance management system
    (InfraLink) -- plan records over core assets, issue records,
    material quantities; nothing is scheduled or dispatched."""

    def test_plan_issue_material_and_summary(self):
        asset = self.make_asset()
        plan = self.vert.create_maintenance_plan("Quarterly PM", OPERATOR,
                                                 asset_id=asset["id"], interval_days=90)
        self.assertIs(plan["scheduled_here"], False)
        wo = self.store.create_work_order(OPERATOR, "maintenance", "PM visit",
                                          project_id=self.proj, asset_id=asset["id"])
        issue = self.vert.record_maintenance_issue("Seal wear", OPERATOR, plan_id=plan["id"],
                                                   asset_id=asset["id"], work_order_id=wo["id"])
        self.assertEqual(issue["status"], "recorded_open")
        self.vert.record_material("seal-kit", 4, OPERATOR, plan_id=plan["id"])
        summary = self.vert.infra_summary(ADMIN)
        self.assertEqual(summary["plans_by_status"], {"active": 1})
        self.assertEqual(summary["material_quantity_by_ref"], {"seal-kit": 4})
        self.assertIs(summary["scheduled_here"], False)

    def test_unknown_work_order_rejected(self):
        with self.assertRaises(NotFoundError):
            self.vert.record_maintenance_issue("x", OPERATOR, work_order_id="wo-99")

    def test_interval_must_be_positive_int(self):
        for bad in (0, 1.5, True):
            with self.assertRaises(ValidationError):
                self.vert.create_maintenance_plan("P", OPERATOR, interval_days=bad)


class TestFacilities(VertFixture):
    """Entry: Facilities & real property management suite /
    IWMS -- facility/space records, lease records in integer
    cents as data, move records; nothing is paid or moved."""

    def test_facility_space_lease_move_and_summary(self):
        facility = self.vert.create_facility("hq-north", "HQ North", OPERATOR,
                                             project_id=self.proj)
        space = self.vert.create_space(facility["id"], "room-4b", OPERATOR,
                                       kind="office", capacity=12)
        self.assertEqual(space["capacity"], 12)
        lease = self.vert.record_lease(facility["id"], OPERATOR, amount_cents=250000,
                                       counterparty_ref="lessor-1")
        self.assertIs(lease["paid_here"], False)
        move = self.vert.record_move_request(facility["id"], OPERATOR, "Team to floor 4")
        self.assertIs(move["moved_here"], False)
        summary = self.vert.facilities_summary(ADMIN)
        self.assertEqual(summary["spaces_by_kind"], {"office": 1})
        self.assertEqual(summary["lease_cents_total"], 250000)
        self.assertIs(summary["paid_here"], False)

    def test_float_cents_rejected(self):
        facility = self.vert.create_facility("hq-1", "HQ", OPERATOR)
        with self.assertRaises(ValidationError):
            self.vert.record_lease(facility["id"], OPERATOR, amount_cents=10.5)
        with self.assertRaises(ValidationError):
            self.vert.record_lease(facility["id"], OPERATOR, amount_cents=True)


class TestCaseManagement(VertFixture):
    """Entry: Case management platforms incl. EEO + FOIA
    (Tyler Federal, AINS eCase) -- case records, evidence as
    opaque references only, decisions under the
    decider-not-opener seam, FOIA production as a recorded
    reported state; nothing is released."""

    def test_case_shape_holds_no_content(self):
        case = self.vert.open_case("case-eeo-1", "eeo", "Workplace complaint", ADMIN,
                                   project_id=self.proj)
        self.assertEqual(
            set(case.keys()),
            {"id", "case_ref", "case_type", "subject", "status", "project_id",
             "released_here", "created_by", "created_utc", "updated_utc"})
        self.assertIs(case["released_here"], False)
        evidence = self.vert.record_case_evidence_ref(case["id"], "ev-ref-9", OPERATOR)
        self.assertIs(evidence["content_held_here"], False)
        self.assertNotIn("content", {k for k in evidence if k != "content_held_here"})

    def test_decision_canonical(self):
        case = self.vert.open_case("case-1", "general", "Matter", ADMIN)
        decision = self.vert.record_case_decision(case["id"], "favorable_reported", OPERATOR)
        self.assertEqual(decision["outcome"], "favorable_reported")
        self.assertIs(decision["effected_here"], False)

    def test_opener_may_not_decide_canonical(self):
        case = self.vert.open_case("case-1", "eeo", "Matter", ADMIN)
        with self.assertRaises(ValidationError):
            self.vert.record_case_decision(case["id"], "dismissed_reported", ADMIN)
        self.assertEqual(self.vert.list_case_decisions(ADMIN, case_id=case["id"]), [])

    def test_foia_production_is_reported_state_only(self):
        case = self.vert.open_case("case-foia-1", "foia", "Records request", OPERATOR)
        production = self.vert.record_foia_production(
            case["id"], OPERATOR, reported_status="reported_released", pages_reported=42)
        self.assertIs(production["released_here"], False)
        self.assertEqual(production["pages_reported"], 42)
        summary = self.vert.case_summary(ADMIN)
        self.assertEqual(summary["foia_productions_by_reported_status"],
                         {"reported_released": 1})
        self.assertIs(summary["released_here"], False)

    def test_foia_production_requires_foia_case(self):
        case = self.vert.open_case("case-1", "eeo", "Matter", OPERATOR)
        with self.assertRaises(ValidationError):
            self.vert.record_foia_production(case["id"], OPERATOR)

    def test_closed_case_is_terminal(self):
        case = self.vert.open_case("case-1", "general", "Matter", OPERATOR)
        self.vert.transition_case(case["id"], "recorded_closed", OPERATOR)
        with self.assertRaises(ValidationError):
            self.vert.transition_case(case["id"], "recorded_open", OPERATOR)


class TestDeciderNotOpenerNegativeControl(VertFixture):
    """Fresh negative control for this unit: the actor who
    records a case decision may never be the case's opener (the
    ``_check_decider_not_opener`` seam in
    ``opsmgmt/verticals.py``).

    Three legs, the house form: (1) the canonical expectation
    from the real implementation, (2) the mutant (the seam
    patched to a no-op in-process) would NOT produce it -- the
    opener's own decision succeeds, and (3) treating the
    mutant's outcome as the expected outcome fails.
    """

    def test_decider_guard_canonical_but_mutant_not(self):
        case = self.vert.open_case("case-nc", "eeo", "Matter", ADMIN)

        # (1) Canonical: the opener's decision is refused and no
        # decision is recorded.
        with self.assertRaises(ValidationError):
            self.vert.record_case_decision(case["id"], "favorable_reported", ADMIN)
        canonical = self.vert.list_case_decisions(ADMIN, case_id=case["id"])
        self.assertEqual(len(canonical), 0)

        # (2) Mutant: with the guard seam disabled, the same
        # decision succeeds -- the mutant would NOT produce the
        # canonical outcome.
        original = verticals_module._check_decider_not_opener
        verticals_module._check_decider_not_opener = (
            lambda opened_by, decider: None)
        try:
            mutant_decision = self.vert.record_case_decision(
                case["id"], "favorable_reported", ADMIN)
        finally:
            verticals_module._check_decider_not_opener = original
        self.assertEqual(mutant_decision["outcome"], "favorable_reported")
        mutant = self.vert.list_case_decisions(ADMIN, case_id=case["id"])
        self.assertEqual(len(mutant), 1)

        # (3) Treating the mutant's outcome as the expectation fails.
        with self.assertRaises(AssertionError):
            self.assertEqual(len(mutant), len(canonical))


class TestProcessMining(VertFixture):
    """Entry: Business process modeling, process mining &
    enterprise architecture platform (ARIS / ALFABET) -- model
    records with elements as data, reported-analysis records;
    no event log is ingested and nothing is mined."""

    def test_model_update_and_reported_analysis(self):
        model = self.vert.create_process_model("intake-flow", "Intake Flow", ADMIN,
                                               element_labels=["intake", "review"],
                                               project_id=self.proj)
        self.assertIs(model["executed_here"], False)
        updated = self.vert.update_process_model(model["id"], ADMIN,
                                                 element_labels=["intake", "review", "decide"])
        self.assertEqual(updated["version"], 2)
        analysis = self.vert.record_reported_analysis(
            model["id"], {"cases_reported": 300, "variants_reported": 12}, OPERATOR)
        self.assertIs(analysis["computed_here"], False)
        self.assertIs(analysis["mined_here"], False)
        summary = self.vert.process_summary(ADMIN)
        self.assertEqual(summary["models_by_kind"], {"process": 1})
        self.assertEqual(summary["analyses"], 1)
        self.assertIs(summary["mined_here"], False)
        # Analysis counts are derived in the summary only: the
        # stored model record carries no analysis count.
        self.assertNotIn("analyses", self.vert.get_process_model(model["id"], ADMIN))

    def test_operator_denied_model_create(self):
        with self.assertRaises(PermissionDenied):
            self.vert.create_process_model("m-1", "M", OPERATOR)
        self.assertIn("vert_model_create:denied", self.audit_actions())

    def test_analysis_counts_validation(self):
        model = self.vert.create_process_model("m-1", "M", ADMIN)
        for bad in ({"cases": -1}, {"cases": True}, {}):
            with self.assertRaises(ValidationError):
                self.vert.record_reported_analysis(model["id"], bad, OPERATOR)


class TestMailPackage(VertFixture):
    """Entry: Mail & package operations (Pitney Bowes) -- item
    records with reported states and locker records; no package
    is tracked live and nothing is shipped."""

    def test_item_lifecycle_and_summary(self):
        item = self.vert.record_mail_item("pkg-881", OPERATOR, carrier_ref="carrier-1",
                                          project_id=self.proj)
        self.assertIs(item["tracked_live_here"], False)
        self.assertIs(item["shipped_here"], False)
        moved = self.vert.update_mail_item_status(item["id"], "reported_delivered", OPERATOR)
        self.assertEqual(moved["status"], "reported_delivered")
        self.vert.register_locker("locker-bank-a", OPERATOR, facility_ref="hq-north")
        summary = self.vert.mail_summary(ADMIN)
        self.assertEqual(summary["items_by_status"], {"reported_delivered": 1})
        self.assertEqual(summary["lockers"], 1)
        self.assertIs(summary["tracked_live_here"], False)

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.vert.record_mail_item("x-1", OPERATOR, kind="freight")


class TestPortfolioPlanning(VertFixture):
    """Entry: Strategic portfolio & agile planning platforms
    (Clarity, Rally) -- portfolio/initiative/roadmap records;
    priority is verbatim data and nothing is ranked."""

    def test_portfolio_initiative_roadmap_and_summary(self):
        portfolio = self.vert.create_portfolio("FY27 Portfolio", OPERATOR,
                                               project_id=self.proj)
        initiative = self.vert.create_initiative(portfolio["id"], "Modernize intake",
                                                 OPERATOR, priority_label="must-do")
        self.assertEqual(initiative["priority_label"], "must-do")
        self.assertIs(initiative["ranked_here"], False)
        self.vert.record_roadmap_item(portfolio["id"], "Intake beta", OPERATOR,
                                      iteration_label="sprint-14")
        summary = self.vert.portfolio_summary(ADMIN)
        self.assertEqual(summary["initiatives_by_status"], {"proposed": 1})
        self.assertEqual(summary["roadmap_items"], 1)
        self.assertIs(summary["ranked_here"], False)
        # No computed score appears; the only rank-shaped key is
        # the honesty label itself, pinned False above.
        self.assertNotIn("score", {k.lower() for k in summary})


class TestBackOfficeERP(VertFixture):
    """Entry: Back-office ERP suite (Accenture) -- journal and
    payroll records in integer cents with recorded states; no
    transaction posts and nothing is paid."""

    def test_journal_payroll_and_derived_totals(self):
        debit = self.vert.record_journal_entry("acct-supplies", "debit", 5000, OPERATOR,
                                               project_id=self.proj)
        self.assertIs(debit["posted_here"], False)
        self.vert.record_journal_entry("acct-cash", "credit", 5000, OPERATOR,
                                       status="reported_posted")
        payroll = self.vert.record_payroll_record(self.pid, OPERATOR, amount_cents=120000,
                                                  period="2026-10")
        self.assertIs(payroll["paid_here"], False)
        summary = self.vert.erp_summary(ADMIN)
        self.assertEqual(summary["debit_cents_total"], 5000)
        self.assertEqual(summary["credit_cents_total"], 5000)
        self.assertEqual(summary["payroll_cents_total"], 120000)
        self.assertIs(summary["posted_here"], False)
        # Totals are derived: the stored entry carries none.
        stored = self.vert.list_journal_entries(ADMIN)[0]
        self.assertNotIn("debit_cents_total", stored)

    def test_float_cents_rejected_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.vert.record_journal_entry("acct-x", "debit", 9.99, OPERATOR)
        entry = self.vert.record_journal_entry("acct-x", "debit", 100, OPERATOR)
        self.assertEqual(entry["id"], "jrn-1")

    def test_unknown_person_rejected(self):
        with self.assertRaises(NotFoundError):
            self.vert.record_payroll_record("per-99", OPERATOR, amount_cents=1)


class TestContractProgress(VertFixture):
    """Entry: Contract progress management application (iSite)
    -- contract, milestone, progress-report, and finance
    records; percent is stored as reported, never computed."""

    def test_contract_milestone_progress_finance(self):
        contract = self.vert.create_contract("ctr-2026-1", "Support Contract", OPERATOR,
                                             project_id=self.proj, org_id=self.oid)
        milestone = self.vert.record_milestone(contract["id"], "Kickoff", OPERATOR,
                                               status="reported_complete",
                                               due_at="2026-06-01T00:00:00Z")
        self.assertEqual(milestone["status"], "reported_complete")
        report = self.vert.record_progress_report(contract["id"], 40, OPERATOR)
        self.assertEqual(report["percent_reported"], 40)
        self.assertIs(report["computed_here"], False)
        finance = self.vert.record_contract_finance(contract["id"], 75000, OPERATOR,
                                                    project_id=self.proj)
        self.assertIs(finance["paid_here"], False)
        summary = self.vert.contract_summary(ADMIN)
        self.assertEqual(summary["milestones_by_status"], {"reported_complete": 1})
        self.assertEqual(summary["finance_cents_total"], 75000)
        # No averaged/computed percent appears anywhere in the summary.
        self.assertNotIn("percent", {k.lower() for k in summary})

    def test_percent_bounds(self):
        contract = self.vert.create_contract("ctr-1", "C", OPERATOR)
        for bad in (-1, 101, 40.5, True):
            with self.assertRaises(ValidationError):
                self.vert.record_progress_report(contract["id"], bad, OPERATOR)

    def test_unknown_org_rejected(self):
        with self.assertRaises(NotFoundError):
            self.vert.create_contract("ctr-1", "C", OPERATOR, org_id="org-99")


class TestMaximoStub(VertFixture):
    """Entry: Enterprise asset management depth: predictive
    maintenance / asset health / IoT telemetry analytics (IBM
    Maximo) -- shipped as a labeled reference implementation:
    reported labels and reported counts only; no prediction,
    health score, or analytics value is computed."""

    def test_health_reference_labels(self):
        asset = self.make_asset("HVAC Unit")
        ref = self.vert.register_health_reference("hvac-roof-1", "asset_health",
                                                  "degraded_reported", OPERATOR,
                                                  asset_id=asset["id"])
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["predicted_here"], False)
        self.assertIs(ref["computed_here"], False)
        self.assertEqual(ref["reported_label"], "degraded_reported")
        self.assertNotIn("score", ref)
        self.assertNotIn("health_score", ref)

    def test_telemetry_analytics_reference_labels(self):
        ref = self.vert.record_telemetry_analytics_reference(
            "hvac-roof-1", {"readings_reported": 900, "alerts_reported": 2}, OPERATOR)
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["reference_transport"], True)
        self.assertIs(ref["computed_here"], False)
        self.assertIs(ref["collected_here"], False)
        summary = self.vert.maximo_summary(ADMIN)
        self.assertEqual(summary["telemetry_analytics_references"], 1)
        self.assertIs(summary["predicted_here"], False)
        for key in summary:
            for token in ("score", "rate", "grade"):
                self.assertNotIn(token, key.lower())


class TestCrossCutting(VertFixture):
    """Cross-cutting pins for the whole verticals surface."""

    def test_vert_actions_recorded_on_core_audit(self):
        self.vert.register_print_device("printer-1", "printer", OPERATOR)
        self.vert.open_case("case-1", "general", "Matter", OPERATOR)
        actions = self.audit_actions()
        self.assertIn("vert_print_device_register", actions)
        self.assertIn("vert_case_open", actions)

    def test_denied_attempt_audited_and_no_state_change(self):
        with self.assertRaises(PermissionDenied):
            self.vert.register_print_device("printer-1", "printer", VIEWER)
        self.assertIn("vert_print_device_register:denied", self.audit_actions())
        self.assertEqual(self.vert.list_print_devices(ADMIN), [])

    def test_no_actor_write_denied(self):
        with self.assertRaises(PermissionDenied):
            self.vert.open_case("case-1", "general", "Matter", None)

    def test_failed_create_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.vert.register_print_device("printer-1", "holodeck", OPERATOR)
        device = self.vert.register_print_device("printer-1", "printer", OPERATOR)
        self.assertEqual(device["id"], "pdv-1")

    def test_unknown_vertical_record(self):
        with self.assertRaises(NotFoundError):
            self.vert.get_case("cas-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.vert.get_product("prd-99", ADMIN)

    def test_records_are_copies(self):
        case = self.vert.open_case("case-1", "general", "Matter", OPERATOR)
        case["status"] = "tampered"
        stored = self.vert.get_case(case["id"], ADMIN)
        self.assertEqual(stored["status"], "recorded_open")

    def test_verticals_do_not_touch_first_unit_surface(self):
        # The first batch unit's OpsExtensions and this unit's
        # OpsVerticals are independent surfaces over one store:
        # building vertical records changes no core record.
        before = self.store.list_work_orders(OPERATOR)
        self.vert.open_case("case-1", "foia", "Request", OPERATOR)
        self.vert.record_journal_entry("acct-x", "debit", 100, OPERATOR)
        self.assertEqual(self.store.list_work_orders(OPERATOR), before)


if __name__ == "__main__":
    unittest.main()
