"""Final GAPS batch tests for the Operations Management untiered set.

Traces to: the 9 open Extended entries of this set's union spec
(``UNION-SPEC.md`` "Gaps registered for this set", GAPS.md section
"Untiered Set 2 -- Operations Management (20 forks, tier null)"),
closed by ``opsmgmt/extensions.py`` under
``../../gaps-batch/DECISION.md``: 8 built as records/derivations
in-substrate, 1 shipped as a labeled reference implementation
(AI assistants & agents, re-judged -- see ``BATCH.md``).

Every test names the entry it pins. Cross-cutting pins: tier null
binds the whole extension surface (a recursive scan finds no
tier-shaped key, no float, and no numeric list in any extension
record or view); stub records carry ``reference_stub: True``;
denied attempts are audited ``ext_<action>:denied``; failed
operations consume no id; derived values are derived at read and
never stored.

The fresh negative control is in
:class:`TestLatestLabelNegativeControl`: the current-state seam
``OpsExtensions._latest_label`` mutated to read the earliest
label instead must not produce the canonical outcome.
"""

import unittest

from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from opsmgmt.extensions import OpsExtensions

from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.person, self.org, self.project = make_store()
        self.ext = OpsExtensions(self.store)
        self.asset = self.store.create_asset(
            "Pump Assembly", OPERATOR, project_id=self.project["id"])

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]


def _walk(value):
    """Yield every (key, value) pair and scalar in a record/view."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


class TestMaintenancePrograms(BatchFixture):
    """Entry: CMMS/EAM depth (built).

    Program definitions over core assets, custody events as
    reported labels, and work-order counts derived at read from
    the core's own work-order views.
    """

    def test_program_definition_shape_and_labels(self):
        program = self.ext.define_maintenance_program(
            "Quarterly PM", OPERATOR, asset_id=self.asset["id"],
            interval_days_reported=90)
        self.assertEqual(program["id"], "pm-1")
        self.assertEqual(program["work_type"], "maintenance")
        self.assertEqual(program["interval_days_reported"], 90)
        self.assertIs(program["definition_only"], True)
        self.assertIs(program["performed_here"], False)
        self.assertIs(program["executed_here"], False)

    def test_program_unknown_asset_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.define_maintenance_program(
                "X", OPERATOR, asset_id="ast-999")
        program = self.ext.define_maintenance_program("Y", OPERATOR)
        self.assertEqual(program["id"], "pm-1")

    def test_program_bad_work_type_and_interval_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.define_maintenance_program(
                "X", OPERATOR, work_type="alchemy")
        with self.assertRaises(ValidationError):
            self.ext.define_maintenance_program(
                "X", OPERATOR, interval_days_reported=1.5)
        with self.assertRaises(ValidationError):
            self.ext.define_maintenance_program(
                "X", OPERATOR, interval_days_reported=True)

    def test_viewer_may_not_define_program(self):
        with self.assertRaises(PermissionDenied):
            self.ext.define_maintenance_program("X", VIEWER)
        self.assertIn("ext_maintenance_program_define:denied",
                      self.audit_actions())

    def test_custody_event_shape_and_labels(self):
        event = self.ext.record_custody_event(
            self.asset["id"], "checked_out", OPERATOR,
            counterparty_ref="VENDOR-9")
        self.assertEqual(event["id"], "cus-1")
        self.assertEqual(event["event_label"], "checked_out")
        self.assertIs(event["custody_transferred_here"], False)
        self.assertIs(event["recorded_only"], True)
        with self.assertRaises(NotFoundError):
            self.ext.record_custody_event("ast-999", "x", OPERATOR)

    def test_program_view_counts_derived_at_read_not_stored(self):
        program = self.ext.define_maintenance_program(
            "PM", OPERATOR, asset_id=self.asset["id"])
        due = "2020-01-01T00:00:00+00:00"
        wo_open = self.store.create_work_order(
            OPERATOR, "maintenance", "Past due PM",
            asset_id=self.asset["id"], due_at=due)
        self.store.create_work_order(
            OPERATOR, "maintenance", "Done PM",
            asset_id=self.asset["id"])
        done = self.store.list_work_orders(actor=OPERATOR)
        done_id = [w for w in done if w["subject"] == "Done PM"][0]["id"]
        self.store.transition_work_order(done_id, OPERATOR, "in_progress")
        self.store.transition_work_order(done_id, OPERATOR, "completed")
        self.store.create_work_order(
            OPERATOR, "task", "Unrelated task",
            asset_id=self.asset["id"])
        self.ext.record_custody_event(self.asset["id"], "issued", OPERATOR)
        view = self.ext.maintenance_program_view(program["id"], OPERATOR)
        self.assertEqual(view["work_order_count"], 2)
        self.assertEqual(view["open_work_order_count"], 1)
        self.assertEqual(view["overdue_work_order_count"], 1)
        self.assertEqual(view["custody_event_count"], 1)
        self.assertIs(view["derived"], True)
        stored = self.ext.get_maintenance_program(program["id"], OPERATOR)
        self.assertNotIn("work_order_count", stored)
        self.assertNotIn("overdue_work_order_count", stored)
        self.assertEqual(wo_open["status"], "open")


class TestManufacturing(BatchFixture):
    """Entry: Manufacturing execution & ERP/MRP (built, records form).

    BOM definitions as data, production orders as records,
    outcomes and produced counts stored exactly as reported;
    nothing is executed.
    """

    def _bom(self):
        return self.ext.define_bill_of_materials(
            "Widget BOM", OPERATOR, project_id=self.project["id"],
            components=[{"part_ref": "PART-1", "quantity": 2},
                        {"part_ref": "PART-2", "quantity": 5}])

    def test_bom_definition_shape(self):
        bom = self._bom()
        self.assertEqual(bom["id"], "bom-1")
        self.assertEqual(bom["components"][1]["quantity"], 5)
        self.assertIs(bom["definition_only"], True)
        self.assertIs(bom["executed_here"], False)

    def test_bom_component_validation_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.define_bill_of_materials(
                "X", OPERATOR,
                components=[{"part_ref": "P", "quantity": 1.5}])
        with self.assertRaises(ValidationError):
            self.ext.define_bill_of_materials(
                "X", OPERATOR,
                components=[{"part_ref": "P", "quantity": 1,
                             "supplier": "S"}])
        with self.assertRaises(ValidationError):
            self.ext.define_bill_of_materials(
                "X", OPERATOR, components=[42])
        bom = self.ext.define_bill_of_materials("Y", OPERATOR)
        self.assertEqual(bom["id"], "bom-1")
        self.assertEqual(bom["components"], [])

    def test_production_order_and_outcome_rollup_derived(self):
        bom = self._bom()
        order = self.ext.create_production_order(
            bom["id"], OPERATOR, quantity=10)
        self.assertEqual(order["project_id"], self.project["id"])
        self.assertIs(order["executed_here"], False)
        self.ext.record_production_outcome(
            order["id"], "reported_partial", OPERATOR, produced_reported=4)
        self.ext.record_production_outcome(
            order["id"], "reported_complete", OPERATOR, produced_reported=6)
        view = self.ext.production_order_view(order["id"], OPERATOR)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["produced_total_reported"], 10)
        stored = self.ext.get_production_order(order["id"], OPERATOR)
        self.assertNotIn("produced_total_reported", stored)
        self.assertNotIn("outcome_count", stored)

    def test_production_order_quantity_must_be_positive_int(self):
        bom = self._bom()
        with self.assertRaises(ValidationError):
            self.ext.create_production_order(bom["id"], OPERATOR, quantity=0)
        with self.assertRaises(ValidationError):
            self.ext.create_production_order(
                bom["id"], OPERATOR, quantity=2.0)
        with self.assertRaises(NotFoundError):
            self.ext.create_production_order("bom-999", OPERATOR)


class TestProcurement(BatchFixture):
    """Entry: Procurement & sourcing platforms (built).

    Requisitions as records, sourcing events as append-only
    reported labels, awards as reported outcomes in integer
    cents; current state derived at read.
    """

    def test_requisition_view_state_and_totals_derived(self):
        req = self.ext.create_requisition(
            "Laptops", OPERATOR, org_id=self.org["id"],
            project_id=self.project["id"])
        self.assertIs(req["decided_here"], False)
        self.assertNotIn("current_state_label", req)
        view0 = self.ext.requisition_view(req["id"], OPERATOR)
        self.assertEqual(view0["current_state_label"], "recorded")
        self.ext.record_sourcing_event(req["id"], "issued", OPERATOR)
        self.ext.record_sourcing_event(
            req["id"], "quotes_received", OPERATOR, supplier_ref="SUP-1")
        self.ext.record_award(req["id"], "SUP-1", OPERATOR,
                              amount_cents_reported=12500)
        self.ext.record_award(req["id"], "SUP-2", OPERATOR,
                              amount_cents_reported=None)
        view = self.ext.requisition_view(req["id"], OPERATOR)
        self.assertEqual(view["current_state_label"], "quotes_received")
        self.assertEqual(view["event_count"], 2)
        self.assertEqual(view["award_count"], 2)
        self.assertEqual(view["awarded_total_cents_reported"], 12500)

    def test_award_amount_must_be_integer_cents(self):
        req = self.ext.create_requisition("X", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_award(req["id"], "SUP-1", OPERATOR,
                                  amount_cents_reported=10.5)
        with self.assertRaises(NotFoundError):
            self.ext.record_sourcing_event("req-999", "issued", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.create_requisition("X", OPERATOR, org_id="org-999")

    def test_viewer_may_not_create_requisition(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_requisition("X", VIEWER)
        self.assertIn("ext_requisition_create:denied",
                      self.audit_actions())


class TestContractExecution(BatchFixture):
    """Entry: Contract execution management (built).

    Agreements as records; execution states are append-only
    reported labels whose latest value derives at read; no
    contract is executed here.
    """

    def test_agreement_current_state_derived_not_stored(self):
        agreement = self.ext.create_agreement(
            "COMPASS surveillance", OPERATOR, org_id=self.org["id"],
            counterparty_ref="VENDOR-2")
        self.assertIs(agreement["executed_here"], False)
        self.assertNotIn("current_state_label", agreement)
        view0 = self.ext.agreement_view(agreement["id"], OPERATOR)
        self.assertEqual(view0["current_state_label"], "recorded")
        self.ext.record_agreement_state(
            agreement["id"], "reported_active", OPERATOR)
        self.ext.record_agreement_state(
            agreement["id"], "reported_under_review", OPERATOR)
        view = self.ext.agreement_view(agreement["id"], OPERATOR)
        self.assertEqual(view["current_state_label"],
                         "reported_under_review")
        self.assertEqual(view["state_count"], 2)
        stored = self.ext.get_agreement(agreement["id"], OPERATOR)
        self.assertNotIn("current_state_label", stored)

    def test_agreement_state_requires_known_agreement(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_agreement_state("agr-999", "x", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.create_agreement("X", OPERATOR, org_id="org-999")


class TestEvCharging(BatchFixture):
    """Entry: EV charging network management (built).

    Stations and sessions as records with energy in integer
    watt-hours as reported; totals derived at read; session
    control ships in reference form in-record.
    """

    def test_station_session_rollup_derived(self):
        station = self.ext.register_charging_station(
            "Depot charger 1", OPERATOR, asset_id=self.asset["id"],
            connector_label="CCS")
        self.assertIs(station["controlled_here"], False)
        self.ext.record_charging_session(
            station["id"], OPERATOR, energy_wh_reported=7200,
            vehicle_ref="VEH-1")
        self.ext.record_charging_session(
            station["id"], OPERATOR, energy_wh_reported=2800)
        view = self.ext.charging_station_view(station["id"], OPERATOR)
        self.assertEqual(view["session_count"], 2)
        self.assertEqual(view["energy_wh_total_reported"], 10000)
        stored = self.ext.get_charging_station(station["id"], OPERATOR)
        self.assertNotIn("energy_wh_total_reported", stored)

    def test_session_energy_must_be_integer_wh(self):
        station = self.ext.register_charging_station("S", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_charging_session(
                station["id"], OPERATOR, energy_wh_reported=7.2)
        with self.assertRaises(ValidationError):
            self.ext.record_charging_session(
                station["id"], OPERATOR, energy_wh_reported=-5)
        with self.assertRaises(NotFoundError):
            self.ext.record_charging_session("evs-999", OPERATOR)

    def test_control_request_is_labeled_reference(self):
        station = self.ext.register_charging_station("S", OPERATOR)
        request = self.ext.record_session_control_request(
            station["id"], "reported_stop_requested", OPERATOR)
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["controlled_here"], False)
        view = self.ext.charging_station_view(station["id"], OPERATOR)
        self.assertEqual(view["control_request_count"], 1)


class TestRealEstate(BatchFixture):
    """Entry: Real-estate/facilities portfolio platform (built).

    Properties and leases as records; portfolio counts derived
    at read.
    """

    def test_portfolio_counts_derived(self):
        p1 = self.ext.register_property(
            "HQ", OPERATOR, org_id=self.org["id"], kind_label="office")
        p2 = self.ext.register_property(
            "Depot", OPERATOR, org_id=self.org["id"], kind_label="depot")
        self.ext.register_property("Other org site", OPERATOR)
        self.ext.create_lease(p1["id"], OPERATOR, tenant_ref="TEN-1",
                              project_id=self.project["id"])
        self.ext.create_lease(p1["id"], OPERATOR, tenant_ref="TEN-2")
        view = self.ext.portfolio_view(self.org["id"], OPERATOR)
        self.assertEqual(view["property_count"], 2)
        self.assertEqual(view["lease_count"], 2)
        self.assertEqual(view["leased_property_count"], 1)
        self.assertIs(view["derived"], True)
        with self.assertRaises(NotFoundError):
            self.ext.portfolio_view("org-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.create_lease("prop-999", OPERATOR)


class TestAccessDevices(BatchFixture):
    """Entry: Kiosk & locker access management (built, records form).

    Grants exist in the record only; no device is unlocked or
    administered. Events are reported labels stored verbatim.
    """

    def test_grant_is_record_only_no_unlock(self):
        device = self.ext.register_access_device(
            "Lobby locker bank", OPERATOR, asset_id=self.asset["id"],
            location_label="Building A")
        self.assertIs(device["unlocked_here"], False)
        self.assertIs(device["device_controlled_here"], False)
        grant = self.ext.record_access_grant(
            device["id"], "PER-EXT-7", OPERATOR, purpose_label="pickup")
        self.assertIs(grant["granted_in_record_only"], True)
        self.assertIs(grant["unlocked_here"], False)
        event = self.ext.record_access_event(
            device["id"], "reported_opened", OPERATOR,
            grantee_ref="PER-EXT-7")
        self.assertIs(event["reported_only"], True)
        view = self.ext.access_device_view(device["id"], OPERATOR)
        self.assertEqual(view["grant_count"], 1)
        self.assertEqual(view["event_count"], 1)
        stored = self.ext.get_access_device(device["id"], OPERATOR)
        self.assertNotIn("grant_count", stored)

    def test_grant_requires_known_device_and_ref(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_access_grant("dev-999", "P-1", OPERATOR)
        device = self.ext.register_access_device("D", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_access_grant(device["id"], "  ", OPERATOR)


class TestAiAssistants(BatchFixture):
    """Entry: AI assistants & agents (reference, re-judged).

    Labeled reference implementation: declarations, request
    records holding opaque references only, outcome records
    holding opaque result references only. No prompt or result
    content exists in any shape; no inference runs.
    """

    def test_assistant_records_carry_stub_labels(self):
        assistant = self.ext.register_assistant(
            "Archie (reference)", ADMIN, capability_label="nl_query")
        self.assertIs(assistant["reference_stub"], True)
        self.assertIs(assistant["inference_here"], False)
        request = self.ext.record_assistant_request(
            assistant["id"], ADMIN, request_ref="REQ-EXT-1")
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["prompt_held"], False)
        outcome = self.ext.record_assistant_outcome(
            request["id"], "reported_answered", ADMIN,
            result_ref="RES-EXT-1")
        self.assertIs(outcome["reference_stub"], True)
        self.assertIs(outcome["inference_here"], False)
        self.assertEqual(outcome["result_ref"], "RES-EXT-1")

    def test_no_shape_can_hold_prompt_or_result_content(self):
        assistant = self.ext.register_assistant("A", ADMIN)
        request = self.ext.record_assistant_request(
            assistant["id"], ADMIN, request_ref="R-1")
        outcome = self.ext.record_assistant_outcome(
            request["id"], "reported_done", ADMIN, result_ref="O-1")
        for record in (assistant, request, outcome):
            for key, _value in _walk(record):
                self.assertNotIn("prompt_text", key)
                self.assertNotIn("result_text", key)
                self.assertNotIn("content", key)
        with self.assertRaises(TypeError):
            self.ext.record_assistant_request(
                assistant["id"], ADMIN, prompt_text="hello")

    def test_assistant_registration_is_admin_only(self):
        # workflow_write is admin-only in the core matrix.
        with self.assertRaises(PermissionDenied):
            self.ext.register_assistant("A", OPERATOR)
        self.assertIn("ext_assistant_register:denied",
                      self.audit_actions())
        assistant = self.ext.register_assistant("A", ADMIN)
        self.assertEqual(assistant["id"], "asst-1")


class TestSupplyChain(BatchFixture):
    """Entry: Supply-chain risk & payments orchestration (built).

    Shipments as records; risk labels verbatim with no computed
    score; payment instructions as integer-cent records that
    move no money; rollup derived at read.
    """

    def test_risk_label_verbatim_no_score(self):
        shipment = self.ext.record_shipment(
            "Resupply run", OPERATOR, project_id=self.project["id"],
            supplier_ref="SUP-3")
        report = self.ext.record_risk_report(
            shipment["id"], "elevated", OPERATOR, source_ref="SCR-1")
        self.assertEqual(report["risk_label"], "elevated")
        self.assertIs(report["score_computed_here"], False)
        self.assertIs(report["reported_only"], True)
        # The exact key set is pinned: there is no field that
        # could hold a computed score, and no numeric value
        # anywhere in the record (labels are booleans/strings).
        self.assertEqual(
            set(report.keys()),
            {"id", "shipment_id", "risk_label", "source_ref",
             "reported_only", "score_computed_here", "created_by",
             "created_utc"})
        for _key, value in _walk(report):
            if isinstance(value, bool):
                continue
            self.assertNotIsInstance(value, (int, float))

    def test_payment_instruction_and_view_rollup_derived(self):
        shipment = self.ext.record_shipment("Run", OPERATOR)
        self.assertIs(shipment["paid_here"], False)
        pay = self.ext.record_payment_instruction(
            shipment["id"], OPERATOR, 4200, payee_ref="SUP-3")
        self.assertIs(pay["paid_here"], False)
        self.assertIs(pay["settled_here"], False)
        self.assertIs(pay["executed_here"], False)
        self.ext.record_payment_instruction(
            shipment["id"], OPERATOR, 800, payee_ref="SUP-4")
        self.ext.record_risk_report(shipment["id"], "low", OPERATOR)
        self.ext.record_risk_report(shipment["id"], "elevated", OPERATOR)
        view = self.ext.shipment_view(shipment["id"], OPERATOR)
        self.assertEqual(view["payment_count"], 2)
        self.assertEqual(view["payment_total_cents_reported"], 5000)
        self.assertEqual(view["risk_report_count"], 2)
        self.assertEqual(view["latest_risk_label"], "elevated")
        stored = self.ext.get_shipment(shipment["id"], OPERATOR)
        self.assertNotIn("payment_total_cents_reported", stored)
        self.assertNotIn("latest_risk_label", stored)

    def test_payment_amount_must_be_positive_integer_cents(self):
        shipment = self.ext.record_shipment("Run", OPERATOR)
        for bad in (0, -1, 10.5, True):
            with self.assertRaises(ValidationError):
                self.ext.record_payment_instruction(
                    shipment["id"], OPERATOR, bad)
        with self.assertRaises(NotFoundError):
            self.ext.record_payment_instruction("shp-999", OPERATOR, 100)


class MutantExtensions(OpsExtensions):
    """Earliest-label mutant of the current-state seam."""

    @staticmethod
    def _latest_label(labels):
        if not labels:
            return "recorded"
        return labels[0]


class TestLatestLabelNegativeControl(BatchFixture):
    """Fresh negative control: the ``_latest_label`` seam.

    A record's current state is its LATEST recorded label. If
    the seam read the earliest label instead, superseded states
    would resurrect: an agreement reported under review after
    being reported active would still read active. The mutant
    must not produce the canonical outcome.
    """

    def _setup_pair(self, ext):
        agreement = ext.create_agreement("A", OPERATOR)
        ext.record_agreement_state(agreement["id"], "reported_active",
                                   OPERATOR)
        ext.record_agreement_state(agreement["id"],
                                   "reported_under_review", OPERATOR)
        return agreement

    def test_latest_label_wins_canonical_but_mutant_not(self):
        agreement = self._setup_pair(self.ext)
        view = self.ext.agreement_view(agreement["id"], OPERATOR)
        self.assertEqual(view["current_state_label"],
                         "reported_under_review")
        mutant = MutantExtensions(self.store)
        magreement = self._setup_pair(mutant)
        mview = mutant.agreement_view(magreement["id"], OPERATOR)
        self.assertEqual(mview["current_state_label"], "reported_active")
        with self.assertRaises(AssertionError):
            self.assertEqual(mview["current_state_label"],
                             "reported_under_review")

    def test_no_labels_reads_recorded_in_both(self):
        agreement = self.ext.create_agreement("A", OPERATOR)
        view = self.ext.agreement_view(agreement["id"], OPERATOR)
        self.assertEqual(view["current_state_label"], "recorded")
        mutant = MutantExtensions(self.store)
        magreement = mutant.create_agreement("A", OPERATOR)
        mview = mutant.agreement_view(magreement["id"], OPERATOR)
        self.assertEqual(mview["current_state_label"], "recorded")

    def test_latest_label_drives_risk_view_too(self):
        shipment = self.ext.record_shipment("Run", OPERATOR)
        self.ext.record_risk_report(shipment["id"], "low", OPERATOR)
        self.ext.record_risk_report(shipment["id"], "elevated", OPERATOR)
        view = self.ext.shipment_view(shipment["id"], OPERATOR)
        self.assertEqual(view["latest_risk_label"], "elevated")
        mutant = MutantExtensions(self.store)
        mshipment = mutant.record_shipment("Run", OPERATOR)
        mutant.record_risk_report(mshipment["id"], "low", OPERATOR)
        mutant.record_risk_report(mshipment["id"], "elevated", OPERATOR)
        mview = mutant.shipment_view(mshipment["id"], OPERATOR)
        self.assertEqual(mview["latest_risk_label"], "low")


class TestTierNullAndShapeScan(BatchFixture):
    """Cross-cutting: tier null and shape discipline.

    Every extension record and derived view is scanned
    recursively: no key may name a tier, a baseline, or an
    equivalence; no value may be a float; no list may hold
    numbers.
    """

    FORBIDDEN_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                           "impact_level")

    def _everything(self):
        ext = self.ext
        program = ext.define_maintenance_program(
            "PM", OPERATOR, asset_id=self.asset["id"],
            interval_days_reported=30)
        custody = ext.record_custody_event(
            self.asset["id"], "issued", OPERATOR)
        program_view = ext.maintenance_program_view(program["id"],
                                                   OPERATOR)
        bom = ext.define_bill_of_materials(
            "B", OPERATOR, project_id=self.project["id"],
            components=[{"part_ref": "P-1", "quantity": 3}])
        order = ext.create_production_order(bom["id"], OPERATOR,
                                            quantity=2)
        outcome = ext.record_production_outcome(
            order["id"], "reported_done", OPERATOR, produced_reported=2)
        order_view = ext.production_order_view(order["id"], OPERATOR)
        req = ext.create_requisition("R", OPERATOR, org_id=self.org["id"])
        event = ext.record_sourcing_event(req["id"], "issued", OPERATOR)
        award = ext.record_award(req["id"], "SUP-1", OPERATOR,
                                 amount_cents_reported=100)
        req_view = ext.requisition_view(req["id"], OPERATOR)
        agreement = ext.create_agreement("A", OPERATOR,
                                         org_id=self.org["id"])
        state = ext.record_agreement_state(
            agreement["id"], "reported_active", OPERATOR)
        agreement_view = ext.agreement_view(agreement["id"], OPERATOR)
        station = ext.register_charging_station(
            "S", OPERATOR, asset_id=self.asset["id"])
        session = ext.record_charging_session(
            station["id"], OPERATOR, energy_wh_reported=10)
        control = ext.record_session_control_request(
            station["id"], "reported_stop", OPERATOR)
        station_view = ext.charging_station_view(station["id"], OPERATOR)
        prop = ext.register_property("HQ", OPERATOR,
                                     org_id=self.org["id"])
        lease = ext.create_lease(prop["id"], OPERATOR, tenant_ref="T-1")
        portfolio = ext.portfolio_view(self.org["id"], OPERATOR)
        device = ext.register_access_device(
            "D", OPERATOR, asset_id=self.asset["id"])
        grant = ext.record_access_grant(device["id"], "P-1", OPERATOR)
        access_event = ext.record_access_event(
            device["id"], "reported_opened", OPERATOR)
        device_view = ext.access_device_view(device["id"], OPERATOR)
        assistant = ext.register_assistant("AI", ADMIN)
        arequest = ext.record_assistant_request(
            assistant["id"], ADMIN, request_ref="RQ-1")
        aoutcome = ext.record_assistant_outcome(
            arequest["id"], "reported_done", ADMIN, result_ref="RS-1")
        shipment = ext.record_shipment("SH", OPERATOR,
                                       project_id=self.project["id"])
        risk = ext.record_risk_report(shipment["id"], "low", OPERATOR)
        payment = ext.record_payment_instruction(
            shipment["id"], OPERATOR, 100, payee_ref="SUP-1")
        shipment_view = ext.shipment_view(shipment["id"], OPERATOR)
        return [program, custody, program_view, bom, order, outcome,
                order_view, req, event, award, req_view, agreement,
                state, agreement_view, station, session, control,
                station_view, prop, lease, portfolio, device, grant,
                access_event, device_view, assistant, arequest,
                aoutcome, shipment, risk, payment, shipment_view]

    def test_no_tier_shaped_key_no_float_no_numeric_list(self):
        for record in self._everything():
            for key, value in _walk(record):
                lowered = key.lower()
                for part in self.FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, lowered,
                        "tier-shaped key %r in %r" % (key, record))
                self.assertNotIsInstance(
                    value, float,
                    "float value at %r in %r" % (key, record))
                if isinstance(value, list):
                    for item in value:
                        self.assertNotIsInstance(
                            item, (int, float),
                            "numeric list at %r in %r" % (key, record))

    def test_stub_records_carry_their_labels(self):
        records = self._everything()
        by_id = {r["id"]: r for r in records if "id" in r}
        for stub_id in ("asst-1", "asrq-1", "asoc-1", "evc-1"):
            self.assertIs(by_id[stub_id]["reference_stub"], True)

    def test_extension_surface_is_audited(self):
        self.ext.define_maintenance_program("PM", OPERATOR)
        actions = self.audit_actions()
        self.assertIn("ext_maintenance_program_define", actions)


class TestBareStoreFixture(unittest.TestCase):
    """The extension surface works over a bare core store too."""

    def test_bare_store(self):
        store = fresh_store()
        ext = OpsExtensions(store)
        org = store.create_organization("Org", ADMIN)
        prop = ext.register_property("Site", ADMIN, org_id=org["id"])
        self.assertEqual(prop["org_id"], org["id"])
        with self.assertRaises(NotFoundError):
            ext.register_property("Site 2", ADMIN, org_id="org-999")


if __name__ == "__main__":
    unittest.main()
